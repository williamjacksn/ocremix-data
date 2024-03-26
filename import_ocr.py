import argparse
import lxml.html
import pathlib
import sqlite3
import urllib.error
import urllib.request


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

    dump_data(cnx)
    cnx.close()


def dump_data(cnx: sqlite3.Connection):
    ocremix_data_sql = pathlib.Path('ocremix-data.sql').resolve()
    with ocremix_data_sql.open('w') as f:
        for line in cnx.iterdump():
            f.write(f'{line}\n')


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


def main():
    args = parse_args()
    do_import(args.ocr_id)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('ocr_id', type=int)
    return parser.parse_args()


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


def parse_remix_title(tree: lxml.html.HtmlElement) -> str:
    return tree.xpath('//h1/a')[0].tail[2:-2]


def write_artist_batch(cnx: sqlite3.Connection, params: list[dict]):
    sql = '''
        insert into artist (id, name, url) values (:id, :name, :url)
        on conflict (id) do update set name = excluded.name, url = excluded.url
    '''
    with cnx:
        cnx.executemany(sql, params)


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


if __name__ == "__main__":
    main()
