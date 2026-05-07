# novel_spider — 小说章节下载器

从 [biquuge.com](https://www.biquuge.com) 搜索小说、查看章节目录、分章节下载到本地。

## 安装

```
pip install -r requirements.txt
```

依赖：`requests>=2.28`、`lxml>=4.9`

## 使用

### 搜索小说

```
python cli.py search <关键词>
```

示例：
```
python cli.py search "天才俱乐部"
```

显示搜索结果后，复制小说 URL 用于后续操作。

### 查看章节目录

```
python cli.py list <小说首页URL>
```

示例：
```
python cli.py list "https://www.biquuge.com/0/112/"
```

显示小说标题、作者、总章节数，列出所有章节。

### 下载章节

```
python cli.py download <小说首页URL> [选项]
```

示例：
```
# 下载第1到第50章
python cli.py download "https://www.biquuge.com/0/112/" -s 1 -e 50

# 下载全部章节
python cli.py download "https://www.biquuge.com/0/112/" --all

# 预览将要下载的内容（不实际下载）
python cli.py download "https://www.biquuge.com/0/112/" -s 1 -e 3 --dry-run

# 断点续传（跳过已下载的章节）
python cli.py download "https://www.biquuge.com/0/112/" -s 1 -e 100 --resume

# 限制请求间隔为 2 秒
python cli.py download "https://www.biquuge.com/0/112/" --all -d 2
```

#### 下载参数

| 参数 | 说明 |
|------|------|
| `-s, --start N` | 起始章节号 (默认: 1) |
| `-e, --end N` | 结束章节号 (默认: 最后一章) |
| `-a, --all` | 下载全部章节 |
| `-o, --output DIR` | 输出目录 (默认: `./novels/`) |
| `-d, --delay SEC` | 请求间隔秒数 (默认: 1.0) |
| `--resume` | 跳过已存在的文件 |
| `--dry-run` | 预览模式，不实际下载 |
| `-v, --verbose` | 显示详细输出 |

## 输出

下载的小说保存在 `./novels/<小说名>/` 目录下，每个章节一个 `.txt` 文件，格式为 `第N章 标题.txt`。

## 配置文件（可选）

支持三层配置，优先级：CLI 参数 > JSON 文件 > 默认值。

JSON 文件位置（按顺序查找，找到即停）：
1. `./novel_spider_config.json`（项目根目录）
2. `~/.novel_spider_config.json`（用户主目录）

示例：
```json
{
    "output_dir": "D:/novels",
    "delay": 2.0,
    "timeout": 60,
    "max_retries": 5
}
```
