import pathlib
import sqlite3


def get_cnx() -> sqlite3.Connection:
    ocremix_data_sql = pathlib.Path('ocremix-data.sql').resolve()
    cnx = sqlite3.connect(':memory:')
    with ocremix_data_sql.open() as f:
        cnx.executescript(f.read())
    cnx.row_factory = sqlite3.Row
    return cnx


def list_remixes(cnx) -> list:
    sql = '''
        select id
        from remix
        order by id
    '''
    with cnx:
        return [row['id'] for row in cnx.execute(sql)]


def write_data_and_close(cnx: sqlite3.Connection):
    ocremix_data_sql = pathlib.Path('ocremix-data.sql').resolve()
    with ocremix_data_sql.open('w') as f:
        for line in cnx.iterdump():
            f.write(f'{line}\n')
    cnx.close()
