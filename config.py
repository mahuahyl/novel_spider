import json
import os
from pathlib import Path


class Config:
    def __init__(self, cli_args=None):
        self.output_dir = "./novels/"
        self.delay = 1.0
        self.timeout = 30
        self.max_retries = 3
        self.user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
        self.proxy = None

        self._load_file_config()

        if cli_args:
            self._apply_cli_args(cli_args)

    def _load_file_config(self):
        paths = [
            Path("./novel_spider_config.json"),
            Path.home() / ".novel_spider_config.json",
        ]
        for p in paths:
            if p.exists():
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for key in ("output_dir", "delay", "timeout", "max_retries", "user_agent", "proxy"):
                    if key in data:
                        setattr(self, key, data[key])
                break

    def _apply_cli_args(self, args):
        if hasattr(args, "output") and args.output:
            self.output_dir = args.output
        if hasattr(args, "delay") and args.delay is not None:
            self.delay = args.delay
