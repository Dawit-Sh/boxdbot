# BoxdBot

A desktop app that scrapes a [Letterboxd](https://letterboxd.com) film page and exports the metadata as a Markdown file.

Paste a film URL, get a formatted `.md` file saved to your Downloads folder.

---

## Features

- Accepts any `letterboxd.com/film/<slug>/` URL
- Extracts title, year, director(s), runtime, rating, genres, top cast, synopsis, and tagline
- Live Markdown preview
- Copy to clipboard or save directly to Downloads

## Download

Grab the latest installer for your platform from the [Releases](../../releases/latest) page.

| Platform | File |
|----------|------|
| Windows  | `.msi` |
| macOS (Intel) | `.dmg` |
| macOS (Apple Silicon) | `.dmg` |
| Linux | `.AppImage` / `.deb` |

## Stack

| Layer | Technology |
|-------|-----------|
| UI shell | [Tauri 2](https://tauri.app) |
| Backend | Rust — `reqwest`, `scraper`, `regex` |
| Frontend | Vanilla JS / CSS (no bundler) |

## Development

### Prerequisites

- [Rust](https://rustup.rs) (stable)
- [Node.js](https://nodejs.org) 18+
- **Windows:** [WebView2](https://developer.microsoft.com/en-us/microsoft-edge/webview2/) + [MSVC Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
- **Linux:** `sudo apt install libwebkit2gtk-4.1-dev libgtk-3-dev libappindicator3-dev librsvg2-dev patchelf`

### Run locally

```bash
npm install
npm run dev
```

### Build a release binary

```bash
npm run build
# output → src-tauri/target/release/bundle/
```

### Replace the app icon

Put a square PNG (1024×1024 recommended) in the project root, then:

```bash
npx tauri icon your-icon.png
```

## Releasing

Push a version tag to trigger the GitHub Actions build across all platforms:

```bash
git tag v1.0.0
git push origin v1.0.0
```

The workflow builds Windows, macOS (x64 + ARM), and Linux in parallel and attaches installers to a draft GitHub Release. Publish the draft when ready.
