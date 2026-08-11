# German Scraper Stremio Addon

This Stremio addon provides German streams for movies and series from multiple sources.

## Features
- **Movies**: Scrapes **Filmpalast.to**, **MegaKino**, and **Kinox.to**.
- **Series**: Scrapes **Serienstream.to**, **Kinox.to**, and **MegaKino**.
- **Robust Matching**: Uses advanced fuzzy title and year matching to find the best streams.
- **Auto-Correction**: Automatically retries searches with simplified titles if no results are found.
- **Captcha Handling**: Built-in support for solving provider captchas (e.g. on Serienstream).

## Installation
1. Install Python 3.10 or higher.
2. Install dependencies:
   ```bash
   pip install fastapi uvicorn niquests niquests[brotli] certifi packaging python-dotenv curl_cffi patchright
   patchright install chromium
   ```
3. Run the addon:
   ```bash
   python main.py
   ```
4. In Stremio, go to Addons -> Community Addons -> Add outside addon and enter:
   `http://localhost:8080/manifest.json`

## Credit
Based on logic from the AniWorld-Downloader project.
