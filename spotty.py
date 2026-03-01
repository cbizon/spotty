import json
import random
import sqlite3
import sys

import spotipy
from spotipy.oauth2 import SpotifyOAuth

CONFIG_FILE = "config.json"
CACHE_FILE = "spotty.db"
SCOPE = "user-library-read"


def load_config(path=CONFIG_FILE):
    with open(path) as f:
        return json.load(f)


def get_spotify_client(config):
    return spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=config["client_id"],
        client_secret=config["client_secret"],
        redirect_uri=config["redirect_uri"],
        scope=SCOPE,
    ))


def get_album_total(sp):
    response = sp.current_user_saved_albums(limit=1)
    return response["total"]


def load_cached_albums(db_path=CACHE_FILE):
    con = sqlite3.connect(db_path)
    try:
        rows = con.execute("SELECT data FROM albums").fetchall()
        return [json.loads(row[0]) for row in rows]
    except sqlite3.OperationalError:
        return []
    finally:
        con.close()


def save_albums_to_cache(albums, db_path=CACHE_FILE):
    con = sqlite3.connect(db_path)
    try:
        con.execute("CREATE TABLE IF NOT EXISTS albums (id INTEGER PRIMARY KEY, data TEXT NOT NULL)")
        con.execute("DELETE FROM albums")
        con.executemany("INSERT INTO albums (data) VALUES (?)", [(json.dumps(a),) for a in albums])
        con.commit()
    finally:
        con.close()


def get_all_saved_albums(sp):
    albums = []
    limit = 50
    offset = 0
    while True:
        response = sp.current_user_saved_albums(limit=limit, offset=offset)
        items = response["items"]
        albums.extend(items)
        if len(items) < limit:
            break
        offset += limit
    return albums


def get_albums(sp, db_path=CACHE_FILE):
    total = get_album_total(sp)
    cached = load_cached_albums(db_path)
    if len(cached) == total:
        return cached
    print("Library changed, refreshing cache...")
    albums = get_all_saved_albums(sp)
    save_albums_to_cache(albums, db_path)
    return albums


def choose_random_albums(albums, n):
    if n > len(albums):
        raise ValueError(f"Requested {n} albums but only {len(albums)} available")
    return random.sample(albums, n)


def format_album(item):
    album = item["album"]
    artists = ", ".join(a["name"] for a in album["artists"])
    return f"{artists} - {album['name']} ({album['release_date'][:4]})"


def main():
    if len(sys.argv) != 2:
        print("Usage: spotty <n>")
        sys.exit(1)

    try:
        n = int(sys.argv[1])
    except ValueError:
        print(f"Error: '{sys.argv[1]}' is not a valid number")
        sys.exit(1)

    if n < 1:
        print("Error: n must be at least 1")
        sys.exit(1)

    config = load_config()
    sp = get_spotify_client(config)

    albums = get_albums(sp)
    print(f"Found {len(albums)} albums in your library")

    selected = choose_random_albums(albums, n)
    print(f"\n{n} random albums:\n")
    for item in selected:
        print(f"  {format_album(item)}")


if __name__ == "__main__":
    main()
