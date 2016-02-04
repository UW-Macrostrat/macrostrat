import urllib2
import os.path
from os import listdir
import sys
import json
from time import sleep

opener = urllib2.build_opener()
opener.addheaders.append(('Cookie', 'EROS_SSO_production=eyJjcmVhdGVkIjoxNDU0NTM0ODE0LCJ1cGRhdGVkIjoiMjAxNi0wMi0wMyAxMjo1MTo1NSIsImlkIjoiKjZQdjF6LGB1ZEZ4N2chPiBQJUFPc11bMlJQR2ZCIiwic2VjcmV0IjoiMGRdM1wvaXgyTE4yPCYsJHhbLD0yank6NDgpIiwiYXV0aFR5cGUiOiIiLCJhdXRoU2VydmljZSI6IkVST1MiLCJ2ZXJzaW9uIjoxLCJzdGF0ZSI6ImJmY2I1NmEwYTFjMDc1YTUzYWQzNDcyNDAzZmM4NDFlZDFlOTMyODhjNjMxMzQ3YjgxOGFjZDQ4NGFhZGRmMGYifQ'))
opener.addheaders.append(('Cookie', 'PHPSESSID=c1642ompf1s489fr3ntja937l2'))


url_template = 'http://earthexplorer.usgs.gov/download/8360/SRTM1%s%sV3/GEOTIFF/EE'


def download(lat, lng):
    log()
    # Output file name
    output_file = 'downloads/' + lat + lng + '.tif'

    # Double check to make sure we haven't downloaded this tif before
    if os.path.isfile(output_file):
        return

    try:
        response = opener.open(url_template % (lat, lng))
        if response.getcode() == 200:
            output = open(output_file, 'wb')
            output.write(response.read())
            output.close()
            write_polygon(lat, lng)
    except:
        pass


def log():
    global checked_cells
    global total_cells
    checked_cells += 1

    sys.stdout.write('  Progress: %d%%   \r' % ( (checked_cells/float(total_cells))*100) )
    sys.stdout.flush()


def write_polygon(lat, lng):

    lat_direction = 1 if lat[:1] == 'N' else -1
    lng_direction = 1 if lng[:1] == 'E' else -1

    new_lat = int(lat[1:3]) * lat_direction
    new_lng = int(lng[1:4]) * lng_direction

    poly = {
        'type': 'Feature',
        'properties': {},
        'geometry': {
            'type': 'Polygon',
            'coordinates': [[
                [new_lng, new_lat],
                [new_lng, new_lat + 1],
                [new_lng + 1, new_lat + 1],
                [new_lng + 1, new_lat],
                [new_lng, new_lat]
            ]]
        }
    }

    with open('./index_map.geojson', 'r+') as data:
        index_map = json.load(data)
        index_map['features'].append(poly)
        data.seek(0)
        json.dump(index_map, data)



# Get a list of all downloaded files
downloaded = [f for f in listdir('downloads') if os.path.isfile(os.path.join('downloads', f)) and f != '.DS_Store']

# Get all latitudes and longitudes that have been checked
lats = [int(tif[1:3]) for tif in downloaded]
lngs = [int(tif[4:7]) for tif in downloaded]

# Back up the max by 1 to make sure we got the whole row (or start at zero)
start_lat = (max(lats) - 1) if len(lats) else 0
start_lng = (max(lngs) - 1) if len(lngs) else 0

# End coordinates
max_lng = 181
max_lat = 61

# Keep track of progress
total_cells = (max_lng * max_lat) * 4
checked_cells = (start_lat * start_lng) * 4

for lat in xrange(start_lat, max_lat):
    for lng in xrange(start_lng, max_lng):
        # Format coordinates
        formatted_lat = str(lat).zfill(2)
        formatted_lng = str(lng).zfill(3)

        # NorthWest
        download('N' + formatted_lat, 'W' + formatted_lng)

        # NorthEast
        download('N' + formatted_lat, 'E' + formatted_lng)

        # SouthWest
        download('S' + formatted_lat, 'W' + formatted_lng)

        # SouthEast
        download('S' + formatted_lat, 'E' + formatted_lng)


#http://earthexplorer.usgs.gov/download/4960/SRTM1 N41 W114 V2/GEOTIFF/EE

#http://earthexplorer.usgs.gov/download/4960/SRTM1N51W180V2/GEOTIFF/EE

#SRTM 1 Arc-Second Global
#http://earthexplorer.usgs.gov/download/8360/SRTM1N46E090V3/GEOTIFF/EE
