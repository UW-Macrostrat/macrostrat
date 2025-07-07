#%%
import requests
import zipfile
import os
import sys
import shutil
from . import gems_etl as dbit

#%%
APIURL = 'https://ngmdb-dev.usgs.gov/connect/apiv1/catalog/pubs/{id}/'

DBCONFIG = {'host':'localhost','port':5432,
            'database':'ngmdb_test','username':'postgres','pw':'postgres'}

#%%
def parse_citation(product_id:int):
    #TODO: add a little exception catching
    print(APIURL.format(id=product_id))
    resp = requests.get(APIURL.format(id=product_id))

    #Get the response as a dictionary
    cite_dict = resp.json()

    authors = ', '.join([a['name'] for a in cite_dict['authors']])
    citation = authors + ' {}, {}'.format(cite_dict['year'],cite_dict['title'])
    citation+= ', 1:{} ,{}'.format(cite_dict['scale'], cite_dict['primary_links'])

    out_dict= {'ngmdb_url':cite_dict['url'],
               'url':cite_dict['primary_links'][0] if len(cite_dict)>0 else '',
               'source':citation,
               'pubyear':cite_dict['year'],
               'authors':authors,
               'scale_denom':cite_dict['scale'],
               'pdp_id':product_id
    }
    
    return out_dict

def _get_gdb_path_in_zip(zipFilePath:str)->str:

    #Unzip file...
    with zipfile.ZipFile(zipFilePath, 'r') as zf:
        for dir in zf.namelist():
            if dir.endswith('.gdb/'):
                return dir


def unpack_gdb_from_zip(zipFilePath:str,targetDirectory:str):

    #Get the gdb path if there is one
    gdb_path = _get_gdb_path_in_zip(zipFilePath)

    #TODO: exception for returning none
    with zipfile.ZipFile(zipFilePath,'r') as zf:
        outpath = zf.extract(gdb_path,targetDirectory)
        for item in zf.namelist():
            if item.startswith(gdb_path) and not item==gdb_path:
                zf.extract(item,targetDirectory)
        

    #Traverse unzipped file looking for GeMS gdbvcxv
    return outpath

def cleanup_unpacked_zip(parent_directory,unpacked_data):
    base = os.path.relpath(parent_directory,unpacked_data).split(os.path.sep)[0]
    print(os.path.join(unpacked_data,base))
    shutil.rmtree(os.path.join(unpacked_data,base))

def load_map_from_zip(pdp:int,zipPath:str,unpackPath:str, engine = None,
                      ingestion_errors = {},ingested_mapsource_ids = []):
    
    path_to_gdb = unpack_gdb_from_zip(zipPath,unpackPath)

    if engine is None:
        engine = dbit.connect_to_db(**DBCONFIG)
        engine.connect()
        db_metadata = dbit.get_schema_metadata(engine,'source')

    #Get the map citation information from ngmdb
    mapsource_entry = parse_citation(pdp)

    l_incoming = len(ingested_mapsource_ids)

    with engine.connect().execution_options(isolation_level = 'AUTOCOMMIT') as conn:

        #Check if there is a geodatabase at the specified location
        if os.path.exists(path_to_gdb):
            try:
                print('Inserting mapsource record...')
                print(mapsource_entry)
                table_obj = db_metadata.tables['source.mapsources']
                stmt = table_obj.insert().values(mapsource_entry)
                res = conn.execute(stmt)

                #Get the newly inserted primary key
                mapsource_id = res.inserted_primary_key[0]

                print('Ingesting gems gdb and updating keys...')
                print(path_to_gdb)
                ingest_errors_i = dbit.etl_gems_database(conn,db_metadata,path_to_gdb
                                                         ,mapsource_id,datasources_delimiter='|',
                                                         doAllowOnlySubsetOfGeMSFields = False)

                #If there are any dictionary errors
                if ingest_errors_i:
                    ingestion_errors[mapsource_id] = ingest_errors_i
                #If there are no errors, add this mapsource_id to the list
                else:
                    ingested_mapsource_ids.append(mapsource_id)
            
            except Exception as e:
                #TODO: I should think about how to enable this catch to delete mapsources that busted
                # print('Exception occured: {}'.format(repr(e)))
                # print('Ensure mapsource {} does not already exist.'.format(mapsource_entry['source']))
                pass
        else:
            print('No gdb found for source: {} at path {}'.format(mapsource_entry['source'],path_to_gdb))
    
        cleanup_unpacked_zip(unpackPath,path_to_gdb)
    return len(ingested_mapsource_ids) > l_incoming #If we succeeded in loaded
    

# %%
