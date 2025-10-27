import os, threading, queue, webbrowser, sys
from pathlib import Path
from datetime import timezone
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from config_loader import load_env_near_exe

env_info = load_env_near_exe(require_local=True,  # require a sibling .env
                             verbose=("--debug-env" in sys.argv))

# --- your existing modules ---
from keyword_trending import co_trending_topics
from analysis import write_csv_topics, write_markdown


def app_dir() -> Path:
    # when frozen, use the folder containing the .exe
    return Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent


APP_DIR = app_dir()

env_path = APP_DIR / ".env"

print("Env Path:" + str(env_path))

# make NLTK use packaged data if present
os.environ.setdefault("NLTK_DATA", str(APP_DIR / "nltk_data"))

APP_TITLE = "NewsTrend – Keyword Co-Trends"
OUTPUT = (APP_DIR / "output")
OUTPUT.mkdir(exist_ok=True)

# --- default knobs (also read from .env if present) ---
LANG = os.getenv("LANG", "en")
DAYS = int(os.getenv("DAYS", "7"))
TOP_K = int(os.getenv("TOP_K", "15"))
HALF_LIFE_H = float(os.getenv("HALF_LIFE_H", "36"))


def _slug(text: str) -> str:
    return "".join(c if c.isalnum() or c in "-_." else "_" for c in text.strip())


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1000x670")
        self.minsize(900, 600)
        self._apply_style()

        self._build_controls()
        self._build_results()
        self._bind_events()

        self.worker_q = queue.Queue()
        self.current_query = None
        self.last_topics_df = None
        self.last_rows = []

    # ------- Apply styles -------
    def _apply_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("vista")
        except tk.TclError:
            style.theme_use("clam")

        base_font = ("Segoe UI", 10) if sys.platform.startswith("win") else ("Helvetica", 11)
        self.option_add("*Font", base_font)
        self.option_add("*TButton.Padding", 8)
        self.option_add("*TMenubutton.Padding", 8)
        self.option_add("*TEntry.Padding", 6)
        self.option_add("*TSpinbox.Padding", 6)

        style.configure("TButton", padding=(10, 6))
        style.map("TButton", relief=[("pressed", "sunken"), ("!pressed", "raised")])

        style.configure("Secondary.TLabel", foreground="#555")
        try:
            style.configure("TPanedwindow", sashrelief="flat", sashwidth=8)
        except tk.TclError:
            pass

        style.configure("Treeview", rowheight=26, borderwidth=0)
        style.configure("Treeview.Heading", font=(base_font[0], base_font[1], "bold"), padding=(8, 6))
        style.map("Treeview.Heading", background=[("active", "#e9eef6")])

        style.configure("Status.TLabel", background="#f5f6f7", relief="groove", anchor="w", padding=(8, 6))

    # ---------- UI ----------
    def _build_controls(self):
        frm = ttk.Frame(self, padding=10)
        frm.pack(fill="x")

        ttk.Label(frm, text="Query:").grid(row=0, column=0, sticky="w")
        self.e_query = ttk.Entry(frm, width=50)
        self.e_query.grid(row=0, column=1, sticky="we", padx=(6, 12))
        self.e_query.insert(0, "")

        ttk.Label(frm, text="Days:").grid(row=0, column=2, sticky="e")
        self.s_days = ttk.Spinbox(frm, from_=1, to=30, width=5)
        self.s_days.set(str(DAYS))
        self.s_days.grid(row=0, column=3, padx=6)

        ttk.Label(frm, text="Top K:").grid(row=0, column=4, sticky="e")
        self.s_topk = ttk.Spinbox(frm, from_=5, to=30, width=5)
        self.s_topk.set(str(TOP_K))
        self.s_topk.grid(row=0, column=5, padx=6)

        ttk.Label(frm, text="Half-life (h):").grid(row=0, column=6, sticky="e")
        self.s_halflife = ttk.Spinbox(frm, from_=6, to=96, width=6, increment=6)
        self.s_halflife.set(str(int(HALF_LIFE_H)))
        self.s_halflife.grid(row=0, column=7, padx=(6, 0))

        frm.grid_columnconfigure(1, weight=1)

        btns = ttk.Frame(self, padding=(10, 0, 10, 10))
        btns.pack(fill="x")

        self.b_run = ttk.Button(btns, text="Run")
        self.b_run.pack(side="left")

        self.b_save_md = ttk.Button(btns, text="Save Markdown", state="disabled")
        self.b_save_md.pack(side="left", padx=8)

        self.b_save_csv = ttk.Button(btns, text="Save CSV", state="disabled")
        self.b_save_csv.pack(side="left")

        self.b_open_out = ttk.Button(btns, text="Open Output Folder")
        self.b_open_out.pack(side="right")

        self.var_status = tk.StringVar(value="Ready.")
        self.lbl_status = ttk.Label(self, textvariable=self.var_status, anchor="w", style="Status.TLabel")
        self.lbl_status.pack(fill="x", padx=10, pady=(0, 6))

    def _sort_tree(self, tree, col, numeric=False):
        items = [(tree.set(k, col), k) for k in tree.get_children("")]
        if numeric:
            def to_num(s):
                try:
                    return float(s)
                except Exception:
                    try:
                        return int(s)
                    except Exception:
                        return 0
            items.sort(key=lambda t: to_num(t[0]))
        else:
            items.sort(key=lambda t: (t[0] is None, str(t[0]).lower()))

        descending = tree.heading(col, "text").endswith(" ▼")
        tree.heading(col, text=col.capitalize() + (" ▲" if descending else " ▼"))

        if descending:
            items.reverse()

        for i, (_, k) in enumerate(items):
            tree.move(k, "", i)

    def _build_results(self):
        pan = ttk.PanedWindow(self, orient=tk.VERTICAL)
        pan.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Top: topics table
        frm_top = ttk.Frame(pan, padding=(0, 4, 0, 4))
        cols = ("topic", "score", "count")
        self.tv_topics = ttk.Treeview(frm_top, columns=cols, show="headings", height=10)
        for c, w, anchor in (
            ("topic", 600, "w"),
            ("score", 120, "e"),
            ("count", 100, "e"),
        ):
            self.tv_topics.heading(c, text=c.capitalize(),
                                   command=lambda col=c: self._sort_tree(self.tv_topics, col, numeric=(col != "topic")))
            self.tv_topics.column(c, width=w, anchor=anchor, stretch=True if c == "topic" else False)

        vs1 = ttk.Scrollbar(frm_top, orient="vertical", command=self.tv_topics.yview)
        self.tv_topics.configure(yscroll=vs1.set, selectmode="browse")
        self.tv_topics.grid(row=0, column=0, sticky="nsew")
        vs1.grid(row=0, column=1, sticky="ns")
        frm_top.grid_rowconfigure(0, weight=1)
        frm_top.grid_columnconfigure(0, weight=1)
        pan.add(frm_top, weight=1)

        # Bottom: articles list
        frm_bottom = ttk.Frame(pan, padding=(0, 4, 0, 0))
        cols2 = ("time", "source", "title")
        self.tv_articles = ttk.Treeview(frm_bottom, columns=cols2, show="headings", height=12)
        for c, w, anchor in (
            ("time", 180, "w"),
            ("source", 140, "w"),
            ("title", 800, "w"),
        ):
            self.tv_articles.heading(c, text=c.capitalize(),
                                     command=lambda col=c: self._sort_tree(self.tv_articles, col, numeric=False))
            self.tv_articles.column(c, width=w, anchor=anchor, stretch=(c == "title"))
        vs2 = ttk.Scrollbar(frm_bottom, orient="vertical", command=self.tv_articles.yview)
        self.tv_articles.configure(yscroll=vs2.set, selectmode="browse")
        self.tv_articles.grid(row=0, column=0, sticky="nsew")
        vs2.grid(row=0, column=1, sticky="ns")
        frm_bottom.grid_rowconfigure(0, weight=1)
        frm_bottom.grid_columnconfigure(0, weight=1)
        pan.add(frm_bottom, weight=2)

    def _bind_events(self):
        self.b_run.configure(command=self._on_run)
        self.b_save_md.configure(command=self._on_save_md)
        self.b_save_csv.configure(command=self._on_save_csv)
        self.b_open_out.configure(command=self._on_open_output)
        self.tv_articles.bind("<Double-1>", self._open_selected_article)

    # ---------- Actions ----------
    def _on_run(self):
        q = self.e_query.get().strip()
        if not q:
            messagebox.showwarning("Input", "Please enter a query.")
            return

        self.current_query = q
        self._set_status(f"Running: {q} …")
        self._set_buttons_busy(True)
        self._clear_tables()

        days = int(self.s_days.get())
        topk = int(self.s_topk.get())
        half_life = float(self.s_halflife.get())

        t = threading.Thread(
            target=self._worker_run_keyword,
            args=(q, days, topk, half_life),
            daemon=True
        )
        t.start()
        self.after(100, self._poll_worker)

    def _worker_run_keyword(self, query, days, topk, half_life):
        try:
            topics_df, rows = co_trending_topics(
                query=query, lang=LANG, days=days,
                half_life_h=half_life, top_k=topk
            )
            rows = sorted(rows, key=lambda r: r.get("published_at") or 0, reverse=True)
            self.worker_q.put(("OK", topics_df, rows))
        except Exception as e:
            self.worker_q.put(("ERR", str(e)))

    def _poll_worker(self):
        try:
            msg = self.worker_q.get_nowait()
        except queue.Empty:
            self.after(100, self._poll_worker)
            return

        if msg[0] == "OK":
            topics_df, rows = msg[1], msg[2]
            self.last_topics_df = topics_df
            self.last_rows = rows
            self._populate_topics(topics_df)
            self._populate_articles(rows)
            n = len(rows)
            if topics_df is not None and not topics_df.empty:
                t1 = topics_df.shape[0]
                self._set_status(f"Done. {t1} topics, {n} articles.")
                self._set_buttons_busy(False, enable_save=True)
            else:
                self._set_status(f"No signal. {n} fetched.")
                self._set_buttons_busy(False, enable_save=False)
        else:
            err = msg[1]
            messagebox.showerror("Error", f"Run failed:\n\n{err}")
            self._set_status("Error.")
            self._set_buttons_busy(False, enable_save=False)

    def _set_buttons_busy(self, busy: bool, enable_save: bool = False):
        self.b_run.configure(state="disabled" if busy else "normal")
        self.b_save_md.configure(state="normal" if enable_save else "disabled")
        self.b_save_csv.configure(state="normal" if enable_save else "disabled")

    def _set_status(self, s: str):
        self.var_status.set(s)

    def _clear_tables(self):
        for tv in (self.tv_topics, self.tv_articles):
            for i in tv.get_children():
                tv.delete(i)

    def _populate_topics(self, df):
        if df is None or df.empty:
            return
        for i, (_, r) in enumerate(df.iterrows()):
            tag = "oddrow" if i % 2 else "evenrow"
            self.tv_topics.insert("", "end",
                                  values=(r["topic"], f"{float(r['score']):.3f}", int(r["count"])),
                                  tags=(tag,))
        self.tv_topics.tag_configure("evenrow", background="#ffffff")
        self.tv_topics.tag_configure("oddrow", background="#f8f9fb")

    def _populate_articles(self, rows):
        for i, r in enumerate(rows[:200]):
            ts = r.get("published_at")
            ts_str = ts.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC") if ts else ""
            src = r.get("source", "")
            title = r.get("title", "")
            tag = "oddrow" if i % 2 else "evenrow"

            iid = self.tv_articles.insert("", "end", values=(ts_str, src, title), tags=(tag,))
            # ✅ store URL along with stripe tag
            self.tv_articles.item(iid, tags=(tag, r.get("url", "")))

        self.tv_articles.tag_configure("evenrow", background="#ffffff")
        self.tv_articles.tag_configure("oddrow", background="#f8f9fb")

    # ✅ robust link opening (new)
    def _open_selected_article(self, _evt=None):
        sel = self.tv_articles.selection()
        if not sel:
            return
        iid = sel[0]
        tags = self.tv_articles.item(iid, "tags") or ()
        for t in tags:
            if isinstance(t, str) and (t.startswith("http://") or t.startswith("https://")):
                webbrowser.open(t)
                return

    def _on_save_md(self):
        if self.last_topics_df is None or not self.last_rows:
            return
        q = self.current_query or "query"
        slug = _slug(q)
        default = OUTPUT / f"coreport_{slug}.md"
        path = filedialog.asksaveasfilename(
            title="Save Markdown",
            defaultextension=".md",
            initialfile=default.name,
            initialdir=str(OUTPUT),
            filetypes=[("Markdown", "*.md")]
        )
        if not path:
            return
        write_markdown(q, self.last_topics_df, self.last_rows, Path(path))
        self._set_status(f"Saved: {path}")

    def _on_save_csv(self):
        if self.last_topics_df is None or self.last_topics_df.empty:
            return
        q = self.current_query or "query"
        slug = _slug(q)
        default = OUTPUT / f"cotopics_{slug}.csv"
        path = filedialog.asksaveasfilename(
            title="Save CSV",
            defaultextension=".csv",
            initialfile=default.name,
            initialdir=str(OUTPUT),
            filetypes=[("CSV", "*.csv")]
        )
        if not path:
            return
        write_csv_topics(self.last_topics_df, Path(path))
        self._set_status(f"Saved: {path}")

    def _on_open_output(self):
        os.startfile(str(OUTPUT))  # Windows convenience


if __name__ == "__main__":
    App().mainloop()
