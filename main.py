import threading
import re
import os
from datetime import date
from pathlib import Path

import requests
from bs4 import BeautifulSoup
import customtkinter as ctk

# ── theme ──────────────────────────────────────────────────────────────────────

BG       = "#14181c"
SURFACE  = "#1f2630"
BORDER   = "#2c3440"
ACCENT   = "#00c030"
ACCENT_H = "#00a828"
TEXT     = "#c8d8e8"
MUTED    = "#667788"
DANGER   = "#e05a5a"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

# ── scraper ────────────────────────────────────────────────────────────────────

def is_valid_url(url: str) -> bool:
    normalized = url.strip().rstrip("/") + "/"
    return bool(re.match(r"(?i)^https?://letterboxd\.com/film/[^/\s]+/$", normalized))


def scrape_film(url: str) -> dict:
    url = url.strip().rstrip("/") + "/"
    resp = requests.get(url, headers={"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9"}, timeout=15)
    if resp.status_code == 404:
        raise ValueError("Film page not found — check the URL.")
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    def meta(prop=None, name=None):
        tag = soup.find("meta", property=prop) if prop else soup.find("meta", attrs={"name": name})
        return (tag.get("content") or "").strip() if tag else ""

    og_title = meta(prop="og:title")
    title = re.sub(r"\s*\(\d{4}\)\s*$", "", og_title).strip()
    year_m = re.search(r"\((\d{4})\)\s*$", og_title)
    year = year_m.group(1) if year_m else ""

    directors = []
    for a in soup.select("a[href*='/director/']"):
        span = a.find("span", class_="prettify")
        name = (span.get_text() if span else a.get_text()).strip()
        if name and name not in directors:
            directors.append(name)

    cast = []
    for a in soup.select("a[href*='/actor/']"):
        name = a.get_text().strip()
        if name and name not in cast:
            cast.append(name)
        if len(cast) >= 5:
            break

    rating = meta(name="twitter:data2")
    if not rating:
        el = soup.find(itemprop="ratingValue")
        rating = (el.get("content") or "").strip() if el else ""

    runtime = ""
    footer = soup.find("p", class_="text-footer")
    if footer:
        runtime = " ".join(footer.get_text(" ").split()).strip()
        for marker in ("More at", "Also on"):
            idx = runtime.find(marker)
            if idx != -1:
                runtime = runtime[:idx].strip()

    genres = []
    for a in soup.select("#tab-genres a[href*='/films/genre/']"):
        g = a.get_text().strip()
        if g and g not in genres:
            genres.append(g)
    if not genres:
        for a in soup.select("a[href*='/films/genre/']"):
            g = a.get_text().strip()
            if g and g not in genres:
                genres.append(g)

    synopsis = ""
    el = soup.find(itemprop="description")
    if el:
        synopsis = el.get_text().strip()
    if not synopsis:
        synopsis = meta(name="description")

    tagline = meta(prop="og:description")

    studios = []
    for a in soup.select("a[href*='/studio/']"):
        s = a.get_text().strip()
        if s and s not in studios:
            studios.append(s)

    return dict(url=url, title=title, year=year, directors=directors, cast=cast,
                rating=rating, runtime=runtime, genres=genres, synopsis=synopsis,
                tagline=tagline, studios=studios)


def to_markdown(film: dict) -> str:
    today = date.today().isoformat()
    lines = []

    heading = f"# {film['title']}"
    if film["year"]:
        heading += f" ({film['year']})"
    lines += [heading, ""]

    if film["tagline"] and film["tagline"] != film["synopsis"]:
        lines += [f"*{film['tagline']}*", ""]

    if film["directors"]:
        label = "Directors" if len(film["directors"]) > 1 else "Director"
        lines.append(f"**{label}:** {', '.join(film['directors'])}")
    if film["runtime"]:
        lines.append(f"**Runtime:** {film['runtime']}")
    if film["rating"]:
        lines.append(f"**Rating:** {film['rating']}")
    if film["genres"]:
        lines.append(f"**Genres:** {', '.join(film['genres'])}")
    if film["studios"]:
        label = "Studios" if len(film["studios"]) > 1 else "Studio"
        lines.append(f"**{label}:** {', '.join(film['studios'])}")

    if film["cast"]:
        lines += ["", "## Cast"]
        for actor in film["cast"]:
            lines.append(f"- {actor}")

    if film["synopsis"]:
        lines += ["", "## Synopsis", film["synopsis"]]

    lines += ["", "---", f"*[View on Letterboxd]({film['url']})*  ", f"*Scraped: {today}*"]
    return "\n".join(lines)


def slugify(s: str) -> str:
    return re.sub(r"^-|-$", "", re.sub(r"[^a-z0-9]+", "-", s.lower()))

# ── app ────────────────────────────────────────────────────────────────────────

