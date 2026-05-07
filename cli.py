import argparse
import sys


def cmd_search(args):
    print(f"Searching for: {args.query}")
    print("(Not yet implemented)")


def cmd_list(args):
    print(f"Listing chapters from: {args.url}")
    print("(Not yet implemented)")


def cmd_download(args):
    print(f"Downloading from: {args.url}")
    if args.all_chapters:
        print("  Range: all chapters")
    else:
        print(f"  Range: {args.start} - {args.end}")
    print(f"  Output: {args.output}")
    print("(Not yet implemented)")


def main():
    parser = argparse.ArgumentParser(
        prog="novel_spider",
        description="Download Chinese web novel chapters",
    )
    sub = parser.add_subparsers(dest="command")

    p_search = sub.add_parser("search", help="Search for a novel by name")
    p_search.add_argument("query", help="Novel name or keyword")
    p_search.set_defaults(func=cmd_search)

    p_list = sub.add_parser("list", help="List all chapters of a novel")
    p_list.add_argument("url", help="Novel index page URL")
    p_list.set_defaults(func=cmd_list)

    p_dl = sub.add_parser("download", help="Download chapters")
    p_dl.add_argument("url", help="Novel index page URL")
    p_dl.add_argument("-s", "--start", type=int, default=1, help="Start chapter (default: 1)")
    p_dl.add_argument("-e", "--end", type=int, default=0, help="End chapter (default: last)")
    p_dl.add_argument("-a", "--all", dest="all_chapters", action="store_true", help="Download all chapters")
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
