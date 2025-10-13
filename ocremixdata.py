import argparse
import collections
import concurrent.futures
import datetime
import json
import pathlib
import sqlite3
import textwrap
import urllib.error
import urllib.request

import htpy
import lxml.etree
import lxml.html


def _swagger_ui_version() -> str:
    data = json.loads(pathlib.Path("package.json").read_text())
    return data.get("dependencies").get("swagger-ui-dist")


def cli_build_pages(args: argparse.Namespace) -> None:
    index_html = htpy.html(lang="en")[
        htpy.head[
            htpy.title["OverClocked ReMix Data"],
            htpy.link(
                href=f"https://unpkg.com/swagger-ui-dist@{_swagger_ui_version()}/swagger-ui.css",
                rel="stylesheet",
            ),
        ],
        htpy.body[
            htpy.div("#swagger-ui"),
            htpy.script(
                crossorigin="anonymous",
                src=f"https://unpkg.com/swagger-ui-dist@{_swagger_ui_version()}/swagger-ui-bundle.js",
            ),
            htpy.script(src="index.js"),
        ],
    ]
    target: pathlib.Path = args.directory / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    print(f"writing to {target}")
    target.write_text(str(index_html), newline="\n")

    index_js = textwrap.dedent("""\
        window.onload = () => {
            window.ui = SwaggerUIBundle({
                url: "ocremix-data.openapi.json",
                dom_id: "#swagger-ui"
            });
        };
    """)
    target = args.directory / "index.js"
    target.parent.mkdir(parents=True, exist_ok=True)
    print(f"writing to {target}")
    target.write_text(index_js, newline="\n")

    cnx = get_cnx()

    for ocr_id in get_remix_ids(cnx):
        target = args.directory / f"remix/OCR{ocr_id:05}.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w") as f:
            print(f"writing to {target}")
            json.dump(get_remix_data(cnx, ocr_id), f, indent=4, sort_keys=True)

    for tag_id in get_tag_ids(cnx):
        target = args.directory / f"tag/{tag_id}.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w") as f:
            print(f"writing to {target}")
            json.dump(get_tag_data(cnx, tag_id), f, indent=4, sort_keys=True)

    target = args.directory / "ocremix-data.db"
    print(f"writing to {target}")
    do_write_sqlite(cnx, target)


def cli_import(args: argparse.Namespace) -> None:
    do_import(args.ocr_id)


def cli_import_missing(args: argparse.Namespace) -> None:
    cnx = get_cnx()
    last_local_id = get_last_local_remix_id(cnx)
    last_published_id = get_last_published_remix_id()
    while last_local_id < last_published_id:
        last_local_id += 1
        do_import(last_local_id)


def cli_json(args: argparse.Namespace) -> None:
    do_json(args.ocr_id)


def cli_update(args: argparse.Namespace) -> None:
    cnx = get_cnx()
    with concurrent.futures.ThreadPoolExecutor() as ex:
        future_to_ocr_id = {}
        for remix_id in get_remix_ids_first_imported(cnx, args.limit):
            future_to_ocr_id[ex.submit(get_html, remix_id)] = remix_id
        for future in concurrent.futures.as_completed(future_to_ocr_id):
            remix_id = future_to_ocr_id[future]
            print(f"Processing OCR{remix_id:05}")
            do_import_html(remix_id, future.result())


def cli_write_sqlite(args: argparse.Namespace) -> None:
    cnx = get_cnx()
    do_write_sqlite(cnx, args.file)
    cnx.close()


def do_import(ocr_id: int) -> None:
    print(f"Processing OCR{ocr_id:05}")

    html = get_html(ocr_id)
    if html is None:
        return

    do_import_html(ocr_id, html)


def do_import_html(ocr_id: int, html: lxml.html.HtmlElement) -> None:
    cnx = get_cnx()

    primary_game = parse_remix_primary_game(html)
    write_game(cnx, primary_game)

    remix_params = {
        "download_url": parse_download_url(html),
        "has_lyrics": 1 if parse_has_lyrics(html) else 0,
        "id": ocr_id,
        "import_datetime": datetime.datetime.now(tz=datetime.UTC).isoformat(),
        "primary_game": primary_game.get("name"),
        "primary_game_id": primary_game.get("id"),
        "title": parse_remix_title(html),
        "youtube_url": parse_youtube_url(html),
    }
    write_remix(cnx, remix_params)

    artists = parse_remix_artists(html)
    write_artist_batch(cnx, artists)
    write_remix_artist(cnx, ocr_id, [a.get("id") for a in artists])

    tags = parse_remix_tags(html)
    write_tag_batch(cnx, tags)
    write_remix_tags(cnx, ocr_id, [t.get("id") for t in tags])

    write_data_and_close(cnx)


