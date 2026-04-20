use chrono::Local;
use html_scraper::{Html, Selector};
use regex::Regex;
use reqwest::Client;
use serde::Serialize;

#[derive(Serialize, Default, Clone)]
pub struct FilmData {
    pub url: String,
    pub title: String,
    pub year: String,
    pub directors: Vec<String>,
    pub cast: Vec<String>,
    pub rating: String,
    pub runtime: String,
    pub genres: Vec<String>,
    pub synopsis: String,
    pub tagline: String,
}

const USER_AGENT: &str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) \
    AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36";

pub fn is_valid_film_url(url: &str) -> bool {
    let normalized = format!("{}/", url.trim().trim_end_matches('/'));
    Regex::new(r"(?i)^https?://letterboxd\.com/film/[^/\s]+/$")
        .unwrap()
        .is_match(&normalized)
}

pub async fn scrape_film(url: &str) -> Result<FilmData, String> {
    let url = format!("{}/", url.trim().trim_end_matches('/'));

    let client = Client::builder()
        .user_agent(USER_AGENT)
        .build()
        .map_err(|e| format!("Client error: {e}"))?;

    let resp = client
        .get(&url)
        .header("Accept-Language", "en-US,en;q=0.9")
        .send()
        .await
        .map_err(|e| format!("Request failed: {e}"))?;

    if resp.status().as_u16() == 404 {
        return Err("Film page not found — check the URL.".into());
    }
    if !resp.status().is_success() {
        return Err(format!("HTTP {}", resp.status()));
    }

    let html = resp.text().await.map_err(|e| e.to_string())?;
    let doc = Html::parse_document(&html);

    Ok(FilmData {
        title: parse_title(&doc),
        year: parse_year(&doc),
        directors: parse_directors(&doc),
        cast: parse_cast(&doc),
        rating: parse_rating(&doc),
        runtime: parse_runtime(&doc),
        genres: parse_genres(&doc),
        synopsis: parse_synopsis(&doc),
        tagline: parse_tagline(&doc),
        url,
    })
}

// ── field parsers ──────────────────────────────────────────────────────────────

fn meta_content(doc: &Html, selector: &str) -> String {
    Selector::parse(selector)
        .ok()
        .and_then(|sel| doc.select(&sel).next())
        .and_then(|el| el.value().attr("content"))
        .map(|s| s.trim().to_string())
        .unwrap_or_default()
}

