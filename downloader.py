import os
import re
import sys
import time

from pathlib import Path

from config import Config
from scraper import create_session, ScraperError
from sites import get_site
from utils import sanitize_filename, ensure_dir


def download_chapters(novel_url, start=1, end=0, output_dir=None, delay=1.0,
                      resume=False, verbose=False, dry_run=False, part=False, config=None):
    """下载小说章节并保存为 txt 文件。

    返回 (已下载数, 失败数)。
    """
    if config is None:
        config = Config()
    if output_dir is None:
        output_dir = config.output_dir
    if delay is None:
        delay = config.delay

    session = create_session(config)

    # Match site adapter
    try:
        site = get_site(novel_url)
    except ValueError as e:
        print(f"Error: {e}")
        return 0, 0

    # 1. Get novel info (chapter list)
    print(f"Fetching novel info from: {novel_url}")
    try:
        info = site.get_novel_info(novel_url, session)
    except Exception as e:
        print(f"Error fetching novel info: {e}")
        return 0, 0

    novel_title = info["title"]
    chapters = info["chapters"]
    total_chapters = len(chapters)

    if total_chapters == 0:
        print("No chapters found.")
        return 0, 0

    print(f"Novel: {novel_title}")
    print(f"Total chapters: {total_chapters}")

    # 2. 校验章节范围
    if end == 0:
        end = total_chapters
    if start < 1:
        start = 1
    if end > total_chapters:
        end = total_chapters
    if start > end:
        print(f"Invalid range: start ({start}) > end ({end})")
        return 0, 0

    print(f"Downloading chapters {start} to {end} ({end - start + 1} chapters)")

    # 3. 创建输出目录
    novel_dir = os.path.join(output_dir, sanitize_filename(novel_title))
    ensure_dir(novel_dir)

    if dry_run:
        print(f"\n[Dry-run] Would save to: {novel_dir}")
        for i in range(start - 1, end):
            ch = chapters[i]
            print(f"  Chapter {i + 1}: {ch['title']}")
        return end - start + 1, 0

    # 4. 逐章下载
    downloaded = 0
    failed = 0
    total = end - start + 1
    filepath_list = []

    try:
        for idx in range(start - 1, end):
            ch = chapters[idx]
            ch_num = idx + 1
            ch_title = ch["title"]
            ch_url = ch["url"]

            # 去掉章节标题自带的"第N章"前缀，避免文件名重复
            clean_title = re.sub(r'^第\d+章\s*', '', ch_title).strip()
            if not clean_title:
                clean_title = ch_title
            filename = f"第{ch_num}章 {sanitize_filename(clean_title)}.txt"
            filepath = os.path.join(novel_dir, filename)
            filepath_list.append(filepath)

            # 断点续传：跳过已存在的文件
            if resume and os.path.exists(filepath):
                if verbose:
                    print(f"[{ch_num}/{total_chapters}] Skipping (exists): {ch_title}")
                downloaded += 1
                continue

            if verbose:
                print(f"[{ch_num}/{total}] Downloading: {ch_title}")

            try:
                content = site.get_chapter_content(ch_url, session, delay=0)
            except Exception as e:
                print(f"[{ch_num}/{total}] FAILED: {ch_title} — {e}")
                # 写入错误占位文件
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(f"[Download failed: {e}]\n")
                failed += 1
                continue

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)

            downloaded += 1

            # 非 verbose 模式下的进度刷新
            if not verbose:
                print('\r'+' '*64, end="", flush=True)      # 擦除上一条进度信息
                print(f"\r[{ch_num}/{total}] {ch_title}", end="", flush=True)

            if delay:
                time.sleep(delay)

    except KeyboardInterrupt:
        print(f"\n\nInterrupted. Downloaded: {downloaded}, Failed: {failed}, "
              f"Remaining: {total - downloaded - failed}")
        return downloaded, failed

    if not verbose:
        print()  # 进度行后换行

    # 5. 整合为单个 txt 文件
    if not part:
        print(f"整合章节 {start} 到 {end} (共 {total} 章)")
        filename = f"{start}-{end}章.txt"
        filepath = os.path.join(novel_dir, filename)
        output = Path(filepath)
        count = 1
        with output.open("w", encoding="utf-8") as outfile:
            for readpath in filepath_list:
                input = Path(readpath)
                outfile.write(f"{input.name[:-4]}\n")
                outfile.write(input.read_text(encoding="utf-8"))
                outfile.write("\n\n")
                print('\r'+' '*64, end="", flush=True)
                print(f"\r[{count}/{total}] {input.name[:-4]}", end="", flush=True)
                count += 1
                input.unlink()

        print()

    # 6. 输出摘要
    print(f"\n完成！保存到: {novel_dir}")
    print(f"已下载: {downloaded}, 失败: {failed}")
    return downloaded, failed
