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


class NovelSpiderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("小说下载器")
        self.root.geometry("620x480")
        self.root.minsize(560, 380)

        self.config = Config()
        self.msg_queue = queue.Queue()
        self.chapters = []
        self.cancel_flag = False
        self.downloading = False

        self._build_ui()
        self._poll_queue()

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        # --- 主题色板 ---
        BG        = "#f0f2f5"
        ACCENT    = "#4361ee"
        ACCENT_H  = "#3a56d4"
        TEXT      = "#000000"
        TEXT_SEC  = "#6b7280"
        BORDER    = "#d1d5db"
        SELECT_BG = "#e0e7ff"
        WHITE     = "#ffffff"
        LOG_BG    = "#1e1e2e"
        LOG_FG    = "#cdd6f4"
        TREE_HEAD = "#4361ee"
        TREE_HEAD_FG = "#ffffff"
        ROW_ALT   = "#f8f9fc"

        FONT      = ("Microsoft YaHei", 9)
        FONT_BOLD = ("Microsoft YaHei", 9, "bold")
        FONT_SM   = ("Microsoft YaHei", 8)
        FONT_LOG  = ("Consolas", 8)

        self._bg = BG
        self._log_bg = LOG_BG
        self._log_fg = LOG_FG
        self._row_alt = ROW_ALT
        self.root.configure(bg=BG)

        style = ttk.Style()
        available = style.theme_names()
        for theme in ("vista", "xpnative", "clam", "alt"):
            if theme in available:
                style.theme_use(theme)
                break

        style.configure(".", font=FONT, background=BG, foreground=TEXT)

        # LabelFrame
        style.configure("TLabelframe", background=BG, borderwidth=1, relief="solid")
        style.configure("TLabelframe.Label", font=FONT_BOLD, background=BG, foreground=ACCENT)

        # Label
        style.configure("TLabel", background=BG, foreground=TEXT, font=FONT)
        style.configure("Progress.TLabel", background=BG, foreground=TEXT_SEC, font=FONT_SM)

        # Button
        style.configure("Accent.TButton", font=FONT_BOLD, background=ACCENT, foreground="#000000",
                         borderwidth=0, padding=(10, 4))
        style.map("Accent.TButton",
                   background=[("active", ACCENT_H), ("disabled", BORDER)],
                   foreground=[("disabled", TEXT_SEC)])
        style.configure("TButton", font=FONT, padding=(8, 3))
        style.map("TButton", background=[("active", SELECT_BG)])

        # Entry
        style.configure("TEntry", fieldbackground=WHITE, borderwidth=1, relief="solid", padding=3)

        # Combobox
        style.configure("TCombobox", fieldbackground=WHITE, borderwidth=1, padding=3)

        # Checkbutton
        style.configure("TCheckbutton", background=BG, font=FONT)

        # Treeview
        style.configure("Treeview", font=FONT_SM, background=WHITE, fieldbackground=WHITE,
                         foreground=TEXT, rowheight=22, borderwidth=0)
        style.configure("Treeview.Heading", font=FONT_BOLD, background=TREE_HEAD,
                         foreground=TREE_HEAD_FG, borderwidth=0, padding=(6, 4))
        style.map("Treeview",
                   background=[("selected", SELECT_BG)],
                   foreground=[("selected", TEXT)])
        style.map("Treeview.Heading", background=[("active", ACCENT_H)])

        # Progressbar
        style.configure("TProgressbar", troughcolor=BORDER, background=ACCENT, borderwidth=0, thickness=8)

        # Scrollbar
        style.configure("TScrollbar", background=BORDER, borderwidth=0, arrowsize=12)

        # ===== 可滚动 Canvas =====
        self._canvas = tk.Canvas(self.root, bg=BG, highlightthickness=0)
        vscroll = ttk.Scrollbar(self.root, orient="vertical", command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=vscroll.set)

        vscroll.pack(side="right", fill="y")
        self._canvas.pack(side="left", fill="both", expand=True)

        container = ttk.Frame(self._canvas, style="TFrame")
        self._canvas_window = self._canvas.create_window((0, 0), window=container, anchor="nw")

        def _on_frame_configure(event):
            self._canvas.configure(scrollregion=self._canvas.bbox("all"))
        container.bind("<Configure>", _on_frame_configure)

        def _on_canvas_configure(event):
            # 让内部 frame 宽度始终跟随 canvas
            self._canvas.itemconfig(self._canvas_window, width=event.width)
        self._canvas.bind("<Configure>", _on_canvas_configure)

        # 鼠标滚轮
        def _on_mousewheel(event):
            self._canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        self._canvas.bind_all("<MouseWheel>", _on_mousewheel)

        pad = {"padx": 6, "pady": 3}

        # --- 搜索区 ---
        frame_search = ttk.LabelFrame(container, text="搜索小说")
        frame_search.pack(fill="x", **pad)

        self.search_var = tk.StringVar()
        ttk.Entry(frame_search, textvariable=self.search_var).pack(
            side="left", fill="x", expand=True, padx=(4, 2), pady=3
        )
        self.search_var.trace_add("write", lambda *_: None)

        self.site_var = tk.StringVar(value="全部站点")
        site_list = ["全部站点"] + list_sites()
        ttk.Combobox(
            frame_search, textvariable=self.site_var,
            values=site_list, state="readonly", width=16
        ).pack(side="left", padx=2, pady=3)

        ttk.Button(frame_search, text="搜索", command=self._on_search, style="Accent.TButton").pack(
            side="left", padx=(2, 4), pady=3
        )
        self.root.bind("<Return>", lambda e: self._on_search())

        # --- 搜索结果 ---
        frame_results = ttk.LabelFrame(container, text="搜索结果（双击填入 URL）")
        frame_results.pack(fill="x", **pad)

        cols = ("title", "author", "site")
        self.result_tree = ttk.Treeview(
            frame_results, columns=cols, show="headings", height=5
        )
        self.result_tree.heading("title", text="书名")
        self.result_tree.heading("author", text="作者")
        self.result_tree.heading("site", text="站点")
        self.result_tree.column("title", width=300)
        self.result_tree.column("author", width=120)
        self.result_tree.column("site", width=120)
        self.result_tree.pack(fill="x", padx=4, pady=2)
        self.result_tree.bind("<Double-1>", self._on_result_double_click)

        # --- URL 输入 ---
        frame_url = ttk.LabelFrame(container, text="小说目录页 URL")
        frame_url.pack(fill="x", **pad)

        self.url_var = tk.StringVar()
        ttk.Entry(frame_url, textvariable=self.url_var).pack(
            side="left", fill="x", expand=True, padx=(4, 2), pady=3
        )
        ttk.Button(frame_url, text="获取章节", command=self._on_fetch_chapters, style="Accent.TButton").pack(
            side="left", padx=(2, 4), pady=3
        )

        # --- 章节列表 ---
        frame_chapters = ttk.LabelFrame(container, text="章节列表")
        frame_chapters.pack(fill="x", **pad)

        ch_cols = ("num", "title")
        self.chapter_tree = ttk.Treeview(
            frame_chapters, columns=ch_cols, show="headings", height=6
        )
        self.chapter_tree.heading("num", text="#", anchor="w")
        self.chapter_tree.heading("title", text="章节标题")
        self.chapter_tree.column("num", width=50, minwidth=40)
        self.chapter_tree.column("title", width=600)
        self.chapter_tree.pack(fill="both", expand=True, padx=4, pady=2)

        range_frame = ttk.Frame(frame_chapters)
        range_frame.pack(fill="x", padx=4, pady=(0, 2))

        ttk.Label(range_frame, text="起始:").pack(side="left")
        self.start_var = tk.StringVar(value="1")
        ttk.Entry(range_frame, textvariable=self.start_var, width=6).pack(
            side="left", padx=(2, 10)
        )
        ttk.Label(range_frame, text="结束:").pack(side="left")
        self.end_var = tk.StringVar(value="0")
        ttk.Entry(range_frame, textvariable=self.end_var, width=6).pack(
            side="left", padx=(2, 10)
        )
        ttk.Button(range_frame, text="全选", command=self._select_all_chapters).pack(
            side="left", padx=4
        )

        # --- 下载设置 ---
        frame_settings = ttk.LabelFrame(container, text="下载设置")
        frame_settings.pack(fill="x", **pad)

        row1 = ttk.Frame(frame_settings)
        row1.pack(fill="x", padx=4, pady=2)
        ttk.Label(row1, text="输出目录:").pack(side="left")
        self.output_var = tk.StringVar(value=self.config.output_dir)
        ttk.Entry(row1, textvariable=self.output_var).pack(
            side="left", fill="x", expand=True, padx=(4, 2)
        )
        ttk.Button(row1, text="浏览...", command=self._browse_output).pack(
            side="left", padx=(2, 0)
        )

        row2 = ttk.Frame(frame_settings)
        row2.pack(fill="x", padx=4, pady=2)
        ttk.Label(row2, text="请求间隔(秒):").pack(side="left")
        self.delay_var = tk.StringVar(value=str(self.config.delay))
        ttk.Entry(row2, textvariable=self.delay_var, width=6).pack(
            side="left", padx=(4, 12)
        )
        self.part_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(row2, text="逐章保存", variable=self.part_var).pack(
            side="left", padx=8
        )
        self.resume_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(row2, text="断点续传", variable=self.resume_var).pack(
            side="left", padx=8
        )

        # --- 操作按钮 ---
        frame_btns = ttk.Frame(container)
        frame_btns.pack(fill="x", **pad)

        self.btn_download = ttk.Button(
            frame_btns, text="开始下载", command=self._on_download, style="Accent.TButton"
        )
        self.btn_download.pack(side="left", padx=6)
        self.btn_cancel = ttk.Button(
            frame_btns, text="取消", command=self._on_cancel, state="disabled"
        )
        self.btn_cancel.pack(side="left", padx=6)

        # --- 进度 & 日志 ---
        frame_progress = ttk.LabelFrame(container, text="进度")
        frame_progress.pack(fill="x", **pad)

        self.progress = ttk.Progressbar(frame_progress, mode="determinate")
        self.progress.pack(fill="x", padx=4, pady=(4, 1))

        self.progress_label = ttk.Label(frame_progress, text="就绪", style="Progress.TLabel")
        self.progress_label.pack(fill="x", padx=4)

        self.log_text = tk.Text(frame_progress, height=5, state="disabled",
                                wrap="word", font=("Consolas", 8),
                                bg=self._log_bg, fg=self._log_fg,
                                insertbackground=self._log_fg,
                                selectbackground="#4361ee", selectforeground="#ffffff",
                                borderwidth=0, highlightthickness=1,
                                highlightbackground=BORDER, padx=6, pady=4)
        log_scrollbar = ttk.Scrollbar(
            frame_progress, orient="vertical", command=self.log_text.yview
        )
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        self.log_text.pack(side="left", fill="both", expand=True, padx=(4, 0), pady=(1, 4))
        log_scrollbar.pack(side="right", fill="y", padx=(0, 4), pady=(1, 4))

    # -------------------------------------------------------------- helpers
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
        self.btn_download.config(state="disabled" if busy else "normal")
        self.btn_cancel.config(state="normal" if busy else "disabled")

    # ------------------------------------------------------------- 搜索
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

    # ------------------------------------------------------------- 获取章节
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

    # ------------------------------------------------------------- 下载
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

        # reuse novel info we already have
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

        # 合并为单个文件
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
        self.cancel_flag = True
        self._log("正在取消...")

    # ------------------------------------------------------------- 浏览目录
    def _browse_output(self):
        path = filedialog.askdirectory(initialdir=self.output_var.get())
        if path:
            self.output_var.set(path)


def main():
    root = tk.Tk()
    # 尝试设置现代化主题
    try:
        style = ttk.Style()
        available = style.theme_use()
        for theme in ("vista", "xpnative", "clam", "alt"):
            if theme in style.theme_names():
                style.theme_use(theme)
                break
    except Exception:
        pass
    app = NovelSpiderApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
