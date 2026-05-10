import argparse
import sys

from scraper import create_session
from sites import get_site, get_searchable_sites
from downloader import download_chapters


def cmd_search(args):
    session = create_session()

    if args.site:
        site = get_site(f"https://{args.site}/")
        if not site.searchable:
            print(f"[{site.domain}] 该站点不支持搜索。")
            print("  请直接提供小说目录页 URL。")
            return
        sites_to_search = [site]
    else:
        sites_to_search = get_searchable_sites()

    if not sites_to_search:
        print("没有可用的搜索站点。")
        return

    all_results = []
    for site in sites_to_search:
        print(f"正在搜索 {site.domain}：{args.query}")
        try:
            results = site.search(args.query, session)
            for r in results:
                r["site"] = site.domain
            all_results.extend(results)
        except Exception as e:
            print(f"  {site.domain}：错误 — {e}")

    if not all_results:
        print("\n未找到结果。")
        print("请直接提供小说目录页 URL：python cli.py list <URL>")
        return

    print()
    for i, novel in enumerate(all_results, 1):
        author_str = f" — {novel['author']}" if novel['author'] else ""
        print(f"  {i}. [{novel['site']}] {novel['title']}{author_str}")
        print(f"     {novel['url']}")
    print()
    print("使用 'python cli.py list <URL>' 查看章节列表，")
    print("    或使用 'python cli.py download <URL>' 下载。")


def cmd_list(args):
    print(f"正在获取章节列表：{args.url}")
    session = create_session()

    try:
        site = get_site(args.url)
        info = site.get_novel_info(args.url, session)
    except Exception as e:
        print(f"错误：{e}")
        return

    print(f"\n  书名：  {info['title']}")
    if info['author']:
        print(f"  作者：{info['author']}")
    print(f"  章节数：{len(info['chapters'])}")
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
        description="下载网络小说章节",
    )
    sub = parser.add_subparsers(dest="command")

    p_search = sub.add_parser("search", help="按名称搜索小说")
    p_search.add_argument("query", help="小说名称或关键词")
    p_search.add_argument("-s", "--site", default=None,
                          help="搜索指定站点（默认：所有可搜索站点）。仅域名，如 biquuge.com")
    p_search.set_defaults(func=cmd_search)

    p_list = sub.add_parser("list", help="列出小说的所有章节")
    p_list.add_argument("url", help="小说目录页 URL")
    p_list.set_defaults(func=cmd_list)

    p_dl = sub.add_parser("download", help="下载章节")
    p_dl.add_argument("url", help="小说目录页 URL")
    p_dl.add_argument("-s", "--start", type=int, default=1, help="起始章节（默认：1）")
    p_dl.add_argument("-e", "--end", type=int, default=0, help="结束章节（默认：最后一章）")
    p_dl.add_argument("-a", "--all", dest="all_chapters", action="store_true", help="下载全部章节")
    p_dl.add_argument("-p", "--part", action="store_true", help="每个章节单独保存为一个 txt 文件")
    p_dl.add_argument("-o", "--output", default=None, help="输出目录（默认：./novels/）")
    p_dl.add_argument("-d", "--delay", type=float, default=None, help="请求间隔秒数")
    p_dl.add_argument("--resume", action="store_true", help="跳过已下载的章节")
    p_dl.add_argument("-v", "--verbose", action="store_true", help="详细输出")
    p_dl.add_argument("--dry-run", action="store_true", help="仅显示将要下载的内容，不实际下载")
    p_dl.set_defaults(func=cmd_download)

    if len(sys.argv) == 1:
        parser.print_help()
        return

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