class BoxdBot(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        self.title("BoxdBot")
        self.geometry("780x680")
        self.minsize(600, 560)
        self.configure(fg_color=BG)

        self._md = ""
        self._filename = "film"
        self._build_ui()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        # ── header ──
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, pady=(40, 28), padx=24)

        title_frame = ctk.CTkFrame(header, fg_color="transparent")
        title_frame.pack()
        ctk.CTkLabel(title_frame, text="Boxd", font=("Segoe UI", 30, "bold"), text_color=TEXT).pack(side="left")
        ctk.CTkLabel(title_frame, text="Bot", font=("Segoe UI", 30, "bold"), text_color=ACCENT).pack(side="left")
        ctk.CTkLabel(header, text="Paste a Letterboxd film URL — get a Markdown file.",
                     font=("Segoe UI", 13), text_color=MUTED).pack(pady=(4, 0))

        # ── input card ──
        input_card = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=10,
                                  border_width=1, border_color=BORDER)
        input_card.grid(row=1, column=0, sticky="ew", padx=60, pady=(0, 6))
        input_card.grid_columnconfigure(0, weight=1)

        row = ctk.CTkFrame(input_card, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=16)
        row.grid_columnconfigure(0, weight=1)

        self.url_entry = ctk.CTkEntry(
            row, placeholder_text="https://letterboxd.com/film/inception/",
            font=("Segoe UI", 13), height=40, corner_radius=8,
            fg_color=BG, border_color=BORDER, border_width=1,
            text_color=TEXT, placeholder_text_color=MUTED,
        )
        self.url_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.url_entry.bind("<Return>", lambda _: self._start_scrape())

        self.scrape_btn = ctk.CTkButton(
            row, text="Scrape", width=100, height=40, corner_radius=8,
            font=("Segoe UI", 13, "bold"), fg_color=ACCENT, hover_color=ACCENT_H,
            text_color="#000", command=self._start_scrape,
        )
        self.scrape_btn.grid(row=0, column=1)

        self.error_label = ctk.CTkLabel(input_card, text="", font=("Segoe UI", 12),
                                        text_color=DANGER, wraplength=580)
        self.error_label.pack(padx=20, pady=(0, 4))

        # ── spinner ──
        self.spinner_label = ctk.CTkLabel(self, text="", font=("Segoe UI", 12), text_color=MUTED)
        self.spinner_label.grid(row=2, column=0, pady=(2, 0))

        # ── result card ──
        result_card = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=10,
                                   border_width=1, border_color=BORDER)
        result_card.grid(row=3, column=0, sticky="nsew", padx=60, pady=(10, 40))
        result_card.grid_columnconfigure(0, weight=1)
        result_card.grid_rowconfigure(1, weight=1)

        result_header = ctk.CTkFrame(result_card, fg_color="transparent")
        result_header.grid(row=0, column=0, sticky="ew", padx=20, pady=(14, 8))
        result_header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(result_header, text="MARKDOWN PREVIEW",
                     font=("Segoe UI", 10, "bold"), text_color=MUTED).grid(row=0, column=0, sticky="w")

        btn_frame = ctk.CTkFrame(result_header, fg_color="transparent")
        btn_frame.grid(row=0, column=1)

        self.copy_btn = ctk.CTkButton(
            btn_frame, text="Copy", width=80, height=30, corner_radius=6,
            font=("Segoe UI", 12), fg_color="transparent", border_width=1,
            border_color=BORDER, text_color=TEXT, hover_color=BORDER,
            command=self._copy,
        )
        self.copy_btn.pack(side="left", padx=(0, 6))

        self.dl_btn = ctk.CTkButton(
            btn_frame, text="Download .md", width=110, height=30, corner_radius=6,
            font=("Segoe UI", 12), fg_color="transparent", border_width=1,
            border_color=BORDER, text_color=TEXT, hover_color=BORDER,
            command=self._download,
        )
        self.dl_btn.pack(side="left")

        self.output = ctk.CTkTextbox(
            result_card, font=("Cascadia Code", 12), fg_color=BG,
            border_color=BORDER, border_width=1, corner_radius=8,
            text_color=TEXT, wrap="word", state="disabled",
        )
        self.output.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))

    # ── actions ────────────────────────────────────────────────────────────────

    def _start_scrape(self):
        url = self.url_entry.get().strip()
        if not url:
            return
        self._set_error("")
        if not is_valid_url(url):
            self._set_error("Not a valid Letterboxd film URL.\nExpected: https://letterboxd.com/film/<slug>/")
            return

        self.scrape_btn.configure(state="disabled")
        self._set_output("")
        self._set_spinner("Scraping film data…")
        threading.Thread(target=self._scrape_thread, args=(url,), daemon=True).start()

    def _scrape_thread(self, url: str):
        try:
            film = scrape_film(url)
            md = to_markdown(film)
            self._md = md
            self._filename = slugify(film["title"] or "film")
            self.after(0, lambda: self._on_success(md))
        except Exception as e:
            self.after(0, lambda: self._on_error(str(e)))

    def _on_success(self, md: str):
        self._set_spinner("")
        self.scrape_btn.configure(state="normal")
        self._set_output(md)

    def _on_error(self, msg: str):
        self._set_spinner("")
        self.scrape_btn.configure(state="normal")
        self._set_error(msg)

    def _copy(self):
        if not self._md:
            return
        self.clipboard_clear()
        self.clipboard_append(self._md)
        self.copy_btn.configure(text="Copied!")
        self.after(1500, lambda: self.copy_btn.configure(text="Copy"))

    def _download(self):
        if not self._md:
            return
        downloads = Path.home() / "Downloads"
        path = downloads / f"{self._filename}.md"
        path.write_text(self._md, encoding="utf-8")
        self.dl_btn.configure(text="Saved ✓")
        self.after(2000, lambda: self.dl_btn.configure(text="Download .md"))

    # ── helpers ────────────────────────────────────────────────────────────────

    def _set_error(self, msg: str):
        self.error_label.configure(text=msg)

    def _set_spinner(self, msg: str):
        self.spinner_label.configure(text=msg)

    def _set_output(self, text: str):
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        if text:
            self.output.insert("1.0", text)
        self.output.configure(state="disabled")


if __name__ == "__main__":
    app = BoxdBot()
    app.mainloop()
