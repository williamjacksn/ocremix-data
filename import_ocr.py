import argparse
import common
import lxml.html
import sqlite3
import urllib.error
import urllib.request


def do_import(ocr_id: int):
    print(f'Processing OCR{ocr_id:05}')

    tree = get_tree(ocr_id)
    if tree is None:
        return

    cnx = common.get_cnx()

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

    common.write_data_and_close(cnx)


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