def do_json(ocr_id: int) -> None:
    cnx = get_cnx()
    data = get_remix_data(cnx, ocr_id)
    print(json.dumps(data, indent=4, sort_keys=True))


def do_write_sqlite(cnx: sqlite3.Connection, target: pathlib.Path) -> None:
    target_cnx = sqlite3.connect(target)
    with target_cnx:
        cnx.backup(target_cnx)
    target_cnx.close()


def get_cnx() -> sqlite3.Connection:
    ocremix_data_sql = pathlib.Path("ocremix-data.sql").resolve()
    cnx = sqlite3.connect(":memory:")
    cnx.row_factory = namedtuple_factory
    with ocremix_data_sql.open(encoding="utf_8") as f:
        cnx.executescript(f.read())
    return cnx


def get_html(ocr_id: int) -> lxml.html.HtmlElement:
    url = f"https://ocremix.org/remix/OCR{ocr_id:05}"
    try:
        data = urllib.request.urlopen(url)  # noqa: S310
        page = data.read().decode()
        return lxml.html.fromstring(page)
    except urllib.error.HTTPError:
        print(f"There was a problem reading {url}")


def get_last_local_remix_id(cnx: sqlite3.Connection) -> int:
    sql = "select max(id) max_id from remix"
    for row in cnx.execute(sql):
        return row.max_id
    return 0


def get_last_published_remix_id() -> int:
    data = urllib.request.urlopen("https://ocremix.org/feeds/ten20/")
    xml = lxml.etree.parse(data)
    for item_el in xml.iter("item"):
        link_el = item_el.find("link")
        return int(link_el.text.split("/")[4][3:])
    return 0


def get_remix_ids_first_imported(cnx: sqlite3.Connection, limit: int = 20) -> list[int]:
    sql = """
        select id from remix
        order by import_datetime
        limit :limit
    """
    params = {
        "limit": limit,
    }
    return [row.id for row in cnx.execute(sql, params)]


def get_remix_data(cnx: sqlite3.Connection, ocr_id: int) -> dict:
    result = {}
    remix_sql = """
        select download_url, has_lyrics, id, title, primary_game, youtube_url
        from remix
        where id = :id
    """
    artists_sql = """
        select a.id, a.name, a.url
        from remix_artist ra
        join artist a on a.id = ra.artist_id
        where ra.remix_id = :id
        order by a.id
    """
    tags_sql = """
        select t.id, t.path, t.url
        from remix_tag rt
        join tag t on t.id = rt.tag_id
        where rt.remix_id = :id
        order by t.id
    """
    params = {
        "id": ocr_id,
    }
    with cnx:
        for row in cnx.execute(remix_sql, params):
            result = {
                "download_url": row.download_url,
                "has_lyrics": bool(row.has_lyrics),
                "id": row.id,
                "ocr_id": f"OCR{row.id:05}",
                "primary_game": row.primary_game,
                "title": row.title,
                "url": f"https://ocremix.org/remix/OCR{row.id:05}",
                "youtube_url": row.youtube_url,
            }
        artists = [
            {"id": row.id, "name": row.name, "url": row.url}
            for row in cnx.execute(artists_sql, params)
        ]
        tags = [
            {"id": row.id, "path": row.path, "url": row.url}
            for row in cnx.execute(tags_sql, params)
        ]
    result["artists"] = artists
    result["tags"] = tags
    return result


def get_remix_ids(cnx: sqlite3.Connection) -> list[int]:
    sql = "select id from remix order by id"
    with cnx:
        return [row.id for row in cnx.execute(sql)]


