import os
import re
import sys
import time
import queue
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from config import Config
from scraper import create_session
from sites import get_site, get_searchable_sites, list_sites
from utils import sanitize_filename, ensure_dir


# ═══════════════════════════════════════════════════════════════════════
#  主题色板
# ═══════════════════════════════════════════════════════════════════════
C = {
    "bg":       "#f5f6fa",
    "card":     "#ffffff",
    "accent":   "#5b5ea6",
    "accent_h": "#484b8a",
    "accent_l": "#e8e9f3",
    "text":     "#2d3436",
    "text2":    "#636e72",
    "border":   "#dfe6e9",
    "select":   "#e8e9f3",
    "head_bg":  "#5b5ea6",
    "head_fg":  "#ffffff",
    "log_bg":   "#1e1e2e",
    "log_fg":   "#cdd6f4",
    "title_bg": "#5b5ea6",
    "close_bg": "#e74c3c",
}

FONT      = ("Microsoft YaHei", 9)
FONT_BOLD = ("Microsoft YaHei", 9, "bold")
FONT_SM   = ("Microsoft YaHei", 8)
FONT_LOG  = ("Consolas", 8)
FONT_TITLE = ("Microsoft YaHei", 10, "bold")


# ═══════════════════════════════════════════════════════════════════════
#  Canvas 圆角胶囊按钮
# ═══════════════════════════════════════════════════════════════════════
class PillButton(tk.Frame):
    """圆角胶囊按钮，支持 hover 变色。"""

    def __init__(self, parent, text="", command=None,
                 bg=C["accent"], fg="#ffffff", hover_bg=C["accent_h"],
                 font=FONT_BOLD, w=80, h=30, radius=None, **kw):
        super().__init__(parent, bg=bg, width=w, height=h, **kw)
        self.pack_propagate(False)
        self._cmd = command
        self._bg = bg
        self._hbg = hover_bg
        self._enabled = True

        self._label = tk.Label(self, text=text, font=font,
                                bg=bg, fg=fg, cursor="hand2")
        self._label.pack(expand=True, fill="both")

        for w in (self, self._label):
            w.bind("<Enter>", self._on_enter)
            w.bind("<Leave>", self._on_leave)
            w.bind("<ButtonRelease-1>", self._on_click)

    def _on_enter(self, e):
        if self._enabled:
            self.config(bg=self._hbg)
            self._label.config(bg=self._hbg)

    def _on_leave(self, e):
        if self._enabled:
            self.config(bg=self._bg)
            self._label.config(bg=self._bg)

    def _on_click(self, e):
        if self._enabled and self._cmd:
            self._cmd()

    def configure(self, cnf=None, **kw):
        if "state" in kw:
            if kw["state"] == "disabled":
                self._enabled = False
                self.config(bg=C["border"])
                self._label.config(bg=C["border"], fg=C["text2"])
            else:
                self._enabled = True
                self.config(bg=self._bg)
                self._label.config(bg=self._bg, fg="#ffffff")
            kw.pop("state")
        if "text" in kw:
            self._label.config(text=kw.pop("text"))
        super().configure(cnf, **kw)

    config = configure


# ═══════════════════════════════════════════════════════════════════════
#  卡片容器（白底 + 圆角 + 阴影感）
# ═══════════════════════════════════════════════════════════════════════
class Card(tk.Frame):
    """带标题的卡片式容器。"""

    def __init__(self, parent, title="", **kw):
        super().__init__(parent, bg=C["bg"], **kw)
        # 外层装饰框
        outer = tk.Frame(self, bg=C["border"])
        outer.pack(fill="both", expand=True)
        inner = tk.Frame(outer, bg=C["card"])
        inner.pack(fill="both", expand=True, padx=1, pady=1)

        if title:
            lbl = tk.Label(inner, text=title, font=FONT_BOLD,
                           bg=C["card"], fg=C["accent"], anchor="w")
            lbl.pack(fill="x", padx=10, pady=(8, 4))

        # 内部内容区
        self.body = tk.Frame(inner, bg=C["card"])
        self.body.pack(fill="both", expand=True, padx=8, pady=(0, 8))


