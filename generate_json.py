import argparse
import common
import json


def get_data(cnx, ocr_id: int) -> dict:
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
    cnx = common.get_cnx()
    data = get_data(cnx, args.ocr_id)
    print(json.dumps(data, indent=4, sort_keys=True))


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('ocr_id', type=int)
    return parser.parse_args()


if __name__ == '__main__':
    main()
