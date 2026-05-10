import argparse
import sys

from scraper import create_session
from sites import get_site, get_all_sites, list_sites
from downloader import download_chapters


def cmd_search(args):
    session = create_session()

    if args.site:
        # Search a specific site
        site = get_site(f"https://{args.site}/")
        sites_to_search = [site]
    else:
        # Search all sites
        sites_to_search = get_all_sites()

    all_results = []
    for site in sites_to_search:
        print(f"Searching {site.domain} for: {args.query}")
        try:
            results = site.search(args.query, session)
            for r in results:
                r["site"] = site.domain
            all_results.extend(results)
        except Exception as e:
            print(f"  {site.domain}: error — {e}")

    if not all_results:
        print("\nNo results found.")
        print("Try providing the novel index page URL directly: python cli.py list <URL>")
        return

    print()
    for i, novel in enumerate(all_results, 1):
        author_str = f" — {novel['author']}" if novel['author'] else ""
        print(f"  {i}. [{novel['site']}] {novel['title']}{author_str}")
        print(f"     {novel['url']}")
    print()
    print("Use 'python cli.py list <URL>' to view chapters, or")
    print("    'python cli.py download <URL>' to download.")


def cmd_list(args):
    print(f"Fetching chapter list from: {args.url}")
    session = create_session()

    try:
        site = get_site(args.url)
        info = site.get_novel_info(args.url, session)
    except Exception as e:
        print(f"Error: {e}")
        return

    print(f"\n  Title:  {info['title']}")
    if info['author']:
        print(f"  Author: {info['author']}")
    print(f"  Chapters: {len(info['chapters'])}")
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
        description="Download Chinese web novel chapters",
    )
    sub = parser.add_subparsers(dest="command")

    p_search = sub.add_parser("search", help="Search for a novel by name")
    p_search.add_argument("query", help="Novel name or keyword")
    p_search.add_argument("-s", "--site", default=None,
                          help=f"Search a specific site (default: all). Supported: {', '.join(list_sites())}")
    p_search.set_defaults(func=cmd_search)

    p_list = sub.add_parser("list", help="List all chapters of a novel")
    p_list.add_argument("url", help="Novel index page URL")
    p_list.set_defaults(func=cmd_list)

    p_dl = sub.add_parser("download", help="Download chapters")
    p_dl.add_argument("url", help="Novel index page URL")
    p_dl.add_argument("-s", "--start", type=int, default=1, help="Start chapter (default: 1)")
    p_dl.add_argument("-e", "--end", type=int, default=0, help="End chapter (default: last)")
    p_dl.add_argument("-a", "--all", dest="all_chapters", action="store_true", help="Download all chapters")
    p_dl.add_argument("-p", "--part", action="store_true", help="Individually include one chapter in every txt file")
    p_dl.add_argument("-o", "--output", default=None, help="Output directory (default: ./novels/)")
    p_dl.add_argument("-d", "--delay", type=float, default=None, help="Delay between requests in seconds")
    p_dl.add_argument("--resume", action="store_true", help="Skip already downloaded chapters")
    p_dl.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    p_dl.add_argument("--dry-run", action="store_true", help="Show what would be downloaded without doing it")
    p_dl.set_defaults(func=cmd_download)

    if len(sys.argv) == 1:
        parser.print_help()
        return

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
