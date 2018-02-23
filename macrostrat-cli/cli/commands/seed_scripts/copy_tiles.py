import sqlite3

# Takes as an input a source and a sink
# Copies all tiles from the source to the sink
sink_path = '/Users/john/code/macrostrat/tileserver-seeder/carto-slim.mbtiles'

# Connect to the source
source_connection = sqlite3.connect('/Users/john/code/macrostrat/tileserver-seeder/tiny-slim.mbtiles')
source_cursor = source_connection.cursor()

# Connect to the sink
sink_connection = sqlite3.connect(sink_path)
sink_cursor = sink_connection.cursor()

# Check if this is an existing mbtiles file or not
sink_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='metadata'")
metadata_exists = sink_cursor.fetchone()

if metadata_exists is None:
    with open('./json_schema.json', 'r') as in_schema:
        schema = in_schema.read()
        sink_cursor.execute("""
            CREATE TABLE metadata (name text, value text);
        """)
        metadata = [
             ('name', 'carto-slim'),
             ('format', 'pbf'),
             ('bounds', '-180.0,-85,180,85'),
             ('center', '0,0'),
             ('minzoom', 0),
             ('maxzoom', 16),
             ('attribution', 'Macrostrat, 2018'),
             ('type', 'overlay'),
             ('version', '2.0'),
             ('json', schema)
        ]
        sink_cursor.executemany("""
            INSERT INTO metadata (name, value)
            VALUES (?, ?);
        """, metadata)
        sink_cursor.execute("""
            CREATE TABLE tiles (
                zoom_level integer,
                tile_column integer,
                tile_row integer,
                tile_data blob
            );
        """)
        sink_cursor.execute("""
            CREATE UNIQUE INDEX tile_index on tiles (zoom_level, tile_column, tile_row);
        """)
        sink_connection.commit()

for tile in source_cursor.execute('SELECT zoom_level, tile_column, tile_row, tile_data FROM tiles'):
    sink_cursor.execute("""
        INSERT OR REPLACE INTO tiles (zoom_level, tile_column, tile_row, tile_data)
        VALUES (?, ?, ?, ?)
    """, tile)

sink_connection.commit()

source_connection.close()
sink_connection.close()
