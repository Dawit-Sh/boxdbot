# BoxdBot

A desktop app that scrapes a [Letterboxd](https://letterboxd.com) film page and exports the metadata as a Markdown file.

Paste a film URL, get a formatted `.md` file saved to your Downloads folder.

---

## Features

- Accepts any `letterboxd.com/film/<slug>/` URL
- Extracts title, year, director(s), runtime, rating, genres, top cast, synopsis, and tagline
- Live Markdown preview
- Copy to clipboard or save directly to Downloads
- Dark-themed UI with responsive background scraping (UI never freezes)

## Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3 |
| GUI | [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) |
| Scraping | BeautifulSoup4 + requests |

## Requirements

- Python 3.7+
- pip

## Setup

```bash
# Clone the repo
git clone https://github.com/Dawit-Sh/boxdbot.git
cd boxdbot

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Run

```bash
python main.py
```

## Usage

1. Paste a Letterboxd film URL (e.g. `https://letterboxd.com/film/oppenheimer/`)
2. Click **Scrape**
3. Preview the generated Markdown in the result panel
4. Click **Copy** to copy to clipboard, or **Download** to save a `.md` file to your Downloads folder