fn parse_title(doc: &Html) -> String {
    let content = meta_content(doc, r#"meta[property="og:title"]"#);
    if content.is_empty() {
        return String::new();
    }
    Regex::new(r"\s*\(\d{4}\)\s*$")
        .unwrap()
        .replace(&content, "")
        .trim()
        .to_string()
}

fn parse_year(doc: &Html) -> String {
    let content = meta_content(doc, r#"meta[property="og:title"]"#);
    if !content.is_empty() {
        if let Some(caps) = Regex::new(r"\((\d{4})\)\s*$").unwrap().captures(&content) {
            return caps[1].to_string();
        }
    }
    Selector::parse("a[href*='/films/year/']")
        .ok()
        .and_then(|sel| {
            doc.select(&sel).find(|el| {
                let t = el.text().collect::<String>();
                Regex::new(r"^\d{4}$").unwrap().is_match(t.trim())
            })
        })
        .map(|el| el.text().collect::<String>().trim().to_string())
        .unwrap_or_default()
}

fn parse_directors(doc: &Html) -> Vec<String> {
    let Ok(sel) = Selector::parse("a[href*='/director/']") else {
        return vec![];
    };
    let span_sel = Selector::parse("span.prettify").ok();
    let mut seen: Vec<String> = Vec::new();

    for el in doc.select(&sel) {
        let name = span_sel
            .as_ref()
            .and_then(|s| el.select(s).next())
            .map(|s| s.text().collect::<String>())
            .unwrap_or_else(|| el.text().collect::<String>());
        let name = name.trim().to_string();
        if !name.is_empty() && !seen.contains(&name) {
            seen.push(name);
        }
    }
    seen
}

fn parse_cast(doc: &Html) -> Vec<String> {
    let Ok(sel) = Selector::parse("a[href*='/actor/']") else {
        return vec![];
    };
    doc.select(&sel)
        .map(|el| el.text().collect::<String>().trim().to_string())
        .filter(|s| !s.is_empty())
        .take(5)
        .collect()
}

fn parse_rating(doc: &Html) -> String {
    let r = meta_content(doc, r#"meta[name="twitter:data2"]"#);
    if !r.is_empty() {
        return r;
    }
    Selector::parse("[itemprop='ratingValue']")
        .ok()
        .and_then(|sel| doc.select(&sel).next())
        .and_then(|el| el.value().attr("content"))
        .map(|s| s.trim().to_string())
        .unwrap_or_default()
}

fn parse_runtime(doc: &Html) -> String {
    let Ok(sel) = Selector::parse("p.text-footer") else {
        return String::new();
    };
    let Some(el) = doc.select(&sel).next() else {
        return String::new();
    };
    let mut text = el
        .text()
        .collect::<Vec<_>>()
        .join(" ")
        .replace('\u{00a0}', " ");
    text = text.trim().to_string();
    for marker in &["More at", "Also on"] {
        if let Some(idx) = text.find(marker) {
            text = text[..idx].trim().to_string();
        }
    }
    text
}

fn parse_genres(doc: &Html) -> Vec<String> {
    let mut genres: Vec<String> = Vec::new();

    if let Ok(sel) = Selector::parse("#tab-genres a[href*='/films/genre/']") {
        for el in doc.select(&sel) {
            let g = el.text().collect::<String>().trim().to_string();
            if !g.is_empty() && !genres.contains(&g) {
                genres.push(g);
            }
        }
    }

    if genres.is_empty() {
        if let Ok(sel) = Selector::parse("a[href*='/films/genre/']") {
            for el in doc.select(&sel) {
                let g = el.text().collect::<String>().trim().to_string();
                if !g.is_empty() && !genres.contains(&g) {
                    genres.push(g);
                }
            }
        }
    }
    genres
}

fn parse_synopsis(doc: &Html) -> String {
    if let Ok(sel) = Selector::parse("[itemprop='description']") {
        if let Some(el) = doc.select(&sel).next() {
            let t = el.text().collect::<String>().trim().to_string();
            if !t.is_empty() {
                return t;
            }
        }
    }
    meta_content(doc, r#"meta[name="description"]"#)
}

fn parse_tagline(doc: &Html) -> String {
    meta_content(doc, r#"meta[property="og:description"]"#)
}

// ── markdown renderer ──────────────────────────────────────────────────────────

pub fn to_markdown(film: &FilmData) -> String {
    let today = Local::now().format("%Y-%m-%d").to_string();
    let mut lines: Vec<String> = Vec::new();

    let mut heading = format!("# {}", film.title);
    if !film.year.is_empty() {
        heading.push_str(&format!(" ({})", film.year));
    }
    lines.push(heading);
    lines.push(String::new());

    if !film.tagline.is_empty() && film.tagline != film.synopsis {
        lines.push(format!("*{}*", film.tagline));
        lines.push(String::new());
    }

    if !film.directors.is_empty() {
        let label = if film.directors.len() > 1 { "Directors" } else { "Director" };
        lines.push(format!("**{}:** {}", label, film.directors.join(", ")));
    }
    if !film.runtime.is_empty() {
        lines.push(format!("**Runtime:** {}", film.runtime));
    }
    if !film.rating.is_empty() {
        lines.push(format!("**Rating:** {}", film.rating));
    }
    if !film.genres.is_empty() {
        lines.push(format!("**Genres:** {}", film.genres.join(", ")));
    }

    if !film.cast.is_empty() {
        lines.push(String::new());
        lines.push("## Cast".into());
        for actor in &film.cast {
            lines.push(format!("- {actor}"));
        }
    }

    if !film.synopsis.is_empty() {
        lines.push(String::new());
        lines.push("## Synopsis".into());
        lines.push(film.synopsis.clone());
    }

    lines.push(String::new());
    lines.push("---".into());
    lines.push(format!("*[View on Letterboxd]({})*  ", film.url));
    lines.push(format!("*Scraped: {today}*"));

    lines.join("\n")
}
