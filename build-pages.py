import json
import ocremixdata
import pathlib

cnx = ocremixdata.get_cnx()

for ocr_id in ocremixdata.get_remix_ids(cnx):
    target = pathlib.Path(f'output/remix/OCR{ocr_id:05}.json')
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('w') as f:
        json.dump(ocremixdata.get_remix_data(cnx, ocr_id), f, indent=4, sort_keys=True)
