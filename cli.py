import argparse
import sys

from scraper import create_session, search_novels, get_novel_info
from downloader import download_chapters


def cmd_search(args):
    print(f"正在搜索: {args.query}")
    results = search_novels(args.query)

    if not results:
        print("未找到结果，或搜索功能暂不可用。")
        print("请直接提供小说首页URL: python cli.py list <URL>")
        return

    print()
    for i, novel in enumerate(results, 1):
        author_str = f" — {novel['author']}" if novel['author'] else ""
        print(f"  {i}. {novel['title']}{author_str}")
        print(f"     {novel['url']}")
    print()
    print("用 'python cli.py list <URL>' 查看章节目录，")
    print("或 'python cli.py download <URL>' 下载。")


def cmd_list(args):
    print(f"正在获取章节目录: {args.url}")
    session = create_session()

    try:
        info = get_novel_info(args.url, session)
    except Exception as e:
        print(f"Error: {e}")
        return

    print(f"\n  书名:  {info['title']}")
    if info['author']:
        print(f"  作者: {info['author']}")
    print(f"  总章节: {len(info['chapters'])}")
    print()

    for i, ch in enumerate(info['chapters'], 1):
        print(f"  {i:>4}. {ch['title']}")


def cmd_download(args):
    start = 1 if args.all_chapters else args.start
    end = 0 if args.all_chapters else args.end
    download_chapters(
        novel_url=args.url,
        start=start,
        end=end,
        output_dir=args.output,
        delay=args.delay if args.delay is not None else 1.0,
        resume=args.resume,
        verbose=args.verbose,
        dry_run=args.dry_run,
        part=args.part,
    )


def main():
    parser = argparse.ArgumentParser(
        prog="novel_spider",
        description="下载中文网络小说章节",
    )
    sub = parser.add_subparsers(dest="command")

    p_search = sub.add_parser("search", help="搜索小说")
    p_search.add_argument("query", help="小说名或关键词")
    p_search.set_defaults(func=cmd_search)

    p_list = sub.add_parser("list", help="列出小说全部章节")
    p_list.add_argument("url", help="小说首页URL")
    p_list.set_defaults(func=cmd_list)

    p_dl = sub.add_parser("download", help="下载章节")
    p_dl.add_argument("url", help="小说首页URL")
    p_dl.add_argument("-s", "--start", type=int, default=1, help="起始章节号（默认: 1）")
    p_dl.add_argument("-e", "--end", type=int, default=0, help="结束章节号（默认: 最后一章）")
    p_dl.add_argument("-a", "--all", dest="all_chapters", action="store_true", help="下载全部章节")
    p_dl.add_argument("-p", "--part", action="store_true", help="保留分章txt文件，不整合")
    p_dl.add_argument("-o", "--output", default=None, help="输出目录（默认: ./novels/）")
    p_dl.add_argument("-d", "--delay", type=float, default=None, help="请求间隔秒数（默认: 1.0）")
    p_dl.add_argument("--resume", action="store_true", help="跳过已下载的章节")
    p_dl.add_argument("-v", "--verbose", action="store_true", help="详细输出")
    p_dl.add_argument("--dry-run", action="store_true", help="预览模式，不实际下载")
    p_dl.set_defaults(func=cmd_download)

    if len(sys.argv) == 1:
        parser.print_help()
        return

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
