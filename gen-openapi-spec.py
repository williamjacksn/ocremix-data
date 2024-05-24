import json

info = {
    'title': 'OverClocked ReMix Data',
    'description': 'This project provides data about remixes published by [OverClocked ReMix](https://ocremix.org/). '
                   'The data is available in JSON and SQLite format.',
    'version': '2024.2'
}

external_docs = {
    'description': 'View the project on GitHub',
    'url': 'https://github.com/williamjacksn/ocremix-data'
}

tags = [
    {
        'name': 'Endpoints',
        'description': 'All available API endpoints'
    }
]

ocremix_data_db_description = '''
This endpoint returns a SQLite database file with all available data. The table schema in the database is as follows:

```
CREATE TABLE artist (
    id integer primary key,
    name text not null,
    url text not null
) strict;

CREATE TABLE game (
    id integer primary key,
    name text not null,
    url text not null
) strict;

CREATE TABLE remix (
    id integer primary key,
    title text not null,
    primary_game text not null,
    import_datetime text,
    youtube_url text,
    primary_game_id int,
    download_url text,
    has_lyrics integer
) strict;

CREATE TABLE remix_artist (
    remix_id integer not null,
    artist_id integer not null,
    _synced integer,
    primary key (remix_id, artist_id)
) strict;

CREATE TABLE remix_tag (
    remix_id integer not null,
    tag_id text not null,
    _synced integer,
    primary key (remix_id, tag_id)
) strict;

CREATE TABLE tag (
    id text primary key,
    path text not null,
    url text not null
) strict;
```
'''

remix_json_properties = {
    'artists': {
        'type': 'array',
        'items': {
            'type': 'object',
            'properties': {
                'id': {'type': 'integer', 'example': 4279},
                'name': {'type': 'string', 'example': 'djpretzel'},
                'url': {'type': 'string', 'example': 'https://ocremix.org/artist/4279/djpretzel'}
            }
        }
    },
    'download_url': {
        'type': 'string',
        'example': 'https://ocrmirror.org/files/music/remixes/Shinobi_Shin_Shuriken_Jam_OC_ReMix.mp3'
    },
    'has_lyrics': {'type': 'boolean', 'example': False},
    'id': {'type': 'integer', 'example': 1},
    'ocr_id': {'type': 'string', 'example': 'OCR00001'},
    'primary_game': {'type': 'string', 'example': 'Shinobi'},
    'tags': {
        'type': 'array',
        'items': {
            'type': 'object',
            'properties': {
                'id': {'type': 'string', 'example': 'electronic'},
                'path': {'type': 'string', 'example': 'Instrumentation > Electronic'},
                'url': {'type': 'string', 'example': 'https://ocremix.org/tag/electronic'}
            }
        }
    },
    'title': {'type': 'string', 'example': 'Shin Shuriken Jam'},
    'url': {'type': 'string', 'example': 'https://ocremix.org/remix/OCR00001'},
    'youtube_url': {'type': 'string', 'example': 'https://www.youtube.com/watch?v=z4D7oqxWS4M'}
}


tag_json_properties = {
    'id': {'type': 'string', 'example': 'electronic'},
    'path': {'type': 'string', 'example': 'Instrumentation > Electronic'},
    'remixes': {
        'type': 'array',
        'items': {
            'type': 'object',
            'properties': {
                'id': {'type': 'integer', 'example': 1},
                'ocr_id': {'type': 'string', 'example': 'OCR00001'},
                'primary_game': {'type': 'string', 'example': 'Shinobi'},
                'title': {'type': 'string', 'example': 'Shin Shuriken Jam'},
                'url': {'type': 'string', 'example': 'https://ocremix.org/remix/OCR00001'},
                'youtube_url': {'type': 'string', 'example': 'https://www.youtube.com/watch?v=z4D7oqxWS4M'}
            }
        }
    }
}

spec = {
    'openapi': '3.1.0',
    'info': info,
    'externalDocs': external_docs,
    'tags': tags,
    'paths': {
        '/ocremix-data.db': {
            'get': {
                'tags': ['Endpoints'],
                'description': ocremix_data_db_description,
                'responses': {
                    '200': {
                        'description': 'A SQLite database file containing all available data',
                        'content': {
                            'application/octet-stream': {
                                'schema': {
                                    'type': 'string',
                                    'format': 'binary',
                                    'example': '[a sqlite database file]'
                                }
                            }
                        }
                    }
                }
            }
        },
        '/remix/{remix_id}.json': {
            'get': {
                'tags': ['Endpoints'],
                'description': 'Returns information about a single remix, including all associated artists and tags',
                'responses': {
                    '200': {
                        'description': 'Information about a single remix',
                        'content': {
                            'application/json': {
                                'schema': {
                                    'type': 'object',
                                    'properties': remix_json_properties
                                }
                            }
                        }
                    }
                }
            },
            'parameters': [
                {
                    'name': 'remix_id',
                    'in': 'path',
                    'description': 'The remix ID',
                    'required': True,
                    'schema': {
                        'type': 'string'
                    },
                    'example': 'OCR00001'
                }
            ]
        },
        '/tag/{tag_id}.json': {
            'get': {
                'tags': ['Endpoints'],
                'description': 'Returns information about a single tag, including all associated remixes',
                'responses': {
                    '200': {
                        'description': 'Information about a single tag',
                        'content': {
                            'application/json': {
                                'schema': {
                                    'type': 'object',
                                    'properties': tag_json_properties
                                }
                            }
                        }
                    }
                }
            },
            'parameters': [
                {
                    'name': 'tag_id',
                    'in': 'path',
                    'description': 'The tag ID',
                    'required': True,
                    'schema': {'type': 'string'},
                    'example': 'electronic'
                }
            ]
        }
    },
    'servers': [
        {'url': 'https://williamjacksn.github.io/ocremix-data'}
    ]
}

with open('output/ocremix-data.openapi.json', 'w') as f:
    json.dump(spec, f, indent=2, sort_keys=True)