def get_tag_data(cnx: sqlite3.Connection, tag_id: str) -> dict:
    tag_sql = "select id, path, url from tag where id = :id"
    remix_sql = """
        select r.id, r.title, r.primary_game, r.youtube_url
        from tag t
        join remix_tag rt on rt.tag_id = t.id
        join remix r on r.id = rt.remix_id
        where t.id = :id
        order by r.id
    """
    params = {
        "id": tag_id,
    }
    with cnx:
        for row in cnx.execute(tag_sql, params):
            result = {"id": row.id, "path": row.path, "url": row.url}
        remixes = [
            {
                "id": row.id,
                "ocr_id": f"OCR{row.id:05}",
                "primary_game": row.primary_game,
                "title": row.title,
                "url": f"https://ocremix.org/remix/OCR{row.id:05}",
                "youtube_url": row.youtube_url,
            }
            for row in cnx.execute(remix_sql, params)
        ]
    result["remixes"] = remixes
    return result


def get_tag_ids(cnx: sqlite3.Connection) -> list[str]:
    sql = "select id from tag order by id"
    with cnx:
        return [row.id for row in cnx.execute(sql)]


def main() -> None:
    args = parse_args()
    args.func(args)


def namedtuple_factory(cursor: sqlite3.Cursor, row: tuple) -> tuple:
    fields = [c[0] for c in cursor.description]
    cls = collections.namedtuple("Row", fields)
    return cls(*row)


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="work with a local OC ReMix metadata database"
    )
    sp = ap.add_subparsers(dest="command", required=True, title="Available commands")

    ps_build = sp.add_parser(
        "build-pages", description="build output JSON for all data"
    )
    ps_build.add_argument(
        "-d",
        "--directory",
        default="output",
        help="output directory, default ./output",
        type=pathlib.Path,
    )
    ps_build.set_defaults(func=cli_build_pages)

    ps_import = sp.add_parser(
        "import",
        description="fetch data for a single ReMix from ocremix.org and store in the "
        "local database",
    )
    ps_import.add_argument(
        "ocr_id", help="the numeric ID of the ReMix to fetch", type=int
    )
    ps_import.set_defaults(func=cli_import)

    ps_import_missing = sp.add_parser(
        "import-missing",
        description="fetch data for all missing ReMixes from ocremix.org and store in "
        "the local database",
    )
    ps_import_missing.set_defaults(func=cli_import_missing)

    ps_json = sp.add_parser(
        "json", description="print the JSON representation of a ReMix"
    )
    ps_json.add_argument(
        "ocr_id", help="the numeric ID of the ReMix to print", type=int
    )
    ps_json.set_defaults(func=cli_json)

    ps_update = sp.add_parser(
        "update",
        description="check and update data for ReMixes imported the longest ago",
    )
    ps_update.add_argument(
        "-l",
        "--limit",
        default="10",
        help="the number of ReMixes to check, default 10",
        type=int,
    )
    ps_update.set_defaults(func=cli_update)

    ps_write_sqlite = sp.add_parser(
        "write-sqlite", description="write local data to a SQLite database file"
    )
    ps_write_sqlite.add_argument(
        "file",
        default="ocremix-data.sqlite",
        help="name of file to write",
        type=pathlib.Path,
    )
    ps_write_sqlite.set_defaults(func=cli_write_sqlite)

    return ap.parse_args()


def parse_has_lyrics(html: lxml.html.HtmlElement) -> bool:
    return bool(html.xpath('//a[@href="#tab-lyrics"]'))


def parse_remix_artists(html: lxml.html.HtmlElement) -> list[dict]:
    result = []
    for a in html.xpath('//h2/a[starts-with(@href, "/artist")]'):
        artist_name = a.text.replace("\ufeff", "")
        artist_url = f"https://ocremix.org{a.get('href')}"
        artist_id = int(a.get("href").split("/")[2])
        result.append(
            {
                "id": artist_id,
                "name": artist_name,
                "url": artist_url,
            }
        )
    return result


def parse_download_url(html: lxml.html.HtmlElement) -> str:
    return html.xpath(
        '//div[@id="modalDownload"]//a[contains(@href, "ocrmirror.org")]/@href'
    )[0]


def parse_remix_primary_game(html: lxml.html.HtmlElement) -> dict:
    el = html.xpath("//h1/a")[0]
    game_name = el.text
    href = el.get("href")
    game_url = f"https://ocremix.org{href}"
    game_id = int(href.split("/")[2])
    return {
        "id": game_id,
        "name": game_name,
        "url": game_url,
    }


