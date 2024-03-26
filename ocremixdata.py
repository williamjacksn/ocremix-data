import argparse
import json
import lxml.html
import pathlib
import sqlite3
import urllib.error
import urllib.request


def cli_import(args: argparse.Namespace):
    do_import(args.ocr_id)


def cli_json(args: argparse.Namespace):
    do_json(args.ocr_id)


def do_import(ocr_id: int):
    print(f'Processing OCR{ocr_id:05}')

    tree = get_tree(ocr_id)
    if tree is None:
        return

    cnx = get_cnx()

    remix_params = {
        'id': ocr_id,
        'title': parse_remix_title(tree),
        'primary_game': parse_remix_primary_game(tree),
    }
    write_remix(cnx, remix_params)

    artists = parse_remix_artists(tree)
    write_artist_batch(cnx, artists)
    write_remix_artist(cnx, ocr_id, [a.get('id') for a in artists])

    tags = parse_remix_tags(tree)
    write_tag_batch(cnx, tags)
    write_remix_tags(cnx, ocr_id, [t.get('id') for t in tags])

    write_data_and_close(cnx)


def do_json(ocr_id: int):
    cnx = get_cnx()
    data = get_remix_data(cnx, ocr_id)
    print(json.dumps(data, indent=4, sort_keys=True))


def get_cnx() -> sqlite3.Connection:
    ocremix_data_sql = pathlib.Path('ocremix-data.sql').resolve()
    cnx = sqlite3.connect(':memory:')
    with ocremix_data_sql.open() as f:
        cnx.executescript(f.read())
    cnx.row_factory = sqlite3.Row
    return cnx


def get_tree(ocr_id: int) -> lxml.html.HtmlElement:
    url = f'https://ocremix.org/remix/OCR{ocr_id:05}'
    try:
        data = urllib.request.urlopen(url)
        page = data.read().decode()
        return lxml.html.fromstring(page)
    except urllib.error.HTTPError:
        print(f'There was a problem reading {url}')


def get_remix_data(cnx: sqlite3.Connection, ocr_id: int) -> dict:
    result = {}
    artists = []
    tags = []
    remix_sql = '''
        select id, title, primary_game
        from remix
        where id = :id
    '''
    artists_sql = '''
        select a.id, a.name, a.url
        from remix_artist ra
        join artist a on a.id = ra.artist_id
        where ra.remix_id = :id
        order by a.id
    '''
    tags_sql = '''
        select t.id, t.path, t.url
        from remix_tag rt
        join tag t on t.id = rt.tag_id
        where rt.remix_id = :id
        order by t.id
    '''
    params = {
        'id': ocr_id,
    }
    with cnx:
        for row in cnx.execute(remix_sql, params):
            result = {
                'primary_game': row['primary_game'],
                'title': row['title'],
                'url': f'https://ocremix.org/remix/OCR{row["id"]:05}',
            }
        for row in cnx.execute(artists_sql, params):
            artists.append({
                'id': row['id'],
                'name': row['name'],
                'url': row['url'],
            })
        for row in cnx.execute(tags_sql, params):
            tags.append({
                'id': row['id'],
                'path': row['path'],
                'url': row['url'],
            })
    result['artists'] = artists
    result['tags'] = tags
    return result


def main():
    args = parse_args()
    args.func(args)


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description='work with a local OC ReMix metadata database')
    sp = ap.add_subparsers(title='Available commands', dest='command', required=True)

    ps_import = sp.add_parser('import', description='fetch data from ocremix.org and store it in the local database')
    ps_import.add_argument('ocr_id', type=int, help='the numeric ID of the ReMix to fetch')
    ps_import.set_defaults(func=cli_import)

    ps_json = sp.add_parser('json', description='print the JSON representation of a ReMix')
    ps_json.add_argument('ocr_id', type=int, help='the numeric ID of the ReMix to print')
    ps_json.set_defaults(func=cli_json)

    return ap.parse_args()


def parse_remix_artists(tree: lxml.html.HtmlElement) -> list[dict]:
    result = []
    for a in tree.xpath('//h2/a[starts-with(@href, "/artist")]'):
        artist_name = a.text.replace('\ufeff', '')
        artist_url = f'https://ocremix.org{a.get("href")}'
        artist_id = int(a.get('href').split('/')[2])
        result.append({
            'id': artist_id,
            'name': artist_name,
            'url': artist_url,
        })
    return result


def parse_remix_primary_game(tree: lxml.html.HtmlElement) -> str:
    return tree.xpath('//h1/a')[0].text


def parse_remix_tags(tree: lxml.html.HtmlElement) -> list[dict]:
    result = []
    for t in tree.xpath('//a[starts-with(@href, "/tag/")]'):
        tag_url = f'https://ocremix.org{t.get("href")}'
        tag_id = t.text
        tag_title = t.get('title')
        if tag_id and tag_title:
            result.append({
                'id': tag_id,
                'path': tag_title.strip(),
                'url': tag_url,
            })
    return result


def parse_remix_title(tree: lxml.html.HtmlElement) -> str:
    return tree.xpath('//h1/a')[0].tail[2:-2]


def write_artist_batch(cnx: sqlite3.Connection, params: list[dict]):
    sql = '''
        insert into artist (id, name, url) values (:id, :name, :url)
        on conflict (id) do update set name = excluded.name, url = excluded.url
    '''
    with cnx:
        cnx.executemany(sql, params)


def write_data_and_close(cnx: sqlite3.Connection):
    ocremix_data_sql = pathlib.Path('ocremix-data.sql').resolve()
    with ocremix_data_sql.open('w') as f:
        for line in cnx.iterdump():
            f.write(f'{line}\n')
    cnx.close()


def write_remix(cnx: sqlite3.Connection, params: dict):
    sql = '''
        insert into remix (id, title, primary_game) values (:id, :title, :primary_game)
        on conflict (id) do update set title = excluded.title, primary_game = excluded.primary_game
    '''
    with cnx:
        cnx.execute(sql, params)


def write_remix_artist(cnx: sqlite3.Connection, remix_id: int, artist_ids: list[int]):
    with cnx:
        cnx.execute(
            'delete from remix_artist where remix_id = :remix_id',
            {'remix_id': remix_id})
        cnx.executemany(
            'insert into remix_artist (remix_id, artist_id) values (:remix_id, :artist_id)',
            [{'remix_id': remix_id, 'artist_id': a} for a in artist_ids]
        )


def write_remix_tags(cnx: sqlite3.Connection, remix_id: int, tag_ids: list[str]):
    with cnx:
        cnx.execute(
            'delete from remix_tag where remix_id = :remix_id',
            {'remix_id': remix_id}
        )
        cnx.executemany(
            'insert into remix_tag (remix_id, tag_id) values (:remix_id, :tag_id)',
            [{'remix_id': remix_id, 'tag_id': t} for t in tag_ids]
        )


def write_tag_batch(cnx: sqlite3.Connection, params: list[dict]):
    sql = '''
        insert into tag (id, path, url) values (:id, :path, :url)
        on conflict (id) do update set path = excluded.path, url = excluded.url
    '''
    with cnx:
        cnx.executemany(sql, params)


if __name__ == "__main__":
    main()
