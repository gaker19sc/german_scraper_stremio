import re
import niquests
from typing import List, Dict, Optional, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from aniworld.search import query_s_to, query_filmpalast, query_megakino, query_kinox
from aniworld.models.s_to.episode import SerienstreamEpisode
from aniworld.models.filmpalast_to.episode import FilmPalastEpisode
from aniworld.models.megakino.series import MegaKinoEpisode
from aniworld.models.kinox.series import KinoxEpisode
from aniworld.config import logger, Audio

CINEMETA_URL = "https://v3-cinemeta.strem.io/meta/{type}/{id}.json"

def get_metadata(media_type: str, imdb_id: str) -> Optional[Dict]:
    """Fetch metadata from Cinemeta."""
    url = CINEMETA_URL.format(type=media_type, id=imdb_id)
    try:
        response = niquests.get(url, timeout=10)
        response.raise_for_status()
        return response.json().get("meta")
    except Exception as e:
        logger.error(f"Failed to fetch metadata for {imdb_id}: {e}")
        return None

def clean_for_match(t: str) -> str:
    """Lowercase and alphanumeric only for title comparison."""
    return re.sub(r'\W+', '', t.lower())

def find_best_matches(results: List[Dict], title: str, year: Optional[int] = None) -> List[str]:
    """Find and prioritize the best matching URLs from search results."""
    if not results:
        return []

    title_clean = clean_for_match(title)
    candidates = []

    # 1. Exact title match
    for res in results:
        res_url = res.get("url") or res.get("link")
        if not res_url: continue
        if clean_for_match(res.get("title", "")) == title_clean:
            candidates.append(res_url)

    # 2. Match title AND year
    if year:
        year_str = str(year)
        for res in results:
            res_url = res.get("url") or res.get("link")
            if not res_url or res_url in candidates: continue
            res_title = res.get("title", "")
            if year_str in res_title and title_clean in clean_for_match(res_title):
                candidates.append(res_url)

    # 3. Partial match
    for res in results:
        res_url = res.get("url") or res.get("link")
        if not res_url or res_url in candidates: continue
        res_title_clean = clean_for_match(res.get("title", ""))
        if title_clean in res_title_clean or res_title_clean in title_clean:
            candidates.append(res_url)

    # 4. Fallback to top results if they seem relevant
    first_word = title.split()[0].lower()
    for res in results[:3]:
        res_url = res.get("url") or res.get("link")
        if not res_url or res_url in candidates: continue
        if first_word in res.get("title", "").lower():
            candidates.append(res_url)

    return candidates

def extract_streams(episode_obj: Any, provider_site_name: str, meta_title: str) -> List[Dict]:
    """Generic helper to extract streams from an episode model object."""
    streams = []
    try:
        provider_data = episode_obj.provider_data
        if not provider_data:
            return []

        # Handle both plain dict and ProviderData object
        data_items = provider_data._data.items() if hasattr(provider_data, "_data") else provider_data.items()

        for (audio, subs), providers in data_items:
            # Filter for German streams as requested
            if audio.value != "German":
                continue

            for name, redirect_url in providers.items():
                try:
                    episode_obj.selected_provider = name
                    episode_obj.selected_language = audio.value
                    direct_url = episode_obj.stream_url

                    streams.append({
                        "name": f"{provider_site_name}\n{name}",
                        "title": f"{meta_title}\n{audio.value}\n{name}",
                        "url": direct_url
                    })
                except Exception as e:
                    logger.debug(f"Failed to get stream for {name} on {provider_site_name}: {e}")
    except Exception as e:
        logger.error(f"Error extracting streams from {provider_site_name}: {e}")
    return streams

def fetch_movie_site_streams(site_name: str, query_fn: Any, episode_cls: Any, title: str, year: Optional[int]) -> List[Dict]:
    """Search and extract streams for a movie from a single site."""
    logger.info(f"Checking {site_name} for movie: {title}")
    try:
        results = query_fn(title)

        # Retry with simplified title if needed
        if not results and ":" in title:
            results = query_fn(title.split(":")[0])

        if not results:
            return []

        candidate_urls = find_best_matches(results, title, year)
        site_streams = []
        for url in candidate_urls[:2]:
            try:
                episode = episode_cls(url)
                streams = extract_streams(episode, site_name, title)
                if streams:
                    site_streams.extend(streams)
                    break # Found valid streams on this site
            except Exception as e:
                logger.error(f"Error processing {site_name} movie {url}: {e}")
        return site_streams
    except Exception as e:
        logger.error(f"Failed to query {site_name}: {e}")
        return []

def get_movie_streams(imdb_id: str) -> List[Dict]:
    """Scrape streams for a movie from multiple providers in parallel."""
    meta = get_metadata("movie", imdb_id)
    if not meta: return []

    title = meta.get("name")
    year = int(meta.get("releaseInfo", 0)) if meta.get("releaseInfo") else None

    all_streams = []

    # Provider configurations
    providers = [
        ("Filmpalast", query_filmpalast, FilmPalastEpisode),
        ("MegaKino", query_megakino, MegaKinoEpisode),
        ("Kinox", query_kinox, KinoxEpisode),
    ]

    with ThreadPoolExecutor(max_workers=len(providers)) as executor:
        futures = {executor.submit(fetch_movie_site_streams, site, q_fn, cls, title, year): site for site, q_fn, cls in providers}
        for future in as_completed(futures):
            all_streams.extend(future.result())

    return all_streams

def fetch_series_site_streams(site_name: str, title: str, season: int, episode_num: int) -> List[Dict]:
    """Search and extract streams for a series from a single site."""
    try:
        if site_name == "Serienstream":
            results = query_s_to(title)
            if not results: return []
            links = find_best_matches(results, title)
            for link in links[:1]:
                series_url = f"https://serienstream.to{link}" if not link.startswith("http") else link
                ep_url = f"{series_url.rstrip('/')}/staffel-{season}/episode-{episode_num}"
                episode = SerienstreamEpisode(url=ep_url)
                return extract_streams(episode, site_name, title)

        elif site_name == "Kinox":
            results = query_kinox(title)
            if not results: return []
            urls = find_best_matches(results, title)
            for url in urls[:1]:
                ep_url = f"{url.split('?')[0]}?s={season}&e={episode_num}"
                episode = KinoxEpisode(ep_url)
                return extract_streams(episode, site_name, title)

        elif site_name == "MegaKino":
            results = query_megakino(title)
            if not results: return []
            urls = find_best_matches(results, title)
            for url in urls[:1]:
                ep_url = f"{url}#mkep={episode_num}"
                episode = MegaKinoEpisode(ep_url)
                return extract_streams(episode, site_name, title)
    except Exception as e:
        logger.error(f"Error fetching from {site_name}: {e}")
    return []

def get_series_streams(imdb_id: str, season: int, episode_num: int) -> List[Dict]:
    """Scrape streams for a series episode from multiple providers in parallel."""
    pure_imdb_id = imdb_id.split(":")[0]
    meta = get_metadata("series", pure_imdb_id)
    if not meta: return []

    title = meta.get("name")
    all_streams = []

    sites = ["Serienstream", "Kinox", "MegaKino"]

    with ThreadPoolExecutor(max_workers=len(sites)) as executor:
        futures = {executor.submit(fetch_series_site_streams, site, title, season, episode_num): site for site in sites}
        for future in as_completed(futures):
            all_streams.extend(future.result())

    return all_streams