# ═══════════════════════════════════════════════════════════════════════
#  自定义标题栏
# ═══════════════════════════════════════════════════════════════════════
class TitleBar(tk.Frame):
    def __init__(self, parent, title="小说下载器", **kw):
        super().__init__(parent, bg=C["title_bg"], height=36, **kw)
        self.pack_propagate(False)
        self._parent = parent

        # 图标 + 标题
        tk.Label(self, text="📖  " + title, font=FONT_TITLE,
                 bg=C["title_bg"], fg="#ffffff").pack(side="left", padx=12)

        # 右侧按钮
        btn_frame = tk.Frame(self, bg=C["title_bg"])
        btn_frame.pack(side="right")

        for text, color, hover, cmd in [
            ("─", C["title_bg"], "#4a4d8a", self._minimize),
            ("□", C["title_bg"], "#4a4d8a", self._maximize),
            ("✕", C["close_bg"], "#c0392b", self._close),
        ]:
            b = tk.Label(btn_frame, text=text, font=("Microsoft YaHei", 11),
                         bg=color, fg="#ffffff", width=3, cursor="hand2")
            b.pack(side="left")
            b.bind("<Enter>", lambda e, w=b, c=hover: w.config(bg=c))
            b.bind("<Leave>", lambda e, w=b, c=color: w.config(bg=c))
            b.bind("<Button-1>", lambda e, f=cmd: f())

        # 拖动
        self.bind("<Button-1>", self._start_move)
        self.bind("<B1-Motion>", self._on_move)

    def _start_move(self, e):
        self._ox, self._oy = e.x, e.y

    def _on_move(self, e):
        x = self._parent.winfo_x() + e.x - self._ox
        y = self._parent.winfo_y() + e.y - self._oy
        self._parent.geometry(f"+{x}+{y}")

    def _minimize(self):
        self._parent.iconify()

    def _maximize(self):
        if self._parent.state() == "zoomed":
            self._parent.state("normal")
        else:
            self._parent.state("zoomed")

    def _close(self):
        self._parent.destroy()


