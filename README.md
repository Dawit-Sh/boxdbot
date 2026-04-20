# BoxdBot

A Flask web app that scrapes a [Letterboxd](https://letterboxd.com) film page and exports the data as a Markdown file.

## Features

- Paste any `letterboxd.com/film/<slug>/` URL
- Extracts title, year, director(s), runtime, rating, genres, cast, synopsis, and tagline
- Preview the Markdown output in-browser
- Copy to clipboard or download as a `.md` file

## Setup

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Then open `http://localhost:5000`.

## Stack

- **Backend:** Python 3, Flask, Requests, BeautifulSoup4
- **Frontend:** Vanilla JS, inline CSS (no build step)
