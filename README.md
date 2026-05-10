# 小说下载器 — 新手使用指南

这个工具可以从多个小说网站下载章节，保存成 txt 文件到电脑上。

## 使用方式

本工具提供两种使用方式：

| 方式 | 说明 | 适合人群 |
|------|------|----------|
| **GUI 图形界面** | 启动一个窗口程序，搜索、选章节、下载全在窗口里完成 | 不习惯命令行的用户 |
| **命令行** | 在命令提示符中输入命令来操作 | 习惯命令行的用户 |

### GUI 模式（推荐新手）

直接双击运行或输入：

```
python main.py
```

会弹出一个窗口，在窗口里搜索小说 → 获取章节 → 下载，全部用鼠标操作即可。具体操作说明见窗口内各区域的提示。

---

## 支持的网站

### 支持搜索的网站

可以直接用小说名搜索，找到小说后下载。

| 网站 | 说明 |
|------|------|
| biquuge.com | 笔趣阁 |
| douyinxs.com | 抖音小说 |

### 不支持搜索的网站

这些网站的搜索接口有反爬保护，无法通过关键词搜索。使用时需要先在浏览器中打开网站，手动找到小说目录页的网址，然后直接用网址执行 `list` 或 `download` 命令。

| 网站 | 说明 |
|------|------|
| xiaoshuopu.com | 小说铺 |
| newqy.com | 掌阅中文 |

---

## 命令行使用说明

以下内容适用于命令行模式。如果你使用 GUI 模式（`python main.py`），不需要看这部分。

### 第一次使用（只需要做一次）

#### 1. 确认电脑上有 Python

打开命令提示符（按 `Win+R`，输入 `cmd`，回车），输入：

```
python --version
```

如果显示 `Python 3.x.x`，说明已经有了，跳到第 3 步。

如果提示找不到 python，需要先安装：

- 打开 https://www.python.org/downloads/
- 点击黄色大按钮下载
- 安装时**一定要勾选** "Add Python to PATH"
- 安装完后重新打开命令提示符

#### 2. 下载这个项目

点击 GitHub 上的 Code → Download ZIP，解压到任意文件夹。

或者在命令提示符里（需要装了 git）：

```
git clone https://github.com/mahuahyl/novel_spider.git
```

#### 3. 安装依赖

打开命令提示符，进入项目文件夹：

```
cd 项目文件夹路径
```

输入以下命令（只需要执行一次）：

```
pip install requests lxml
```

看到 `Successfully installed` 就说明装好了。

---

### 使用方法

以后每次使用，先打开命令提示符，进入项目文件夹，然后执行下面的命令。

#### 第一步：搜索小说（仅限支持搜索的网站）

```
python cli.py search 小说名
```

例如你想找《天才俱乐部》：

```
python cli.py search 天才俱乐部
```

默认会在所有支持搜索的网站中查找。也可以指定只搜某一个网站：

```
python cli.py search 天才俱乐部 -s biquuge.com
```

你会看到类似这样的结果：

```
正在搜索 biquuge.com：天才俱乐部

  1. [biquuge.com] 天才俱乐部 — 浅浅与蝉
     https://www.biquuge.com/0/112/

使用 'python cli.py list <URL>' 查看章节列表，
    或使用 'python cli.py download <URL>' 下载。
```

**复制这行网址**（选中后按 Ctrl+C），下一步要用。

##### 不支持搜索的网站怎么办？

先在浏览器中打开对应网站（如 https://www.xiaoshuopu.com），在网站上搜索小说，找到小说的目录页后复制网址，直接从第二步开始。

#### 第二步：看看有哪些章节（可选）

把刚才复制的网址粘到命令里：

```
python cli.py list "刚才复制的网址"
```

例如：

```
python cli.py list "https://www.biquuge.com/0/112/"
```

会显示这本书有多少章，每章叫什么名字。

#### 第三步：下载小说

把网址粘进去，告诉程序你要下载哪些章节：

```
python cli.py download "刚才复制的网址" -s 起始章节号 -e 结束章节号
```

##### 常用例子：

**下载前面 50 章：**
```
python cli.py download "https://www.biquuge.com/0/112/" -s 1 -e 50
```

**下载整本书（全部章节）：**
```
python cli.py download "https://www.biquuge.com/0/112/" --all
```

**每章保存为单独的 txt 文件：**
```
python cli.py download "https://www.biquuge.com/0/112/" --all -p
```

**只想看看会下载哪些，先不下载：**
```
python cli.py download "https://www.biquuge.com/0/112/" -s 1 -e 3 --dry-run
```

**上次下了一半，接着下载（跳过已下载的）：**
```
python cli.py download "https://www.biquuge.com/0/112/" --all --resume
```

---

### 下载到哪里了？

下载的小说会放在项目文件夹里的 `novels` 文件夹下。

默认情况下，指定范围内的所有章节会合并为一个 txt 文件。使用 `-p` 参数后，每章单独保存为一个 txt 文件。

路径大概是：
```
项目文件夹/novels/小说名/1-50章.txt
```

或使用 `-p` 参数后：
```
项目文件夹/novels/小说名/第1章 章节标题.txt
                      /第2章 章节标题.txt
                      /...
```

---

### 常见问题

**Q: 下载速度太快被网站限制了怎么办？**

加一个延迟参数，让程序每下载一章等 2 秒：
```
python cli.py download "网址" --all -d 2
```

**Q: 想下载到别的文件夹？**

用 `-o` 参数指定路径：
```
python cli.py download "网址" -s 1 -e 50 -o "D:/我的小说"
```

**Q: 程序下载到一半断了？**

用 `--resume` 重新运行，它会跳过已经下载好的章节：
```
python cli.py download "网址" --all --resume
```

**Q: 搜索不到小说怎么办？**

- 先尝试在不同网站搜索：`python cli.py search 小说名`
- 或者打开小说网站，在网站上搜索，找到小说目录页后复制网址，直接从第二步开始：`python cli.py list <URL>`
