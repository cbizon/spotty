import json
import random
import sys

import spotipy
from spotipy.oauth2 import SpotifyOAuth

CONFIG_FILE = "config.json"
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

    print("Fetching your saved albums...")
    albums = get_all_saved_albums(sp)
    print(f"Found {len(albums)} albums in your library")

    selected = choose_random_albums(albums, n)
    print(f"\n{n} random albums:\n")
    for item in selected:
        print(f"  {format_album(item)}")


if __name__ == "__main__":
    main()