# ═══════════════════════════════════════════════════════════════════════
#  主应用
# ═══════════════════════════════════════════════════════════════════════
class NovelSpiderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("小说下载器")
        self.root.geometry("640x560")
        self.root.minsize(580, 420)
        self.root.configure(bg=C["bg"])

        self.config = Config()
        self.msg_queue = queue.Queue()
        self.chapters = []
        self.cancel_flag = False
        self.downloading = False

        self._build_ui()
        self._poll_queue()

    # ────────────────────────── UI 构建 ──────────────────────────
    def _build_ui(self):
        # ---- ttk 样式（仅用于 Treeview / Progressbar / Scrollbar）----
        style = ttk.Style()
        for th in ("vista", "xpnative", "clam", "alt"):
            if th in style.theme_names():
                style.theme_use(th)
                break

        style.configure("Treeview", font=FONT_SM, background=C["card"],
                         fieldbackground=C["card"], foreground=C["text"],
                         rowheight=24, borderwidth=0)
        style.configure("Treeview.Heading", font=FONT_BOLD,
                         background=C["head_bg"], foreground=C["head_fg"],
                         borderwidth=0, padding=(6, 4))
        style.map("Treeview",
                   background=[("selected", C["select"])],
                   foreground=[("selected", C["text"])])
        style.map("Treeview.Heading", background=[("active", C["accent_h"])])
        style.configure("TProgressbar", troughcolor=C["border"],
                         background=C["accent"], borderwidth=0, thickness=6)

        # ---- 主内容区 ----
        container = tk.Frame(self.root, bg=C["bg"])
        container.pack(fill="both", expand=True)

        pad = {"padx": 8, "pady": 4}

        # ════════ 1. 搜索 ════════
        card_search = Card(container, title="搜索小说")
        card_search.pack(fill="x", **pad)
        sf = card_search.body

        self.search_var = tk.StringVar()
        self._make_entry(sf, self.search_var).pack(
            side="left", fill="x", expand=True, padx=(0, 6))
        self.search_var.trace_add("write", lambda *_: None)

        self.site_var = tk.StringVar(value="全部站点")
        site_list = ["全部站点"] + list_sites()
        self._make_combobox(sf, self.site_var, site_list, width=14).pack(
            side="left", padx=(0, 6))

        self._btn_search = PillButton(sf, text="搜索", command=self._on_search, w=60, h=28, radius=14)
        self._btn_search.pack(side="left")
        self.root.bind("<Return>", lambda e: self._on_search())

        # ════════ 2. 搜索结果 ════════
        card_results = Card(container, title="搜索结果（双击填入 URL）")
        card_results.pack(fill="x", **pad)

        cols = ("title", "author", "site")
        self.result_tree = ttk.Treeview(card_results.body, columns=cols,
                                         show="headings", height=4)
        self.result_tree.heading("title", text="书名")
        self.result_tree.heading("author", text="作者")
        self.result_tree.heading("site", text="站点")
        self.result_tree.column("title", width=300)
        self.result_tree.column("author", width=100)
        self.result_tree.column("site", width=100)
        self.result_tree.pack(fill="x")
        self.result_tree.bind("<Double-1>", self._on_result_double_click)

        # ════════ 3. URL 输入 ════════
        card_url = Card(container, title="小说目录页 URL")
        card_url.pack(fill="x", **pad)
        uf = card_url.body

        self.url_var = tk.StringVar()
        self._make_entry(uf, self.url_var).pack(
            side="left", fill="x", expand=True, padx=(0, 6))
        self._btn_fetch = PillButton(uf, text="获取章节", command=self._on_fetch_chapters,
                                      w=80, h=28, radius=14)
        self._btn_fetch.pack(side="left")

        # ════════ 4. 章节列表 ════════
        card_ch = Card(container, title="章节列表")
        card_ch.pack(fill="x", **pad)

        ch_cols = ("num", "title")
        self.chapter_tree = ttk.Treeview(card_ch.body, columns=ch_cols,
                                          show="headings", height=6)
        self.chapter_tree.heading("num", text="#", anchor="w")
        self.chapter_tree.heading("title", text="章节标题")
        self.chapter_tree.column("num", width=40, minwidth=30)
        self.chapter_tree.column("title", width=500)
        self.chapter_tree.pack(fill="both", expand=True)

        rf = tk.Frame(card_ch.body, bg=C["card"])
        rf.pack(fill="x", pady=(4, 0))

        tk.Label(rf, text="起始:", font=FONT, bg=C["card"], fg=C["text"]).pack(side="left")
        self.start_var = tk.StringVar(value="1")
        self._make_entry(rf, self.start_var, width=5).pack(side="left", padx=(2, 10))

        tk.Label(rf, text="结束:", font=FONT, bg=C["card"], fg=C["text"]).pack(side="left")
        self.end_var = tk.StringVar(value="0")
        self._make_entry(rf, self.end_var, width=5).pack(side="left", padx=(2, 10))

        PillButton(rf, text="全选", command=self._select_all_chapters,
                   w=50, h=24, radius=12, font=FONT, bg=C["accent_l"], fg=C["text"],
                   hover_bg=C["select"]).pack(side="left")

        # ════════ 5. 下载设置 ════════
        card_set = Card(container, title="下载设置")
        card_set.pack(fill="x", **pad)
        sf2 = card_set.body

        r1 = tk.Frame(sf2, bg=C["card"])
        r1.pack(fill="x", pady=(0, 4))
        tk.Label(r1, text="输出目录:", font=FONT, bg=C["card"], fg=C["text"]).pack(side="left")
        self.output_var = tk.StringVar(value=self.config.output_dir)
        self._make_entry(r1, self.output_var).pack(
            side="left", fill="x", expand=True, padx=(4, 4))
        PillButton(r1, text="浏览", command=self._browse_output,
                   w=46, h=24, radius=12, font=FONT, bg=C["accent_l"], fg=C["text"],
                   hover_bg=C["select"]).pack(side="left")

        r2 = tk.Frame(sf2, bg=C["card"])
        r2.pack(fill="x")
        tk.Label(r2, text="请求间隔(秒):", font=FONT, bg=C["card"], fg=C["text"]).pack(side="left")
        self.delay_var = tk.StringVar(value=str(self.config.delay))
        self._make_entry(r2, self.delay_var, width=5).pack(side="left", padx=(4, 12))

        self.part_var = tk.BooleanVar(value=False)
        self._make_check(r2, "逐章保存", self.part_var).pack(side="left", padx=6)
        self.resume_var = tk.BooleanVar(value=False)
        self._make_check(r2, "断点续传", self.resume_var).pack(side="left", padx=6)

        # ════════ 6. 操作按钮 ════════
        btn_bar = tk.Frame(container, bg=C["bg"])
        btn_bar.pack(fill="x", padx=8, pady=6)

        self.btn_download = PillButton(btn_bar, text="开始下载", command=self._on_download,
                                        w=90, h=32, radius=16)
        self.btn_download.pack(side="left", padx=(0, 8))

        self.btn_cancel = PillButton(btn_bar, text="取消", command=self._on_cancel,
                                      w=60, h=32, radius=16,
                                      bg=C["border"], fg=C["text2"], hover_bg="#c0c4cc")
        self.btn_cancel.pack(side="left")
        # 初始禁用：灰色
        self._cancel_enabled = False

        # ════════ 7. 进度 & 日志 ════════
        card_prog = Card(container, title="进度")
        card_prog.pack(fill="x", **pad)
        pf = card_prog.body

        self.progress = ttk.Progressbar(pf, mode="determinate")
        self.progress.pack(fill="x", pady=(0, 2))

        self.progress_label = tk.Label(pf, text="就绪", font=FONT_SM,
                                        bg=C["card"], fg=C["text2"], anchor="w")
        self.progress_label.pack(fill="x")

        log_frame = tk.Frame(pf, bg=C["log_bg"])
        log_frame.pack(fill="both", expand=True, pady=(4, 0))

        self.log_text = tk.Text(log_frame, height=5, state="disabled",
                                wrap="word", font=FONT_LOG,
                                bg=C["log_bg"], fg=C["log_fg"],
                                insertbackground=C["log_fg"],
                                selectbackground=C["accent"], selectforeground="#fff",
                                borderwidth=0, highlightthickness=0,
                                padx=8, pady=4)
        lsb = tk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview,
                            width=8, bg=C["border"], troughcolor=C["log_bg"],
                            relief="flat")
        self.log_text.configure(yscrollcommand=lsb.set)
        self.log_text.pack(side="left", fill="both", expand=True)
        lsb.pack(side="right", fill="y")

    # ──────────────── 自定义控件工厂 ────────────────
    def _make_entry(self, parent, var, width=None):
        e = tk.Entry(parent, textvariable=var, font=FONT,
                     bg=C["card"], fg=C["text"],
                     insertbackground=C["text"],
                     relief="solid", bd=1, highlightthickness=1,
                     highlightbackground=C["border"],
                     highlightcolor=C["accent"],
                     width=width)
        return e

    def _make_combobox(self, parent, var, values, width=None):
        cb = ttk.Combobox(parent, textvariable=var, values=values,
                           state="readonly", width=width, font=FONT)
        return cb

    def _make_check(self, parent, text, var):
        return tk.Checkbutton(parent, text=text, variable=var,
                               font=FONT, bg=C["card"], fg=C["text"],
                               selectcolor=C["card"],
                               activebackground=C["card"],
                               activeforeground=C["text"],
                               relief="flat", bd=0)

    # ──────────────────── helpers ────────────────────
    def _log(self, msg):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", msg + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _poll_queue(self):
        try:
            while True:
                kind, data = self.msg_queue.get_nowait()
                if kind == "log":
                    self._log(data)
                elif kind == "progress":
                    current, total, label = data
                    self.progress["value"] = current / total * 100 if total else 0
                    self.progress_label.config(text=label)
                elif kind == "search_done":
                    self._fill_search_results(data)
                elif kind == "chapters_done":
                    self._fill_chapters(data)
                elif kind == "error":
                    messagebox.showerror("错误", data)
                    self._log(f"错误: {data}")
                elif kind == "download_done":
                    self._on_download_finished(data)
        except queue.Empty:
            pass
        self.root.after(100, self._poll_queue)

    def _set_busy(self, busy):
        self.downloading = busy
        if busy:
            self.btn_download.configure(state="disabled")
            # 取消按钮高亮
            self.btn_cancel._bg = C["accent"]
            self.btn_cancel._hbg = C["accent_h"]
            self.btn_cancel.config(bg=C["accent"])
            self.btn_cancel._label.config(bg=C["accent"], fg="#ffffff")
            self._cancel_enabled = True
        else:
            self.btn_download.configure(state="normal")
            self.btn_cancel._bg = C["border"]
            self.btn_cancel._hbg = "#c0c4cc"
            self.btn_cancel.config(bg=C["border"])
            self.btn_cancel._label.config(bg=C["border"], fg=C["text2"])
            self._cancel_enabled = False

    # ──────────────────── 搜索 ────────────────────
    def _on_search(self):
        query = self.search_var.get().strip()
        if not query:
            messagebox.showwarning("提示", "请输入搜索关键词")
            return
        site_name = self.site_var.get()
        self._log(f"搜索: {query} ({site_name})")
        self._set_busy(True)
        threading.Thread(
            target=self._search_thread, args=(query, site_name), daemon=True
        ).start()

    def _search_thread(self, query, site_name):
        session = create_session(self.config)
        if site_name == "全部站点":
            sites_to_search = get_searchable_sites()
        else:
            try:
                sites_to_search = [get_site(f"https://{site_name}/")]
            except ValueError as e:
                self.msg_queue.put(("error", str(e)))
                self.msg_queue.put(("download_done", None))
                return

        all_results = []
        for site in sites_to_search:
            self.msg_queue.put(("log", f"  搜索 {site.domain}..."))
            try:
                results = site.search(query, session)
                for r in results:
                    r["site"] = site.domain
                all_results.extend(results)
            except Exception as e:
                self.msg_queue.put(("log", f"  {site.domain} 搜索失败: {e}"))

        self.msg_queue.put(("search_done", all_results))
        self.msg_queue.put(("download_done", None))

    def _fill_search_results(self, results):
        for item in self.result_tree.get_children():
            self.result_tree.delete(item)
        for r in results:
            self.result_tree.insert("", "end", values=(
                r["title"], r.get("author", ""), r.get("site", "")
            ), tags=(r["url"],))
        self._log(f"找到 {len(results)} 个结果")

    def _on_result_double_click(self, event):
        sel = self.result_tree.selection()
        if not sel:
            return
        tags = self.result_tree.item(sel[0], "tags")
        if tags:
            self.url_var.set(tags[0])

    # ──────────────────── 获取章节 ────────────────────
    def _on_fetch_chapters(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("提示", "请输入小说目录页 URL")
            return
        self._log(f"获取章节列表: {url}")
        self._set_busy(True)
        threading.Thread(
            target=self._fetch_chapters_thread, args=(url,), daemon=True
        ).start()

    def _fetch_chapters_thread(self, url):
        session = create_session(self.config)
        try:
            site = get_site(url)
            info = site.get_novel_info(url, session)
            self.msg_queue.put(("chapters_done", info))
        except Exception as e:
            self.msg_queue.put(("error", str(e)))
        finally:
            self.msg_queue.put(("download_done", None))

    def _fill_chapters(self, info):
        self.chapters = info["chapters"]
        title = info["title"]
        author = info.get("author", "")

        for item in self.chapter_tree.get_children():
            self.chapter_tree.delete(item)
        for i, ch in enumerate(self.chapters, 1):
            self.chapter_tree.insert("", "end", values=(i, ch["title"]))

        self.start_var.set("1")
        self.end_var.set(str(len(self.chapters)))
        self._log(f"《{title}》{' 作者: ' + author if author else ''}  共 {len(self.chapters)} 章")

    def _select_all_chapters(self):
        self.start_var.set("1")
        self.end_var.set(str(len(self.chapters)) if self.chapters else "0")

    # ──────────────────── 下载 ────────────────────
    def _on_download(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("提示", "请先获取章节列表")
            return
        if not self.chapters:
            messagebox.showwarning("提示", "没有可下载的章节")
            return

        try:
            start = int(self.start_var.get())
            end = int(self.end_var.get())
        except ValueError:
            messagebox.showwarning("提示", "起始/结束必须为数字")
            return

        total = len(self.chapters)
        if end <= 0 or end > total:
            end = total
        if start < 1:
            start = 1
        if start > end:
            messagebox.showwarning("提示", "起始章节不能大于结束章节")
            return

        try:
            delay = float(self.delay_var.get())
        except ValueError:
            delay = 1.0

        output_dir = self.output_var.get().strip() or self.config.output_dir
        self.cancel_flag = False
        self._set_busy(True)
        self.progress["value"] = 0
        self._log(f"开始下载第 {start} 到 {end} 章...")

        threading.Thread(
            target=self._download_thread,
            args=(url, start, end, output_dir, delay,
                  self.part_var.get(), self.resume_var.get()),
            daemon=True
        ).start()

    def _download_thread(self, url, start, end, output_dir, delay, part, resume):
        session = create_session(self.config)
        try:
            site = get_site(url)
        except ValueError as e:
            self.msg_queue.put(("error", str(e)))
            self.msg_queue.put(("download_done", None))
            return

        try:
            info = site.get_novel_info(url, session)
        except Exception as e:
            self.msg_queue.put(("error", f"获取小说信息失败: {e}"))
            self.msg_queue.put(("download_done", None))
            return

        novel_title = info["title"]
        chapters = info["chapters"]
        total_chapters = len(chapters)

        if end > total_chapters:
            end = total_chapters

        novel_dir = os.path.join(output_dir, sanitize_filename(novel_title))
        ensure_dir(novel_dir)

        downloaded = 0
        failed = 0
        total = end - start + 1
        filepath_list = []

        for idx in range(start - 1, end):
            if self.cancel_flag:
                self.msg_queue.put(("log", f"\n已中断。已下载: {downloaded}, 失败: {failed}"))
                break

            ch = chapters[idx]
            ch_num = idx + 1
            ch_title = ch["title"]
            ch_url = ch["url"]

            clean_title = re.sub(r'^第\d+章\s*', '', ch_title).strip()
            if not clean_title:
                clean_title = ch_title
            filename = f"第{ch_num}章 {sanitize_filename(clean_title)}.txt"
            filepath = os.path.join(novel_dir, filename)
            filepath_list.append(filepath)

            if resume and os.path.exists(filepath):
                self.msg_queue.put(("log", f"[{ch_num}/{total}] 跳过（已存在）: {ch_title}"))
                downloaded += 1
                self.msg_queue.put(("progress", (downloaded + failed, total,
                                   f"{downloaded + failed}/{total}")))
                continue

            try:
                content = site.get_chapter_content(ch_url, session, delay=0)
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)
                downloaded += 1
                self.msg_queue.put(("log", f"[{ch_num}/{total}] {ch_title} ✓"))
            except Exception as e:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(f"[下载失败: {e}]\n")
                failed += 1
                self.msg_queue.put(("log", f"[{ch_num}/{total}] 失败: {ch_title} — {e}"))

            self.msg_queue.put(("progress", (downloaded + failed, total,
                               f"{downloaded + failed}/{total}")))

            if delay > 0:
                time.sleep(delay)

        if not part and not self.cancel_flag and filepath_list:
            self.msg_queue.put(("log", f"整合章节..."))
            merge_name = f"{start}-{end}章.txt"
            merge_path = os.path.join(novel_dir, merge_name)
            count = 0
            for fp in filepath_list:
                if not os.path.exists(fp):
                    continue
                from pathlib import Path
                p = Path(fp)
                with open(merge_path, "a", encoding="utf-8") as outfile:
                    outfile.write(f"{p.name[:-4]}\n")
                    outfile.write(p.read_text(encoding="utf-8"))
                    outfile.write("\n\n")
                try:
                    os.unlink(fp)
                except OSError:
                    pass
                count += 1

        self.msg_queue.put(("log", f"\n完成! 保存到: {novel_dir}"))
        self.msg_queue.put(("log", f"已下载: {downloaded}, 失败: {failed}"))
        self.msg_queue.put(("download_done", None))

    def _on_download_finished(self, _):
        self._set_busy(False)
        self.progress["value"] = 100
        self.progress_label.config(text="下载完成")

    def _on_cancel(self):
        if self._cancel_enabled:
            self.cancel_flag = True
            self._log("正在取消...")

    def _browse_output(self):
        path = filedialog.askdirectory(initialdir=self.output_var.get())
        if path:
            self.output_var.set(path)


def main():
    root = tk.Tk()
    app = NovelSpiderApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
