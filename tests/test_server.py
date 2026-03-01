import base64
import os
import sqlite3
import tempfile

from server import build_image_map, render_album_rows, render_page_header, render_random_page
from spotty import get_image_base64


def make_album_item(artist, title, year, spotify_url="https://open.spotify.com/album/x", img_url="https://img/1.jpg"):
    return {
        "album": {
            "name": title,
            "release_date": f"{year}-01-01",
            "artists": [{"name": artist}],
            "external_urls": {"spotify": spotify_url},
            "images": [{"url": img_url, "width": 64, "height": 64}],
        }
    }


# --- render_random_page ---

def test_render_contains_album_title():
    albums = [make_album_item("Radiohead", "OK Computer", 1997)]
    html = render_random_page(albums)
    assert "OK Computer" in html


def test_render_contains_artist():
    albums = [make_album_item("Radiohead", "OK Computer", 1997)]
    html = render_random_page(albums)
    assert "Radiohead" in html


def test_render_contains_year():
    albums = [make_album_item("Radiohead", "OK Computer", 1997)]
    html = render_random_page(albums)
    assert "1997" in html


def test_render_contains_spotify_link():
    url = "https://open.spotify.com/album/abc123"
    albums = [make_album_item("Radiohead", "OK Computer", 1997, spotify_url=url)]
    html = render_random_page(albums)
    assert url in html


def test_render_falls_back_to_url_when_not_in_image_map():
    img = "https://img.example.com/cover.jpg"
    albums = [make_album_item("Radiohead", "OK Computer", 1997, img_url=img)]
    html = render_random_page(albums, image_map={})
    assert img in html


def test_render_uses_base64_when_in_image_map():
    img = "https://img.example.com/cover.jpg"
    albums = [make_album_item("Radiohead", "OK Computer", 1997, img_url=img)]
    fake_b64 = base64.b64encode(b"fakeimagedata").decode()
    html = render_random_page(albums, image_map={img: fake_b64})
    assert f"data:image/jpeg;base64,{fake_b64}" in html
    assert img not in html  # URL replaced by data URI


def test_render_multiple_albums():
    albums = [make_album_item(f"Artist {i}", f"Album {i}", 2000 + i) for i in range(5)]
    html = render_random_page(albums)
    for i in range(5):
        assert f"Album {i}" in html


def test_render_shows_count_in_heading():
    albums = [make_album_item("A", "B", 2000), make_album_item("C", "D", 2001)]
    html = render_random_page(albums)
    assert "2 Random Albums" in html


def test_render_no_image_when_missing():
    item = {
        "album": {
            "name": "No Art",
            "release_date": "2000-01-01",
            "artists": [{"name": "Artist"}],
            "external_urls": {"spotify": "#"},
            "images": [],
        }
    }
    html = render_random_page([item])
    assert "<img" not in html


# --- render_page_header ---

def test_render_page_header_shows_count():
    html = render_page_header(7)
    assert "7 Random Albums" in html


def test_render_page_header_no_status_by_default():
    html = render_page_header(5)
    assert '<p class="status">' not in html


def test_render_page_header_shows_status_when_given():
    html = render_page_header(5, status="Rebuilding library cache, please wait...")
    assert "Rebuilding library cache" in html


# --- render_album_rows ---

def test_render_album_rows_contains_title():
    albums = [make_album_item("Radiohead", "OK Computer", 1997)]
    html = render_album_rows(albums)
    assert "OK Computer" in html


def test_render_album_rows_no_image_when_missing():
    item = {
        "album": {
            "name": "No Art",
            "release_date": "2000-01-01",
            "artists": [{"name": "Artist"}],
            "external_urls": {"spotify": "#"},
            "images": [],
        }
    }
    html = render_album_rows([item])
    assert "<img" not in html


# --- get_image_base64 ---

def _make_db_with_image(db_path, url, data):
    con = sqlite3.connect(db_path)
    con.execute("CREATE TABLE IF NOT EXISTS images (url TEXT PRIMARY KEY, data BLOB NOT NULL)")
    con.execute("INSERT INTO images (url, data) VALUES (?, ?)", (url, data))
    con.commit()
    con.close()


def test_get_image_base64_returns_cached():
    data = b"\x89PNG fake image bytes"
    url = "https://img.example.com/test.jpg"
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        _make_db_with_image(db_path, url, data)
        result = get_image_base64(url, db_path)
        assert result == base64.b64encode(data).decode()
    finally:
        os.unlink(db_path)


def test_get_image_base64_no_duplicate_on_second_call():
    data = b"image data"
    url = "https://img.example.com/test.jpg"
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        _make_db_with_image(db_path, url, data)
        # Second call should hit cache, not re-insert
        result = get_image_base64(url, db_path)
        con = sqlite3.connect(db_path)
        count = con.execute("SELECT COUNT(*) FROM images WHERE url=?", (url,)).fetchone()[0]
        con.close()
        assert count == 1
        assert result == base64.b64encode(data).decode()
    finally:
        os.unlink(db_path)


# --- build_image_map ---

def test_build_image_map_returns_base64_for_cached():
    data = b"fake jpeg"
    img_url = "https://img.example.com/art.jpg"
    albums = [make_album_item("Artist", "Album", 2000, img_url=img_url)]
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        _make_db_with_image(db_path, img_url, data)
        result = build_image_map(albums, db_path)
        assert result[img_url] == base64.b64encode(data).decode()
    finally:
        os.unlink(db_path)


def test_build_image_map_skips_albums_without_images():
    item = {
        "album": {
            "name": "No Art",
            "release_date": "2000-01-01",
            "artists": [{"name": "Artist"}],
            "external_urls": {"spotify": "#"},
            "images": [],
        }
    }
    with tempfile.TemporaryDirectory() as d:
        result = build_image_map([item], db_path=os.path.join(d, "test.db"))
        assert result == {}
