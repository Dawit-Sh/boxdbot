import re
import requests
from bs4 import BeautifulSoup
from dataclasses import dataclass, field
from datetime import date

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

FILM_URL_RE = re.compile(r"^https?://letterboxd\.com/film/[^/\s]+/?$")


@dataclass
class FilmData:
    url: str
    title: str = ""
    year: str = ""
    directors: list[str] = field(default_factory=list)
    cast: list[str] = field(default_factory=list)
    rating: str = ""
    runtime: str = ""
    genres: list[str] = field(default_factory=list)
    synopsis: str = ""
    tagline: str = ""


def is_valid_film_url(url: str) -> bool:
    return bool(FILM_URL_RE.match(url.strip().rstrip("/") + "/"))


def scrape_film(url: str, timeout: int = 15) -> FilmData:
    url = url.strip().rstrip("/") + "/"
    resp = requests.get(url, headers=HEADERS, timeout=timeout)
    if resp.status_code == 404:
        raise ValueError("Film page not found — check the URL.")
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    return FilmData(
        url=url,
        title=_title(soup),
        year=_year(soup),
        directors=_directors(soup),
        cast=_cast(soup),
        rating=_rating(soup),
        runtime=_runtime(soup),
        genres=_genres(soup),
        synopsis=_synopsis(soup),
        tagline=_tagline(soup),
    )


# ── field parsers ─────────────────────────────────────────────────────────────

def _title(soup: BeautifulSoup) -> str:
    # og:title contains "Title (Year)" — split off the year
    meta = soup.find("meta", property="og:title")
    if meta and meta.get("content"):
        content = meta["content"].strip()
        # Strip trailing " (YYYY)" if present
        return re.sub(r"\s*\(\d{4}\)\s*$", "", content).strip()
    return ""


def _year(soup: BeautifulSoup) -> str:
    # og:title contains "Title (Year)"
    meta = soup.find("meta", property="og:title")
    if meta and meta.get("content"):
        m = re.search(r"\((\d{4})\)\s*$", meta["content"])
        if m:
            return m.group(1)
    # fallback: any bare 4-digit year link near the header
    for a in soup.find_all("a", href=re.compile(r"/films/year/\d{4}/")):
        text = a.get_text(strip=True)
        if re.match(r"^\d{4}$", text):
            return text
    return ""


def _directors(soup: BeautifulSoup) -> list[str]:
    # Primary: contributor links to /director/
    seen: dict[str, None] = {}
    for a in soup.select("a[href*='/director/']"):
        # Grab the visible text; skip nav/menu items that say "Director" generically
        inner = a.find("span", class_="prettify") or a
        name = inner.get_text(strip=True)
        if name and name not in seen:
            seen[name] = None
    return list(seen.keys())


def _cast(soup: BeautifulSoup) -> list[str]:
    actors = [a.get_text(strip=True) for a in soup.select("a[href*='/actor/']")]
    return [a for a in actors if a][:5]


def _rating(soup: BeautifulSoup) -> str:
    meta = soup.find("meta", {"name": "twitter:data2"})
    if meta and meta.get("content"):
        return meta["content"].strip()
    el = soup.find(itemprop="ratingValue")
    return el["content"].strip() if el and el.get("content") else ""


def _runtime(soup: BeautifulSoup) -> str:
    el = soup.find("p", class_="text-footer")
    if not el:
        return ""
    text = el.get_text(" ", strip=True).replace("\xa0", " ")
    # Strip trailing "More at IMDb..." link text
    for marker in ("More at", "Also on"):
        idx = text.find(marker)
        if idx != -1:
            text = text[:idx].strip()
    return text


def _genres(soup: BeautifulSoup) -> list[str]:
    genres = [a.get_text(strip=True) for a in soup.select("#tab-genres a[href*='/films/genre/']")]
    if not genres:
        genres = [a.get_text(strip=True) for a in soup.select("a[href*='/films/genre/']")]
    return list(dict.fromkeys(g for g in genres if g))  # dedup, preserve order


def _synopsis(soup: BeautifulSoup) -> str:
    el = soup.find(itemprop="description")
    if el:
        return el.get_text(strip=True)
    meta = soup.find("meta", {"name": "description"})
    return meta["content"].strip() if meta and meta.get("content") else ""


def _tagline(soup: BeautifulSoup) -> str:
    el = soup.find("meta", property="og:description")
    return el["content"].strip() if el and el.get("content") else ""


# ── markdown renderer ──────────────────────────────────────────────────────────

def to_markdown(film: FilmData) -> str:
    lines: list[str] = []

    heading = f"# {film.title}"
    if film.year:
        heading += f" ({film.year})"
    lines += [heading, ""]

    if film.tagline and film.tagline != film.synopsis:
        lines += [f"*{film.tagline}*", ""]

    meta_rows = []
    if film.directors:
        label = "Directors" if len(film.directors) > 1 else "Director"
        meta_rows.append(f"**{label}:** {', '.join(film.directors)}")
    if film.runtime:
        meta_rows.append(f"**Runtime:** {film.runtime}")
    if film.rating:
        meta_rows.append(f"**Rating:** {film.rating}")
    if film.genres:
        meta_rows.append(f"**Genres:** {', '.join(film.genres)}")
    lines += meta_rows

    if film.cast:
        lines += ["", "## Cast", *[f"- {actor}" for actor in film.cast]]

    if film.synopsis:
        lines += ["", "## Synopsis", film.synopsis]

    lines += [
        "",
        "---",
        f"*[View on Letterboxd]({film.url})*  ",
        f"*Scraped: {date.today().isoformat()}*",
    ]

    return "\n".join(lines)
