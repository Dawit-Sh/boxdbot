import io
import re
from flask import Flask, jsonify, render_template_string, request, send_file
from scraper import is_valid_film_url, scrape_film, to_markdown

app = Flask(__name__)

# ── HTML template ──────────────────────────────────────────────────────────────

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>BoxdBot</title>
<style>
  :root {
    --bg:       #14181c;
    --surface:  #1f2630;
    --border:   #2c3440;
    --accent:   #00c030;
    --accent-h: #00a828;
    --text:     #c8d8e8;
    --muted:    #678;
    --danger:   #e05a5a;
    --radius:   8px;
    --mono:     "JetBrains Mono", "Fira Code", "Cascadia Code", monospace;
  }

  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    background: var(--bg);
    color: var(--text);
    font-family: system-ui, -apple-system, sans-serif;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 48px 16px 80px;
  }

  header {
    text-align: center;
    margin-bottom: 48px;
  }
  header h1 {
    font-size: 2rem;
    font-weight: 700;
    letter-spacing: -0.5px;
    color: #fff;
  }
  header h1 span { color: var(--accent); }
  header p {
    margin-top: 8px;
    color: var(--muted);
    font-size: 0.9rem;
  }

  .card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 24px;
    width: 100%;
    max-width: 680px;
  }

  .input-row {
    display: flex;
    gap: 10px;
  }

  input[type="text"] {
    flex: 1;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    color: var(--text);
    font-size: 0.95rem;
    padding: 10px 14px;
    outline: none;
    transition: border-color 0.15s;
  }
  input[type="text"]:focus { border-color: var(--accent); }
  input[type="text"]::placeholder { color: var(--muted); }

  button {
    background: var(--accent);
    border: none;
    border-radius: var(--radius);
    color: #000;
    cursor: pointer;
    font-size: 0.9rem;
    font-weight: 600;
    padding: 10px 20px;
    transition: background 0.15s, opacity 0.15s;
    white-space: nowrap;
  }
  button:hover { background: var(--accent-h); }
  button:disabled { opacity: 0.45; cursor: not-allowed; }

  .error {
    color: var(--danger);
    font-size: 0.85rem;
    margin-top: 10px;
    display: none;
  }

  .result-card {
    display: none;
    margin-top: 24px;
  }

  .result-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
  }
  .result-header span {
    font-size: 0.8rem;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.08em;
  }

  .actions { display: flex; gap: 8px; }

  .btn-secondary {
    background: transparent;
    border: 1px solid var(--border);
    color: var(--text);
    font-size: 0.82rem;
    padding: 6px 14px;
  }
  .btn-secondary:hover { background: var(--border); }

  pre {
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    color: var(--text);
    font-family: var(--mono);
    font-size: 0.82rem;
    line-height: 1.65;
    overflow-x: auto;
    padding: 18px;
    white-space: pre-wrap;
    word-break: break-word;
    max-height: 520px;
    overflow-y: auto;
  }

  .spinner {
    display: none;
    margin-top: 24px;
    text-align: center;
    color: var(--muted);
    font-size: 0.9rem;
  }
  .spinner::before {
    content: "";
    display: inline-block;
    width: 18px;
    height: 18px;
    border: 2px solid var(--border);
    border-top-color: var(--accent);
    border-radius: 50%;
    animation: spin 0.7s linear infinite;
    margin-right: 10px;
    vertical-align: middle;
  }
  @keyframes spin { to { transform: rotate(360deg); } }

  .copy-flash { background: var(--accent-h) !important; color: #000 !important; }
</style>
</head>
<body>

<header>
  <h1>Boxd<span>Bot</span></h1>
  <p>Paste a Letterboxd film URL — get a Markdown file.</p>
</header>

<div class="card">
  <div class="input-row">
    <input
      id="url"
      type="text"
      placeholder="https://letterboxd.com/film/inception/"
      autocomplete="off"
      spellcheck="false"
    />
    <button id="scrape-btn" onclick="scrape()">Scrape</button>
  </div>
  <p class="error" id="error"></p>
</div>

<div class="spinner" id="spinner">Scraping film data…</div>

<div class="card result-card" id="result-card">
  <div class="result-header">
    <span>Markdown preview</span>
    <div class="actions">
      <button class="btn-secondary" onclick="copyMd()">Copy</button>
      <button class="btn-secondary" onclick="downloadMd()">Download .md</button>
    </div>
  </div>
  <pre id="output"></pre>
</div>

<script>
  let currentMd = "";
  let currentFilename = "film";

  const urlInput  = document.getElementById("url");
  const scrapeBtn = document.getElementById("scrape-btn");
  const errorEl   = document.getElementById("error");
  const spinner   = document.getElementById("spinner");
  const resultCard = document.getElementById("result-card");
  const output    = document.getElementById("output");

  urlInput.addEventListener("keydown", e => { if (e.key === "Enter") scrape(); });

  function setError(msg) {
    errorEl.textContent = msg;
    errorEl.style.display = msg ? "block" : "none";
  }

  async function scrape() {
    const url = urlInput.value.trim();
    if (!url) return;

    setError("");
    scrapeBtn.disabled = true;
    resultCard.style.display = "none";
    spinner.style.display = "block";

    try {
      const res = await fetch("/scrape", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
      });
      const data = await res.json();

      if (!res.ok) {
        setError(data.error || "Scraping failed.");
        return;
      }

      currentMd = data.markdown;
      currentFilename = slugify(data.title || "film");
      output.textContent = currentMd;
      resultCard.style.display = "block";
    } catch (e) {
      setError("Network error — is the server running?");
    } finally {
      scrapeBtn.disabled = false;
      spinner.style.display = "none";
    }
  }

  async function downloadMd() {
    const res = await fetch("/download", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ markdown: currentMd, filename: currentFilename }),
    });
    const blob = await res.blob();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = currentFilename + ".md";
    a.click();
  }

  function copyMd() {
    navigator.clipboard.writeText(currentMd).then(() => {
      const btn = event.target;
      btn.textContent = "Copied!";
      btn.classList.add("copy-flash");
      setTimeout(() => { btn.textContent = "Copy"; btn.classList.remove("copy-flash"); }, 1500);
    });
  }

  function slugify(s) {
    return s.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  }
</script>
</body>
</html>"""


# ── routes ─────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/scrape", methods=["POST"])
def scrape():
    url = (request.json or {}).get("url", "").strip()
    if not url:
        return jsonify({"error": "No URL provided."}), 400
    if not is_valid_film_url(url):
        return jsonify({"error": "Not a valid Letterboxd film URL.\nExpected: https://letterboxd.com/film/<slug>/"}), 400
    try:
        film = scrape_film(url)
        md = to_markdown(film)
        return jsonify({"markdown": md, "title": film.title, "year": film.year})
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": f"Scrape failed: {e}"}), 500


@app.route("/download", methods=["POST"])
def download():
    body = request.json or {}
    md = body.get("markdown", "")
    filename = re.sub(r"[^a-z0-9\-]", "", body.get("filename", "film")) or "film"
    buf = io.BytesIO(md.encode("utf-8"))
    return send_file(buf, as_attachment=True, download_name=f"{filename}.md", mimetype="text/markdown")


if __name__ == "__main__":
    app.run(debug=True, port=5000)
