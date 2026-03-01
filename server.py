from flask import Flask, request, Response, stream_with_context

from spotty import (CACHE_FILE, get_album_total, get_all_saved_albums, get_cached_album_count,
                    get_image_base64, get_spotify_client, load_config, pick_image_url,
                    sample_cached_albums, save_albums_to_cache)

app = Flask(__name__)

_sp = None

PAGE_STYLE = """
  body { font-family: sans-serif; max-width: 800px; margin: 40px auto; padding: 0 20px; background: #111; color: #eee; }
  h1 { font-size: 1.4em; color: #1db954; }
  .status { color: #aaa; font-style: italic; }
  table { width: 100%; border-collapse: collapse; }
  tr:hover { background: #222; }
  a { color: #1db954; text-decoration: none; }
  a:hover { text-decoration: underline; }
"""


def get_sp():
    global _sp
    if _sp is None:
        config = load_config()
        _sp = get_spotify_client(config)
    return _sp


def build_image_map(albums, db_path=CACHE_FILE):
    result = {}
    for item in albums:
        url = pick_image_url(item["album"])
        if url:
            result[url] = get_image_base64(url, db_path)
    return result


def render_page_header(n, status=None):
    status_html = f'<p class="status">{status}</p>' if status else ""
    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>{n} Random Albums</title>
  <style>{PAGE_STYLE}</style>
</head>
<body>
  <h1>{n} Random Albums</h1>
  {status_html}
"""


def render_album_rows(albums, image_map=None):
    if image_map is None:
        image_map = {}
    rows = []
    for item in albums:
        album = item["album"]
        title = album["name"]
        artists = ", ".join(a["name"] for a in album["artists"])
        year = album["release_date"][:4]
        url = album["external_urls"].get("spotify", "#")
        img_url = pick_image_url(album)
        if img_url and img_url in image_map:
            img_src = f"data:image/jpeg;base64,{image_map[img_url]}"
        else:
            img_src = img_url
        img_tag = f'<img src="{img_src}" width="64" height="64" style="border-radius:4px">' if img_src else ""
        rows.append(
            f"<tr>"
            f"<td style='padding:8px'>{img_tag}</td>"
            f"<td style='padding:8px'><a href='{url}' target='_blank'><strong>{title}</strong></a><br>{artists}</td>"
            f"<td style='padding:8px;color:#888'>{year}</td>"
            f"</tr>"
        )
    return "<table>\n" + "\n".join(rows) + "\n</table>"


def render_page_footer():
    return "</body></html>"


def render_random_page(albums, image_map=None):
    return (render_page_header(len(albums))
            + render_album_rows(albums, image_map)
            + render_page_footer())


def _generate(sp, n):
    total = get_album_total(sp)
    needs_rebuild = get_cached_album_count() != total

    status = "Rebuilding library cache, please wait..." if needs_rebuild else None
    yield render_page_header(n, status)
    yield " " * 1024  # flush browser buffer before the slow part

    if needs_rebuild:
        albums = get_all_saved_albums(sp)
        save_albums_to_cache(albums)

    selected = sample_cached_albums(n)
    image_map = build_image_map(selected)
    yield render_album_rows(selected, image_map)
    yield render_page_footer()


@app.route("/random")
def random_albums():
    raw = request.query_string.decode().strip()
    try:
        n = int(raw)
    except ValueError:
        return Response(f"Invalid count: '{raw}' — use /random?10", status=400)
    if n < 1:
        return Response("Count must be at least 1", status=400)

    sp = get_sp()
    return Response(stream_with_context(_generate(sp, n)), content_type="text/html")


if __name__ == "__main__":
    app.run(port=3907)
