# 小说下载器 — 新手使用指南

这个工具可以从笔趣阁下载小说章节，保存成 txt 文件到电脑上。

## 第一次使用（只需要做一次）

### 1. 确认电脑上有 Python

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

### 2. 下载这个项目

点击 GitHub 上的 Code → Download ZIP，解压到任意文件夹。

或者在命令提示符里（需要装了 git）：

```
git clone https://github.com/mahuahyl/novel_spider.git
```

### 3. 安装依赖

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

## 使用方法

以后每次使用，先打开命令提示符，进入项目文件夹，然后执行下面三个命令之一。

### 第一步：搜索小说

```
python cli.py search 小说名
```

例如你想找《天才俱乐部》：

```
python cli.py search 天才俱乐部
```

你会看到类似这样的结果：

```
Searching for: 天才俱乐部

  1. 天才俱乐部 — 浅浅与蝉
     https://www.biquuge.com/0/112/

Use 'python cli.py list <URL>' to view chapters
```

**复制这行网址**（选中后按 Ctrl+C），下一步要用。

### 第二步：看看有哪些章节（可选）

把刚才复制的网址粘到命令里：

```
python cli.py list "刚才复制的网址"
```

例如：

```
python cli.py list "https://www.biquuge.com/0/112/"
```

会显示这本书有多少章，每章叫什么名字。

### 第三步：下载小说

把网址粘进去，告诉程序你要下载哪些章节：

```
python cli.py download "刚才复制的网址" -s 起始章节号 -e 结束章节号
```

#### 常用例子：

**下载前面 50 章：**
```
python cli.py download "https://www.biquuge.com/0/112/" -s 1 -e 50
```

**下载整本书（全部章节）：**
```
python cli.py download "https://www.biquuge.com/0/112/" --all
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

## 下载到哪里了？

下载的小说会放在项目文件夹里的 `novels` 文件夹下。

路径大概是：
```
项目文件夹/novels/小说名/第1章 章节标题.txt
                      /第2章 章节标题.txt
                      /...
```

---

## 常见问题

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

先打开 https://www.biquuge.com 在网站上搜索，找到小说后复制网址，直接从第二步开始。
