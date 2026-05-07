import os
import sys
import time

from config import Config
from scraper import create_session, get_novel_info, fetch_chapter_all_pages, ScraperError
from parser import ParseError
from utils import sanitize_filename, ensure_dir


def download_chapters(novel_url, start=1, end=0, output_dir=None, delay=1.0,
                      resume=False, verbose=False, dry_run=False, config=None):
    """Download novel chapters and save as text files.

    Returns (downloaded_count, failed_count).
    """
    if config is None:
        config = Config()
    if output_dir is None:
        output_dir = config.output_dir
    if delay is None:
        delay = config.delay

    session = create_session(config)

    # 1. Get novel info (chapter list)
    print(f"Fetching novel info from: {novel_url}")
    try:
        info = get_novel_info(novel_url, session)
    except (ScraperError, ParseError) as e:
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

    # 2. Validate range
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

    # 3. Set up output directory
    novel_dir = os.path.join(output_dir, sanitize_filename(novel_title))
    ensure_dir(novel_dir)

    if dry_run:
        print(f"\n[Dry-run] Would save to: {novel_dir}")
        for i in range(start - 1, end):
            ch = chapters[i]
            print(f"  Chapter {i + 1}: {ch['title']}")
        return end - start + 1, 0

    # 4. Download chapters
    downloaded = 0
    failed = 0
    total = end - start + 1

    try:
        for idx in range(start - 1, end):
            ch = chapters[idx]
            ch_num = idx + 1
            ch_title = ch["title"]
            ch_url = ch["url"]

            filename = f"第{ch_num}章 {sanitize_filename(ch_title)}.txt"
            filepath = os.path.join(novel_dir, filename)

            # Resume: skip if file exists
            if resume and os.path.exists(filepath):
                if verbose:
                    print(f"[{ch_num}/{total_chapters}] Skipping (exists): {ch_title}")
                downloaded += 1
                continue

            if verbose:
                print(f"[{ch_num}/{total}] Downloading: {ch_title}")

            try:
                content = fetch_chapter_all_pages(ch_url, session, delay=0)
            except (ScraperError, ParseError) as e:
                print(f"[{ch_num}/{total}] FAILED: {ch_title} — {e}")
                # Write error placeholder
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(f"[Download failed: {e}]\n")
                failed += 1
                continue

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)

            downloaded += 1

            # Progress update for non-verbose mode
            if not verbose:
                print(f"\r[{ch_num}/{total}] {ch_title}", end="", flush=True)

            if delay:
                time.sleep(delay)

    except KeyboardInterrupt:
        print(f"\n\nInterrupted. Downloaded: {downloaded}, Failed: {failed}, "
              f"Remaining: {total - downloaded - failed}")
        return downloaded, failed

    if not verbose:
        print()  # newline after progress line

    # 5. Summary
    print(f"\nDone! Saved to: {novel_dir}")
    print(f"Downloaded: {downloaded}, Failed: {failed}")
    return downloaded, failed
