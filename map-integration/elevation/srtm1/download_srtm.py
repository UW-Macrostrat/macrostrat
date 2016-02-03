import urllib2
import os.path

opener = urllib2.build_opener()
opener.addheaders.append(('Cookie', 'EROS_SSO_production=eyJjcmVhdGVkIjoxNDU0NTM0ODE0LCJ1cGRhdGVkIjoiMjAxNi0wMi0wMyAxMjo1MTo1NSIsImlkIjoiKjZQdjF6LGB1ZEZ4N2chPiBQJUFPc11bMlJQR2ZCIiwic2VjcmV0IjoiMGRdM1wvaXgyTE4yPCYsJHhbLD0yank6NDgpIiwiYXV0aFR5cGUiOiIiLCJhdXRoU2VydmljZSI6IkVST1MiLCJ2ZXJzaW9uIjoxLCJzdGF0ZSI6ImJmY2I1NmEwYTFjMDc1YTUzYWQzNDcyNDAzZmM4NDFlZDFlOTMyODhjNjMxMzQ3YjgxOGFjZDQ4NGFhZGRmMGYifQ'))
opener.addheaders.append(('Cookie', 'PHPSESSID=c1642ompf1s489fr3ntja937l2'))


url_template = 'http://earthexplorer.usgs.gov/download/4960/SRTM1%s%sV2/GEOTIFF/EE'

def download(lat, lng):
    # Output file name
    output_file = 'downloads/' + lat + lng + '.tif'

    # don't download if file exists
    if os.path.isfile(output_file):
        return

    try:
        response = opener.open(url_template % (lat, lng))
        if response.getcode() == 200:
            output = open(output_file, 'wb')
            output.write(response.read())
            output.close()
    except:
        pass


#for lat in xrange(0, 181):
#    for lng in xrange(0, 61):

for lat in xrange(40, 42):
    for lng in xrange(89, 91):
        # Format coordinates
        formatted_lat = str(lat).zfill(2)
        formatted_lng = str(lng).zfill(3)

        # Do NorthWest
        download('N' + formatted_lat, 'W' + formatted_lng)

        # Do NorthEast
        download('N' + formatted_lat, 'E' + formatted_lng)

        # Do SouthWest
        download('S' + formatted_lat, 'W' + formatted_lng)

        # Do SouthEast
        download('S' + formatted_lat, 'E' + formatted_lng)


#http://earthexplorer.usgs.gov/download/4960/SRTM1 N41 W114 V2/GEOTIFF/EE

#http://earthexplorer.usgs.gov/download/4960/SRTM1N51W180V2/GEOTIFF/EE
