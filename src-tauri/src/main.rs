// Prevents an additional console window on Windows in release
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod film;

use film::{is_valid_film_url, scrape_film, to_markdown};
use serde::Serialize;
use tauri::Manager;

#[derive(Serialize)]
struct ScrapeResult {
    markdown: String,
    title: String,
    year: String,
}

#[tauri::command]
async fn scrape(url: String) -> Result<ScrapeResult, String> {
    if !is_valid_film_url(&url) {
        return Err(
            "Not a valid Letterboxd film URL.\nExpected: https://letterboxd.com/film/<slug>/"
                .into(),
        );
    }
    let film = scrape_film(&url).await?;
    let markdown = to_markdown(&film);
    Ok(ScrapeResult {
        title: film.title.clone(),
        year: film.year.clone(),
        markdown,
    })
}

/// Saves markdown to ~/Downloads/<filename>.md and returns the saved path.
#[tauri::command]
async fn save_markdown(
    app: tauri::AppHandle,
    markdown: String,
    filename: String,
) -> Result<String, String> {
    let downloads = app
        .path()
        .download_dir()
        .map_err(|e| format!("Could not resolve Downloads folder: {e}"))?;
    let path = downloads.join(format!("{filename}.md"));
    std::fs::write(&path, markdown.as_bytes())
        .map_err(|e| format!("Failed to save: {e}"))?;
    Ok(path.to_string_lossy().to_string())
}

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![scrape, save_markdown])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
