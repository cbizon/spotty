import json
import os
import tempfile

import pytest

from spotty import choose_random_albums, format_album, load_cached_albums, load_config, save_albums_to_cache


def make_album_item(artist, title, year):
    return {
        "album": {
            "name": title,
            "release_date": f"{year}-01-01",
            "artists": [{"name": artist}],
        }
    }


def make_album_items(n):
    return [make_album_item(f"Artist {i}", f"Album {i}", 2000 + i) for i in range(n)]


# --- load_config ---

def test_load_config_reads_json():
    data = {"client_id": "abc", "client_secret": "xyz", "redirect_uri": "http://localhost"}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        path = f.name
    try:
        config = load_config(path)
        assert config == data
    finally:
        os.unlink(path)


def test_load_config_missing_file():
    with pytest.raises(FileNotFoundError):
        load_config("/nonexistent/path/config.json")


# --- choose_random_albums ---

def test_choose_random_albums_returns_correct_count():
    albums = make_album_items(20)
    selected = choose_random_albums(albums, 5)
    assert len(selected) == 5


def test_choose_random_albums_no_duplicates():
    albums = make_album_items(20)
    selected = choose_random_albums(albums, 10)
    # Each item is a distinct dict object from the original list
    assert len(set(id(x) for x in selected)) == 10


def test_choose_random_albums_all():
    albums = make_album_items(5)
    selected = choose_random_albums(albums, 5)
    assert len(selected) == 5


def test_choose_random_albums_too_many():
    albums = make_album_items(3)
    with pytest.raises(ValueError, match="only 3 available"):
        choose_random_albums(albums, 5)


def test_choose_random_albums_is_random():
    albums = make_album_items(100)
    results = [tuple(id(x) for x in choose_random_albums(albums, 10)) for _ in range(5)]
    # Astronomically unlikely that all 5 draws are identical
    assert len(set(results)) > 1


# --- format_album ---

def test_format_album_single_artist():
    item = make_album_item("Radiohead", "OK Computer", 1997)
    assert format_album(item) == "Radiohead - OK Computer (1997)"


def test_format_album_multiple_artists():
    item = {
        "album": {
            "name": "Collabo",
            "release_date": "2010-06-15",
            "artists": [{"name": "Artist A"}, {"name": "Artist B"}],
        }
    }
    assert format_album(item) == "Artist A, Artist B - Collabo (2010)"


def test_format_album_uses_year_only():
    item = make_album_item("Someone", "Something", 1985)
    result = format_album(item)
    assert result.endswith("(1985)")
    assert "1985-01-01" not in result


# --- cache ---

def test_load_cached_albums_no_db():
    with tempfile.TemporaryDirectory() as d:
        result = load_cached_albums(os.path.join(d, "spotty.db"))
        assert result == []


def test_save_and_load_cache_roundtrip():
    albums = make_album_items(5)
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        save_albums_to_cache(albums, db_path)
        result = load_cached_albums(db_path)
        assert result == albums
    finally:
        os.unlink(db_path)


def test_save_cache_overwrites_previous():
    first = make_album_items(3)
    second = make_album_items(7)
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        save_albums_to_cache(first, db_path)
        save_albums_to_cache(second, db_path)
        result = load_cached_albums(db_path)
        assert result == second
    finally:
        os.unlink(db_path)