def parse_remix_tags(html: lxml.html.HtmlElement) -> list[dict]:
    result = []
    for t in html.xpath('//a[starts-with(@href, "/tag/")]'):
        tag_url = f"https://ocremix.org{t.get('href')}"
        tag_id = t.text
        tag_title = t.get("title")
        if tag_id and tag_title:
            result.append(
                {
                    "id": tag_id,
                    "path": tag_title.strip(),
                    "url": tag_url,
                }
            )
    return result


def parse_remix_title(html: lxml.html.HtmlElement) -> str:
    return html.xpath("//h1/a")[0].tail[2:-2]


def parse_youtube_url(html: lxml.html.HtmlElement) -> str:
    for el in html.xpath(
        '//a[starts-with(@data-preview, "https://www.youtube.com/watch?v=")]'
    ):
        return el.get("data-preview")


def write_artist_batch(cnx: sqlite3.Connection, params: list[dict]) -> None:
    sql = """
        insert into artist (id, name, url) values (:id, :name, :url)
        on conflict (id) do update set name = excluded.name, url = excluded.url
    """
    with cnx:
        cnx.executemany(sql, params)


def write_data_and_close(cnx: sqlite3.Connection) -> None:
    cnx.row_factory = sqlite3.Row
    ocremix_data_sql = pathlib.Path("ocremix-data.sql").resolve()
    with ocremix_data_sql.open("w", encoding="utf_8") as f:
        for line in cnx.iterdump():
            f.write(f"{line}\n")
    cnx.close()


def write_game(cnx: sqlite3.Connection, params: dict) -> None:
    sql = """
        insert into game (
            id, name, url
        ) values (
            :id, :name, :url
        ) on conflict (id) do update set
            name = excluded.name, url = excluded.url
    """
    with cnx:
        cnx.execute(sql, params)


def write_remix(cnx: sqlite3.Connection, params: dict) -> None:
    sql = """
        insert into remix (
            download_url, has_lyrics, id, import_datetime, primary_game,
            primary_game_id, title, youtube_url
        ) values (
            :download_url, :has_lyrics, :id, :import_datetime, :primary_game,
            :primary_game_id, :title, :youtube_url
        ) on conflict (id) do update set
            download_url = excluded.download_url, has_lyrics = excluded.has_lyrics,
            import_datetime = excluded.import_datetime,
            primary_game = excluded.primary_game,
            primary_game_id = excluded.primary_game_id, title = excluded.title,
            youtube_url = excluded.youtube_url
    """
    with cnx:
        cnx.execute(sql, params)


def write_remix_artist(
    cnx: sqlite3.Connection, remix_id: int, artist_ids: list[int]
) -> None:
    with cnx:
        cnx.execute(
            "update remix_artist set _synced = 0 where remix_id = :remix_id",
            {"remix_id": remix_id},
        )
        cnx.executemany(
            """
                insert into remix_artist (
                    remix_id, artist_id, _synced
                ) values (
                    :remix_id, :artist_id, 1
                ) on conflict (remix_id, artist_id) do update set
                    _synced = excluded._synced
            """,
            [{"remix_id": remix_id, "artist_id": a} for a in artist_ids],
        )
        cnx.execute(
            "delete from remix_artist where remix_id = :remix_id and _synced = 0",
            {"remix_id": remix_id},
        )


def write_remix_tags(
    cnx: sqlite3.Connection, remix_id: int, tag_ids: list[str]
) -> None:
    with cnx:
        cnx.execute(
            "update remix_tag set _synced = 0 where remix_id = :remix_id",
            {"remix_id": remix_id},
        )
        cnx.executemany(
            """
                insert into remix_tag (
                    remix_id, tag_id, _synced
                ) values (
                    :remix_id, :tag_id, 1
                ) on conflict (remix_id, tag_id) do update set
                    _synced = excluded._synced
            """,
            [{"remix_id": remix_id, "tag_id": t} for t in tag_ids],
        )
        cnx.execute(
            "delete from remix_tag where remix_id = :remix_id and _synced = 0",
            {"remix_id": remix_id},
        )


def write_tag_batch(cnx: sqlite3.Connection, params: list[dict]) -> None:
    sql = """
        insert into tag (id, path, url) values (:id, :path, :url)
        on conflict (id) do update set path = excluded.path, url = excluded.url
    """
    with cnx:
        cnx.executemany(sql, params)


if __name__ == "__main__":
    main()
