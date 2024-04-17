import json
import ocremixdata
import pathlib
import sqlite3

cnx = ocremixdata.get_cnx()

for ocr_id in ocremixdata.get_remix_ids(cnx):
    target = pathlib.Path(f'output/remix/OCR{ocr_id:05}.json')
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('w') as f:
        print(f'writing to {target}')
        json.dump(ocremixdata.get_remix_data(cnx, ocr_id), f, indent=4, sort_keys=True)

for tag_id in ocremixdata.get_tag_ids(cnx):
    target = pathlib.Path(f'output/tag/{tag_id}.json')
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('w') as f:
        print(f'writing to {target}')
        json.dump(ocremixdata.get_tag_data(cnx, tag_id), f, indent=4, sort_keys=True)

target = sqlite3.connect(pathlib.Path('output/ocremix-data.db'))
with target:
    print(f'writing to {target}')
    cnx.backup(target)
target.close()
