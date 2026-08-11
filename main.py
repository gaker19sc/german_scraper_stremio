import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from scraper import get_movie_streams, get_series_streams
from aniworld.config import logger

ADDON_ID = "org.stremio.german.scraper"
VERSION = "1.0.0"

MANIFEST = {
    "id": ADDON_ID,
    "version": VERSION,
    "name": "German Scraper",
    "description": "Provides German streams from Filmpalast, Serienstream, MegaKino, and Kinox.",
    "logo": "https://www.stremio.com/static/images/stremio-logo.png",
    "resources": ["stream"],
    "types": ["movie", "series"],
    "idPrefixes": ["tt"],
}

app = FastAPI(title="German Scraper Stremio Addon", version=VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return RedirectResponse(url="/manifest.json")

@app.get("/manifest.json")
async def get_manifest():
    return MANIFEST

@app.get("/stream/{type}/{id}.json")
def get_stream(type: str, id: str):
    logger.info(f"Stream request: Type={type}, ID={id}")

    streams = []

    try:
        if type == "movie":
            # id is imdb_id
            streams = get_movie_streams(id)
        elif type == "series":
            # id is imdb_id:season:episode
            parts = id.split(":")
            if len(parts) >= 3:
                imdb_id = parts[0]
                season = int(parts[1])
                episode = int(parts[2])
                streams = get_series_streams(imdb_id, season, episode)
            else:
                logger.warning(f"Invalid series ID format: {id}")
    except Exception as e:
        logger.error(f"Error handling stream request for {id}: {e}")

    # Deduplicate and clean up streams
    unique_streams = []
    seen_urls = set()
    for s in streams:
        if s.get("url") and s["url"] not in seen_urls:
            unique_streams.append(s)
            seen_urls.add(s["url"])

    logger.debug(f"Returning {len(unique_streams)} streams.")
    return {"streams": unique_streams}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)
