import os
import numpy as np

import geopandas as gpd
import fiona
import pandas as pd
import difflib

import sqlalchemy as db

import json

#These are errors defined by the driver for when an insert failts related to the database and when relational integrity isn't met - these are defined by the database driver, but its important that we know
#how to recognize them in order to track problem databases
from psycopg2 import DatabaseError,IntegrityError as DatabaseError,IntegrityError 


# TODO: Get geomaterial from DB as part of functions? Hack for now with a file
GEOMATERIALS = []
with open(os.path.join(os.path.split(os.path.abspath(__file__))[0],'geomats.txt'),'r') as file:
    for line in file:
        GEOMATERIALS.append(line.strip())


#TODO: Define global variables for table names where needed
DB_DRIVER = 'psycopg2'
SOURCE_DATA_SCHEMA = 'source'

#TODO: Would love to not do this... can I load table metadata differently, or lookup the schema differently, 
#or somethings?
MAPSOURCES_TBLNM = 'mapsources'
MAPSOURCES_FOREIGNKEY = 'mapsourceid'

#Delimiter to use for concatenation where OK
DB_DELIMITER = '|'

#Spatial reference ID of the project
PROJ_SRID = 5070

#TODO: Tracking instances of multiple datasources... This isn't used currently, and would
#need to create a very non-standard pipeline for ingestion if it was - because datasources table would need to be ingested in
#a topologic order for itself. I wonder if the better strategy is doing this after the fact....
#For feature classes that may reference other items in the same table. This is currently only for concatenated datasources
SELFREFERENCEFIELD = 'multidatasourceids' 

#TODO: Should I swap to define some of these table order/fieldmatching things by looking at the db itself?
#Which features don't we need to take not of existing in a gems database, glossary and geomaterial are fixed at project level,
#topology we don't need to save
GEMS_FEATURES_TO_IGNORE = ['geomaterialdict','stations','photopoints','t_1_dirtyareas','t_1_pointerrors','t_1_lineerrors','t_1_polyerrors']

#Datasources and DOMU must come first, in that order, as datasources has no foreign keys, but important
#primary keys, then DOMU uses datasource foreign key, and establishes important mapunit primary key
#TODO: There are a lot of other possible non-core-geo-content tables that we did not include in NGS
#but might be worth including here
GEMS_TABLE_INGESTION_ORDER = [
#Non-spatial tables
'datasources',
'glossary',
'descriptionofmapunits',
# 'standardlithology',

#Polygons
'datasourcepolys',
'mapunitpolys',
'mapunitoverlaypolys',
'overlaypolys',

#Lines
'contactsandfaults',
'cartographiclines',
'geologiclines',
'mapunitlines',
'isovaluelines',


# #Points
# #TODO: Ignoring stations for now... getting weird type errors
# # 'stations',
# 'fossilpoints',
# 'genericpoints',
# 'geochronpoints',
# 'mapunitpoints',
# 'orientationpoints',

]

#Dictionary that maps a table w/ foreign key fields to the foreign/primarykeys
#NOTE: I could probably automate this, as gems uses a fairly standard naming convention. I am also going to hangle 'mapunit' differently, 
# because most foreign key values will just be replaces, 'mapunit' will be recreated
# dict is structure as dict[<table>] = [(foreignkey1, [table1, primarykey1]), (foreignkey2, [table2, primarykey2])]
GEMS_TABLE_FK_DICT = { 
    'mapunitpolys': [('datasourceid',('datasources','datasources_id')), 
                    ('descriptionofmapunitsid',('descriptionofmapunits','descriptionofmapunits_id'))],

    'mapunitoverlaypolys': [('datasourceid',('datasources','datasources_id')),
                             ('descriptionofmapunitsid',('descriptionofmapunits','descriptionofmapunits_id'))],

    'mapunitlines':[('datasourceid',('datasources','datasources_id')),
                     ('descriptionofmapunitsid',('descriptionofmapunits','descriptionofmapunits_id'))],

    'overlaypolys' : [('datasourceid',('datasources','datasources_id'))],

    'contactsandfaults': [('datasourceid',('datasources','datasources_id'))],

    'glossary': [('definitionsourceid',('datasources','datasources_id'))],

    'datasources': [],

    'datasourcepolys':[('datasourceid',('datasources','datasources_id'))],

    'descriptionofmapunits': [('descriptionsourceid',('datasources','datasources_id'))],

    'cartographiclines' : [('datasourceid',('datasources','datasources_id'))],

    'geologiclines': [('datasourceid',('datasources','datasources_id'))],

    'isovaluelines': [('datasourceid',('datasources','datasources_id'))],

    'contactsandfaults' :[('datasourceid',('datasources','datasources_id'))],

    'orientationpoints' : [('locationsourceid',('datasources','datasources_id')),
                           ('orientationsourceid',('datasources','datasources_id')),
                             ('descriptionofmapunitsid',('descriptionofmapunits','descriptionofmapunits_id'))],

    'mapunitpoints': [('descriptionofmapunitsid',('descriptionofmapunits','descriptionofmapunits_id')),
                       ('datasourceid',('datasources','datasources_id'))],

    'geochronpoints':[('locationsourceid',('datasources','datasources_id')),
                      ('analysissourceid',('datasources','datasources_id')),
                        ('descriptionofmapunitsid',('descriptionofmapunits','descriptionofmapunits_id'))],

    'genericpoints':[('descriptionofmapunitsid',('descriptionofmapunits','descriptionofmapunits_id')),
                     ('locationsourceid',('datasources','datasources_id')),('datasourceid',('datasources','datasources_id'))],

    'fossilpoints':[('descriptionofmapunitsid',('descriptionofmapunits','descriptionofmapunits_id')),
                    ('stationsid',('stations','stations_id')),
                    ('datasourceid',('datasources','datasources_id)')),
                    ('fossilagesourceid',('datasources','datasources_id)')),
                    ('fossilformssourceid',('datasources','datasources_id)')),
                    ('locationsourceid',('datasources','datasources_id)'))],

    'standardlithology':[('descriptionofmapunitsid',('descriptionofmapunits','descriptionofmapunits_id')),
                          ('datasourceid',('datasources','datasources_id'))],

    'stations':[('descriptionofmapunitsid',('descriptionofmapunits','descriptionofmapunits_id')),
                          ('datasourceid',('datasources','datasources_id'))]

}

#Dictionary that maps <table> to (primarykey, geometryfield, databaseingestionfunction[e.g., ST_GeomFromWKB])
GEMS_SPATIAL_TABLES_FIELDS = {'cartographiclines':['cartographiclines_id','shape','ST_LineFromWKB'],
'contactsandfaults':['contactsandfaults_id','shape','ST_LineFromWKB'],
'datasourcepolys':['datasourcepolys_id','shape','ST_PolyFromWKB'],
'geologiclines':['geologiclines_id','shape','ST_LineFromWKB'],
'isovaluelines':['isovaluelines_id','shape','ST_LineFromWKB'],
'mapunitlines':['mapunitlines_id','shape','ST_LineFromWKB'],
'mapunitoverlaypolys':['mapunitoverlaypolys_id','shape','ST_PolyFromWKB'],
'mapunitpolys':['mapunitpolys_id','shape','ST_PolyFromWKB'],
'overlaypolys':['overlaypolys_id','shape','ST_PolyFromWKB'],
'mapunitpoints':['mapunitpoints_id','shape','ST_PointFromWKB'],
'orientationpoints':['orientationpoints_id','shape','ST_PointFromWKB'],
'samples':['samples_id','shape','ST_PointFromWKB'],
'stations':['stations_id','shape','ST_PointFromWKB'],
'fossilpoints':['fossilpoints_id','shape','ST_PointFromWKB'],
'genericpoints':['genericpoints_id','shape','ST_PointFromWKB'],
'geochronpoints':['geochronpoints_id','shape','ST_PointFromWKB'],
}


#Dictionary that maps a gems table to the fields we will ingest.
#This is written out so that we can strip out and save gems fields we want to store. 
#Rather than write out this table, we could compare the fields in a gems file gdb to the 
#records in the equivalent table of the combined map DB, but its possible a filegdb would have reused
#fieldnames in a different way.
#TODO: gems toolbox tools has a 'Gems definition' file w/ this info. However, I have added 'descriptionofmapunitsid' to accompany all mapunits
GEMS_TABLE_FIELD_DICT = {
'datasources':['source','notes','url','datasources_id'],

'glossary':['term','definition','definitionsourceid','glossary_id'],

'descriptionofmapunits':['mapunit','name','fullname','age','description','hierarchykey','paragraphstyle',
                               'label','symbol','areafillrgb','areafillpatterndescription','descriptionsourceid','geomaterial',
                               'geomaterialconfidence','descriptionofmapunits_id'],

'datasourcepolys':['datasourceid','notes','datasourcepolys_id'],

'mapunitpolys':['mapunit','descriptionofmapunitsid','identityconfidence','label',
                'symbol','datasourceid','notes','mapunitpolys_id'],

'mapunitoverlaypolys':['mapunit','descriptionofmapunitsid','identityconfidence','label',
                       'symbol','datasourceid','notes','mapunitoverlaypolys_id'],

'overlaypolys':['type','identityconfidence','label','symbol','datasourceid','notes','overlaypolys_id'],

'contactsandfaults':['type','isconcealed','locationconfidencemeters','existenceconfidence','identityconfidence','symbol',
                     'label','datasourceid','notes','contactsandfaults_id'],

'cartographiclines':['type','symbol','label','datasourceid','notes','cartographiclines_id'],

'geologiclines':['type','isconcealed','locationconfidencemeters','existenceconfidence','identityconfidence',
                 'symbol','label','datasourceid','notes','geologiclines_id'],

'mapunitlines':['mapunit','descriptionofmapunitsid','isconcealed','locationconfidencemeters',
                'existenceconfidence','identityconfidence','symbol','label','plotatscale','datasourceid','notes','mapunitlines_id'],

'isovaluelines': ['type','value','valueconfidence','symbol','label','datasourceid','notes'],

'fossilpoints':['type','symbol','label','locationconfidencemeters','plotatscale','stationsid','datasourceid','mapunit',
                'descriptionofmapunitsid','notes','fossilpoints_id','materialanalyzed','alternatesampleid',
                'fieldsampleid','fossilage','fossilagesourceid','fossilforms','fossilformssourceid','locationsourceid'],

'genericpoints':['type','symbol','label','locationconfidencemeters','plotatscale','stationsid',
                 'mapunit','datasourceid','locationsourceid','descriptionofmapunitsid','notes','genericpoints_id'],

'geochronpoints':['type','fieldsampleid','alternatesampleid','mapunit','descriptionofmapunitsid','symbol',
                  'label','locationconfidencemeters','plotatscale','materialanalyzed','numericage','agepluserror',
                  'ageminuserror','errormeasure','ageunits','stationsid','locationsourceid','analysissourceid','notes','geochronpoints_id'],

'mapunitpoints':['mapunit','descriptionofmapunitsid','locationconfidencemeters',
                 'existenceconfidence','identityconfidence','symbol','label','plotatscale','datasourceid','notes','mapunitpoints_id'],

'orientationpoints':['type','azimuth','inclination','symbol','label','locationconfidencemeters',
                     'identityconfidence','orientationconfidencedegrees','plotatscale','stationsid',
                     'mapunit','descriptionofmapunitsid','locationsourceid','orientationsourceid','notes','orientationpoints_id'],

'stations':['fieldid','locationconfidencemeters','observedmapunit','mapunit','descriptionofmapunitsid',
            'symbol','label','plotatscale','datasourceid','notes','stations_id'],

'standardlithology':['mapunit','parttype','lithology','proportionterm','proportionvalue',
                     'scientificconfidence','datasourceid']
}

#This dictionary maps a table name to a dictionary of renamed fields. 
#Not currently used... but in theory this could be more flexible in the future...
#Dictionary maps dict[<gemstablename>]->tuple[<newtablename>,dict[gemsfield] -> targetfields>]
GEMS_TO_SOURCEMAPDATA_REMAPPING = {
# 'descriptionofmapunits':('descriptionofmapunits',{'mapunit':'mapunit','descriptionofmapunits_id':'descriptionofmapunits_id'}),
}

# #Rather than specify all 'remapping' of mapunit, with no change in destination table, generate it from table components above
# for table in GEMS_TABLE_FIELD_DICT:
#     if ('mapunit' in GEMS_TABLE_FIELD_DICT[table]) and not(table in GEMS_TO_SOURCEMAPDATA_REMAPPING):
#         GEMS_TO_SOURCEMAPDATA_REMAPPING[table] = (table,{'mapunit':'mapunit','descriptionofmapunitsid':'descriptionofmapunitsid'})

EXTRAITEMSFIELD = 'additional_attributes'
EXTRAMAPSOURCEFEATURESFIELD = 'additional_features'

EXTRAITEMSTOIGNORE = ['geometry','shape_length','shape_area', 
                        'created_user','created_date','last_edited_user',
                        'last_edited_date','orig_fid']

class NpEncoder(json.JSONEncoder):
    #Occasionally we will get fields in tables
    #that get loaded in as numpy datatypes, but are
    #not gems fields. The ETL behavior is to strip those
    #to a json field. However some numpy datatypes can not
    #be dumped to json. This catches a few common examples that
    #feel safe to catch
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        return super(NpEncoder, self).default(obj)


#########################
## basic postgres interaction
#########################

def check_if_table_exists(connection,table,schema):
    sql_statement = '''SELECT EXISTS (
    SELECT FROM information_schema.tables 
    WHERE  table_schema = '{schema:}'
    AND    table_name   = '{table:}'
    );'''.format(table=table,schema=schema)
    sql_statement = db.sql.text(sql_statement)
    res = connection.execute(sql_statement)
    return res.first()[0]

def get_schema_metadata(db_engine,schema):
    #Get the metadata object that contains info about db tables/columns

    #TODO: Need to figure this out... seems I need to specify a schema, but load stuff outside that schema? Is this because this
    #recursively loads related tables?
    metadata_obj = db.MetaData(schema = schema) 
    metadata_obj.reflect(bind=db_engine)

    return metadata_obj

def connect_to_db(host,port, database,username,pw, dialect = 'postgresql'):
    #TODO: Figure out what different drivers control...

    # connect_string = '{dialect}+{driver}://{username}:{password}@{host}:{port}/{database}'.format(dialect=dialect,driver=driver,
    #                                                                                             username=username, password=pw,
    #                                                                                             host = host,port = port,
    #                                                                                             database=database)

    #Populate the connection string using the built in method in sqlalchemy
    url_object = db.engine.URL.create(
    "{}+{}".format(dialect,DB_DRIVER),
    username=username,
    password=pw,  # plain (unescaped) text
    host=host,
    database=database,
    port = port)

    #Get a database connection 'engine'
    engine = db.create_engine(url_object)

    return engine

def replace_db_records(engine,db_metadata, target_table, field_to_match,value_to_match, target_field_value_dict):
    '''
    #TODO: Add check that primary key is actually present
    '''

    #Get the table object from the metadata object
    table_obj = get_table_object_from_gems_tablename(engine,db_metadata,target_table)

    #Get the statement to execute
    stmt = db.update(table_obj).values(target_field_value_dict).where(table_obj.c[field_to_match] == value_to_match)

    #Execute the statement
    res = engine.execute(stmt)

    return res

def insert_db_record(engine,db_metadata, target_table, target_field_value_dict):
    #TODO: Need to test this function

    table_obj = get_table_object_from_gems_tablename(engine,db_metadata,target_table)

    stmt = table_obj.insert().values(target_field_value_dict)
     
    res = engine.execute(stmt)

    return res

def test_ETL_tables_for_required_elements(engine,db_metadata,doPrint = True):

    missing_items = {}
    renamed_tables = {'descriptionofmapunits':'descriptionofmapunits'}
    renamed_fields = {'mapunit':'mapunit',
                      'descriptionofmapunits_id':'descriptionofmapunits_id'}

    #Get gems table/column definition, convert to lower case
    from GeMS_Definition import startDict as gemsDefDictUC

    gemsDefDict = {} #Space for lower case version
    for tbl in gemsDefDictUC:
        tblLC = tbl.lower()
        fields = gemsDefDictUC[tbl]
        lcFields = []
        if tblLC in renamed_tables:
            tblLC = renamed_tables[tblLC]

        for field in fields:

            field[0] = field[0].lower()
            if field[0] in renamed_fields:
                field[0] = renamed_fields[field[0]]
            #Just keep track of field name
            lcFields.append(field[0])

        gemsDefDict[tblLC] = lcFields

    GEMS_SPATIAL_TABLES_FIELDS
    GEMS_TABLE_FIELD_DICT
    GEMS_TABLE_FK_DICT
    GEMS_TABLE_INGESTION_ORDER

    #First, check the GEMS_TABLE_INGESTION_ORDER
    for tbl in gemsDefDict:
        if not tbl in GEMS_TABLE_INGESTION_ORDER:
            if not 'TABLE_INGESTION_ORDER' in missing_items:
                missing_items['TABLE_INGESTION_ORDER'] = {}
            missing_items['TABLE_INGESTION_ORDER'][tbl] = 'Table missing from ingestion order: {}'.format(tbl)

    #Second, check GEMS_SPATIAL_TABLES_Fields
    from GeMS_Definition import shape_dict as gemsShapeDict
    for tbl in gemsShapeDict:
        if not tbl.lower() in GEMS_SPATIAL_TABLES_FIELDS:
            if not gemsShapeDict[tbl].lower() == 'table':
                if not 'SPATIAL_TABLES' in missing_items:
                    missing_items['SPATIAL_TABLES'] = {}
                missing_items['SPATIAL_TABLES'][tbl] = 'Table missing from spatial tables list: {}, needs spatial type: {}'.format(tbl.lower(),gemsShapeDict[tbl])

    
    #Third, check GEMS_TABLE_FK_Dict_Fields
    #TODO: Could actually compare database FK definition to table definition using sqlalchemy metadata...
    for tbl in gemsDefDict:
        if not tbl in GEMS_TABLE_FK_DICT:
            if not 'TABLE_FK' in missing_items:
                missing_items['TABLE_FK'] = {}
            missing_items['TABLE_FK'][tbl] = 'Table missing from FK Dict order: {}'.format(tbl)

    #Fourth, check GEMS_TABLE_FIELD_DICT
    missing_items['TABLE_FIELD'] = {}
    for tbl in gemsDefDict:
        if tbl in GEMS_TABLE_FIELD_DICT:
            fieldDiff = set(gemsDefDict[tbl]).difference(GEMS_TABLE_FIELD_DICT[tbl])
            if fieldDiff:
                missing_items['TABLE_FIELD'][tbl] = 'Fields missing for {} table: {}'.format(tbl,fieldDiff)
        else:
            missing_items['TABLE_FIELD'][tbl] = 'Table missing from ingestion order: {}'.format(tbl)
        

    if doPrint:
        if missing_items:
            print('----------------------------------------------')
            print('----------------------------------------------')
            print('The following items elements are missing from ETL definitions \n')
            print('----------------------------------------------')

            for missing_item in missing_items:
                if missing_items[missing_item]:
                    print('----------------------------------------------')
                    print('Content missing from ETL dict: {}'.format(missing_item))
                    print('----------------------------------------------')
                    print('----------------------------------------------')

                    for missing_content in missing_items[missing_item]:
                        print(missing_items[missing_item][missing_content])
                        print('----------------------------------------------')

        else:
            print('Hooray, all required elements present in database! ヘ( ^o^)ノ＼(^_^ )')

    return missing_items

    

def test_engine_for_required_elements(engine,db_metadata, doPrint = True):
    """_summary_

    Args:
        engine (_type_): _description_
        db_metadata (_type_): _description_
    """
    missing_items = {}
    renamed_tables = {'descriptionofmapunits':'descriptionofmapunits'}
    renamed_fields = {'mapunit':'mapunit',
                      'descriptionofmapunits_id':'descriptionofmapunits_id'}

    #Get gems table/column definition, convert to lower case
    from GeMS_Definition import startDict as gemsDefDictUC

    gemsDefDict = {} #Space for lower case version
    for tbl in gemsDefDictUC:
        tblLC = tbl.lower()
        fields = gemsDefDictUC[tbl]
        lcFields = []
        if tblLC in renamed_tables:
            tblLC = renamed_tables[tblLC]

        for field in fields:

            field[0] = field[0].lower()
            if field[0] in renamed_fields:
                field[0] = renamed_fields[field[0]]
            #Just keep track of field name
            lcFields.append(field[0])

        gemsDefDict[tblLC] = lcFields
        
    for tbl in gemsDefDict:
        try:
            tbl_obj = get_table_object_from_gems_tablename(engine,db_metadata,tbl)
            tbl_columns = [c.name for c in tbl_obj.columns]
            req_fields = gemsDefDict[tbl]
            missing_fields = []
            for req_field in req_fields:
                if not(req_field in tbl_columns):
                    missing_fields.append(req_field)
            
            if len(missing_fields)>0:
                missing_items[tbl] = missing_fields
        except KeyError:
            missing_items[tbl] = 'Table missing, needs fields: {}'.format(gemsDefDict[tbl])


    if doPrint:
        if missing_items:
            print('The following GeMS elements are missing from the target database: \n')

            for table in missing_items:
                print('Missing table: {} \n'.format(table))
                print('Fields: {} \n'.format(missing_items[table]))
                print('----------------------------------------------')

        else:
            print('Hooray, all required elements present in database! ヘ( ^o^)ノ＼(^_^ )')

    return missing_items

def get_table_object_from_gems_tablename(engine,db_metadata,table_name:str):
    """ Returns the joint database name based on the gems table name

    NOTE: This could probably be a simpler function or a dictionary lookup, but for now this would offer some future flexibility if there
    were major changes in naming conventions.

    #TODO: Would it be more flexible to just get the metadata directly from the engine? Perhaps like the following:
    
    engine = create_engine(dbUrl)
    meta = MetaData()
    table = Table('tableName', meta, autoload=True, autoload_with=engine)

    Args:
        engine (_type_): _description_
        table_name (str): the name of a gems table to ingest

    Returns:
        _type_: _description_
    """

    #TODO: add in error checks for if the table exists?

    # #datasources, mapsources
    # if 'sources' in table_name:
    #     db_tablename = 'reference_info.{}'.format(table_name)

    # #TODO: This is not a very safe way to do things... should add some error checks in or think about other potential cases
    # else:
    #     db_tablename = 'source.{}'.format(table_name)

    vocabulary_tables = ['geomaterialdict']

    if not( '.' in table_name):
        prefix = 'source'
        if table_name in vocabulary_tables:
            prefix = 'vocabularies'
        #All gems ingested tables should be stored in 'soure'
        db_tablename = '{}.{}'.format(prefix,table_name)
    else:
        db_tablename = table_name

    return db_metadata.tables[db_tablename]

#################################################################################################################################################################
## EXTRACT
#################################################################################################################################################################
def extract_gems_database_to_dict_of_dataframes(path_to_gdb):
    #Get all the layers in the databse
    layers = fiona.listlayers(path_to_gdb)

    #Load in each layer as a dict
    gems_db_dict = {} #Initialize dict

    #Loop through each layer
    for layer in layers:
        #Load a layer
        table_df = gpd.read_file(path_to_gdb,layer = layer,engine = 'pyogrio')

        #Record this tables data in the output dict
        gems_db_dict[layer] = table_df


    return gems_db_dict

#################################################################################################################################################################
## TRANSFORM
#################################################################################################################################################################

def _transform_reset_geomaterial_values(table_df):
    #TODO: Should probably put this in a try/except to catch geomaterials that aren't close...
    table_df['descriptionofmapunits']['geomaterial'] = table_df['descriptionofmapunits']['geomaterial'].apply(lambda val: None if val is None else difflib.get_close_matches(val,GEOMATERIALS)[0])
    return table_df

def _transform_lowercase_onecharacter_isconcealed(table_df):

    for table in table_df:
        for col in table_df[table]:
            if col.lower() == 'isconcealed':
                table_df[table][col] = table_df[table][col].str.lower()
                table_df[table][col] = table_df[table][col].str[0] #Only get first character

    return table_df

def _transform_remap_gems_fields(table_df,layer):

    '''Remaps columns (aka fields) in the layer based on the globally defined remapping dict.
    
    Will leave this as a standalone function to enable facilitate future complexity if needed.
    
    '''
    
    if layer in GEMS_TO_SOURCEMAPDATA_REMAPPING:
        table_df = table_df.rename(columns = GEMS_TO_SOURCEMAPDATA_REMAPPING[layer][1])
        layer = GEMS_TO_SOURCEMAPDATA_REMAPPING[layer][0]

    return table_df, layer

def _transform_sanitize_and_remap_gems_fields(gems_db_dict):

    #Initialize an output dictionary for new field/table names
    outDict = {}

    for layer in gems_db_dict:
        #Get a lowercase version of this fieldname
        layer_lc = layer.lower()

        #Get this layer
        table_df = gems_db_dict[layer]

        #TODO: Converting columns to lowercase - but does this make my DB not GeMS compliant?
        table_df.columns = table_df.columns.str.lower() 
        
        #Preform any field renaming
        table_df,target_layer = _transform_remap_gems_fields(table_df,layer_lc)

        #Record this tables data in the output dict
        outDict[target_layer] = table_df

    return outDict

def _transform_projection_spatial_manipulation(gems_db_dict):

    for layer in gems_db_dict:
        #Project to project CRS. #TODO: Should I just add a check first if it is in the correct CRS? Should also 
        if layer in GEMS_SPATIAL_TABLES_FIELDS:
            #Get the table
            table_df = gems_db_dict[layer]

            #If there are any invalid geometries, make them valid
            if ~np.all(table_df.is_valid):
                print('Invalid geometries found in table: {}, making valid...'.format(layer))
                table_df['geometry'] = table_df.make_valid()
                

            #Project
            table_df = table_df.to_crs(epsg=PROJ_SRID)

            #Explode any lingering spatial features
            table_df = table_df.explode(ignore_index=True)

            #To do:
            #simplify?

            #merge?

            #split at intersections?

            #update dictionary
            gems_db_dict[layer] = table_df


    return gems_db_dict

def _transform_drop_unused_gems_features(gems_db_dict, gems_features_to_ignore = None):
    '''
    Generate a clean dictionary of features that will be used, as well as a dictionary of all unused features
    unused_item_dict maps feature class names to a list of fields
    '''
    gems_db_dict_clean = {}
    unused_item_dict = {}

    #What features are included in geodatabases that we don't need to keep track of being included
    if gems_features_to_ignore is None:
        gems_features_to_ignore = GEMS_FEATURES_TO_IGNORE

    #Loop through the gems_db_dict keys
    for key in gems_db_dict:

        #If the FC is in our list of expected ingestion order, ingest it
        if key in GEMS_TABLE_INGESTION_ORDER:
            gems_db_dict_clean[key] = gems_db_dict[key]

        #If it isn't, get the fieldnames and save them as a list - but ignore standard gems features taht we aren't loading in because we want to standardize (e.g., glossary, geomaterialdict)
        elif not(key in gems_features_to_ignore):
            #Get a list of the fields for this feature, ignoring things like geometry, length, area
            unused_item_dict[key] = [field for field in gems_db_dict[key].columns if not(field in EXTRAITEMSTOIGNORE)]

    return gems_db_dict_clean, unused_item_dict

def _transform_gems_concatenated_datasources_to_primarykeys(gems_db_dict,delimiter = '|',new_delimiter = '|'):
    """Find all concatenated datasources, add them as a new primary key


    #TODO: Lots of lingering questions w/ cleaning up datasources.

    # A likely reality imposed by delimited keys is that entries won't be sanitized (e.g., weird whitespaces - 'DAS1|DAS2' and 'DAS1 | DAS2  '). 
    #Currently 'DAS2|DAS1' will also be considered something different than 'DAS1|DAS2'


    Args:
        gems_db_dict (_type_): _description_
        delimiter (str, optional): _description_. Defaults to '|'.

    Returns:
        _type_: _description_
    """
    
    #Is this a unique problem to datasources? Think so, but not sure, so leave fields as variables.
    tablename = 'datasources'
    primarykey = 'datasources_id'
    fieldToConcat = 'source'

    #First pull out datasources table
    ds_table = gems_db_dict[tablename]

    #Next find all entries that aren't the datasources table but have foreign keys
    other_tables = [tbl for tbl in gems_db_dict if (not(tbl==tablename) and (tbl in GEMS_TABLE_FK_DICT))]

    #Create a list of all the concatenated datasources
    concatd_ds = []

    #Loop through each table
    for tbl in other_tables:
        # print('working on datasources for {}...'.format(tbl))

        #Get the table from the dictionary of tables
        table_df = gems_db_dict[tbl]
        # print('Table has columns: {}'.format(table_df.columns))

        #Get the foreign key fields and their corresponding tables, primary keys from the lookup dictionary
        fkfields_tables_pks = GEMS_TABLE_FK_DICT[tbl]

        for foreignkey, table_pk in fkfields_tables_pks:
            # print('Working on fk/pk pair: {}/{}'.format(foreignkey,table_pk))
            #If this foreign key points to the table of interest (datasources)
            if table_pk[0] == tablename:
                # print(tbl)
                
                #Find column indices that contain the delimeter
                delimitedIdcs= table_df[foreignkey].str.contains(delimiter,regex=False)
                
                #delimitedIdcs may contain null values, because headings in a gems DOMU don't need datasources apparently
                delimitedIdcs[delimitedIdcs.isna()] = False
                delimitedFields = table_df.index[delimitedIdcs].tolist()

                if len(delimitedFields) > 0:
                    print('Found delimited entries in {} table: '.format(tbl))
                    
                    #Iterate through any delimited fields present
                    for i in delimitedFields:
                        #NOTE: Probably more efficient to check if the concatenated key is correctly formatted first, rather than assume it needs to be ordered and stripped as I do here.

                        #Get the components of the concatenated key
                        key_components = np.sort(table_df.loc[i,foreignkey].split(delimiter)) #Get the sorted delimiter entries

                        #Rejoin the foreign key components as a concatenated entry after stripping any whitespace. Could just do this in one line above, but this is a bit more readable.
                        new_concatdkey = new_delimiter.join([k.strip() for k in key_components])

                        #If the new_concatdkey isn't in our list of new keys, add it
                        if not(new_concatdkey) in concatd_ds:
                            concatd_ds.append(new_concatdkey)

                        #Replace the old key with the clean one
                        table_df.loc[i,foreignkey] = new_concatdkey

    #If there were any concatenated datasources
    if concatd_ds:
        # print('adding concatenated datasources: {}'.format(concatd_ds))
        #Now need to build the concatenated datasources as their own unique entries.
        ds_toappend = pd.DataFrame(data=None, columns=ds_table.columns) #Create a space to host the newly created datasource entries

        #Create a space for the self-reference list
        ds_toappend[SELFREFERENCEFIELD] = [[] for ds in concatd_ds]

        #For each new datasource entry needed
        for i,new_ds in enumerate(concatd_ds):
            #Create a space to host the components of this new datasource entry
            sub_dfs = []
            #Split the components of the datasource
            split_ds = [ds.strip() for ds in new_ds.split(new_delimiter)]
            #For each component datasource
            for j,ds in enumerate(split_ds):
                #Find that component entry in the datasources table

                #TODO: This needs some sort of error check if the component entry isn't found in gems
                sub_dfs.append(ds_table[ds_table[primarykey]==ds])

            sub_df = pd.concat(sub_dfs,ignore_index=True)

            # 
            ds_toappend.loc[i,primarykey] = new_ds

            #Combine all the columns into a delimted entry
            for col in ds_toappend.columns:
                if not(col == primarykey) and not(col == SELFREFERENCEFIELD):
                    ds_toappend.loc[i,col] = new_delimiter.join([str(val) for val in sub_df[col].values])

            #Track the list of primary keys that goes with each entry
            ds_toappend.loc[i,SELFREFERENCEFIELD].extend([val for val in sub_df[primarykey].values])

            #Prepend a little message that this was combined
            ds_toappend.loc[i,fieldToConcat] = 'Combination of multiple sources: ' + ds_toappend.loc[i,fieldToConcat]

        #Add these new datasources to the ds_table
        ds_table[SELFREFERENCEFIELD] = [None for i in range(len(ds_table))]
        gems_db_dict[tablename] = pd.concat([ds_table,ds_toappend],ignore_index=True)

    return gems_db_dict

# def _transform_uniqueify_mapunit_values(gems_db_dict,mapsource_id,mapunitfieldname = 'mapunit',do_update_in_place = True):
#     """Update all 'mapunit' fields with a modifier from the mapsource_id to make them unique.

#     Args:
#         gems_db_dict (dictionary): dictionary of pandas geodataframes, with the key equal to the table name from a gems .gdb
#         mapsource_id (string - primarykey to mapsource_id table): a unique identified tied to the map sources

#     Returns:
#         gems_db_dict (dictionary): dictionary of pandas geodataframes, with the key equal to the table name from a gems .gdb. All
#         entries in any fields that reference map units have been modified to be unique. 
#     """

#     #Swap the variable of the gems_db_dict with a copy if we don't want to copy in place
#     if not(do_update_in_place):
#         unq_dict = {}
#         for tbl in gems_db_dict:
#             unq_dict[tbl] = gems_db_dict[tbl].copy()
#         gems_db_dict = unq_dict

#     for tablename in gems_db_dict:
#         table_df = gems_db_dict[tablename]
#         for column in table_df.columns:
#             #TODO: Consider whether checking case is appropriate or not
#             #If this is a 'mapunit' fieldname, make prepend 
#             if column.lower() == mapunitfieldname.lower():
#                 unique_mapunits = []
#                 # print('Found mapunit column in table: {}'.format(tablename))
#                 #TODO: Test what is needed to actually detect mapunits
#                 for i,row in table_df.iterrows():
#                     #If this isn't a blank entry, add a unique map unit
#                     if row[column] == '' or (row[column] is None):
#                         unique_mapunits.append(None)
#                     #TODO: Test above w/ maps with blank map units
#                     else:
#                         unique_mapunits.append('{}|{}'.format(str(mapsource_id),row[column]))
#                 table_df[column] = unique_mapunits
                    
#         gems_db_dict[tablename] = table_df

#     return gems_db_dict

def _transform_add_foreignkeyfields_to_accompany_mapunit(gems_db_dict,do_update_in_place = True):
    """_summary_

    #TODO: Is it worthwhile (or possible) to abstract this function?
    Args:
        gems_db_dict (_type_): _description_
        do_update_in_place (bool, optional): _description_. Defaults to True.

    Returns:
        _type_: _description_
    """
    #Pseudo-constants in the event this logic could stay but apply to a different table
    TBL = 'descriptionofmapunits'
    EXISTINGPK_FIELD = 'mapunit'
    EXISTINGFK_FIELD = 'mapunit'
    ROBUSTPK_FIELD = 'descriptionofmapunits_id'
    ROBUSTFK_FIELD = 'descriptionofmapunitsid'

    #Swap the variable of the gems_db_dict with a copy if we don't want to copy in place
    if not(do_update_in_place):
        unq_dict = {}
        for tbl in gems_db_dict:
            unq_dict[tbl] = gems_db_dict[tbl].copy()
        gems_db_dict = unq_dict

    #Get the dmu
    dmu_df = gems_db_dict[TBL]
    
    # print(dmu_df.columns)

    #Get a dictionary that maps mapunits to description of map unit ids
    mapunit_id_map = {}
    for i,row in dmu_df.iterrows():
        mapunit_id_map[row[EXISTINGPK_FIELD]] = row[ROBUSTPK_FIELD]

    #Loop through all the tables (that aren't the 'descriptionofmapunits')
    tables_to_update = [tbl for tbl in gems_db_dict if not(tbl==TBL)]

    #For each table
    for tbl in tables_to_update:
        
        #Check this table for containing 'mapunit' field
        if EXISTINGFK_FIELD in GEMS_TABLE_FIELD_DICT[tbl]:
            # print('Starting on tbl: {}'.format(tbl))
            #Get the table
            tbl_df = gems_db_dict[tbl]
            # print('columns present: {}'.format(tbl_df.columns))
            #Preallocate an empty list to store the _id values
            dmu_ids = []
            #For each record in the table
            for i,row in tbl_df.iterrows():
                #assign a blank id in case there is no defined foreign key
                id = None
                #Check that this is actually a valid mapunit defined in the dmu table
                if row[EXISTINGPK_FIELD] in mapunit_id_map:
                    #If this was a mapunit we could map to a descriptionofmapunits id, store the id
                    id = mapunit_id_map[row[EXISTINGPK_FIELD]]
                dmu_ids.append(id)
            #Assign all ids
            tbl_df[ROBUSTFK_FIELD] = dmu_ids

            #Pass back to db_dict
            gems_db_dict[tbl] = tbl_df
    
    return gems_db_dict

def _transform_single_table_flatten_additional_columns_to_json(table_df: gpd.GeoDataFrame, columns_for_insert: list,do_update_in_place: bool = True,extra_attributes_column: str = None):
    """ Removes unwanted columns from a table and converts them to a json format.

    Args:
        table_df (gpd.GeoDataFrame): _description_
        columns_for_insert (list): _description_
        do_update_in_place (bool, optional): _description_. Defaults to True.
        extra_attributes_column (str, optional): _description_. Defaults to None.

    Returns:
        _type_: _description_
    """

    #If no column name was specified, use the default
    if extra_attributes_column is None:
        extra_attributes_column = EXTRAITEMSFIELD

    #Swap the variable of the table_df with a copy if we don't want to copy in place
    if not(do_update_in_place):
        table_df = table_df.copy()

    #Get the list of columns for the json records
    columns_for_json = [c for c in table_df.columns if (not(c in columns_for_insert) and not(c in EXTRAITEMSTOIGNORE))]
    columns_to_drop = [c for c in table_df.columns if not(c in columns_for_insert)]

    #Get a version of the dataframe with the records to keep and those to json-ize
    #Convert geodataframes to a dataframe, geodataframe's .to_json() function creates a geojson, which has a lot more in it than we want
    df_tojson = pd.DataFrame(table_df[columns_for_json])

    if do_update_in_place:
        #If updating in place, the drop function has no return
        table_df.drop(columns = columns_to_drop,inplace=do_update_in_place)
    else:
        #If not updating in place, replace our copy of table_df
        table_df = table_df.drop(columns = columns_to_drop,inplace=do_update_in_place)

    #Add in the json entries as a new column to the table if needed
    #TODO: Think about reordering this code to remove the overhead above if not needed
    if len(columns_for_json) > 0:
        print('Parsing the following into json attribute: {}'.format(columns_for_json))
        json_records = []
        for i,row in df_tojson.iterrows():
            thisdict = {}
            for col in df_tojson:
                thisdict[col] = row[col]
            json_records.append(json.dumps(thisdict,cls=NpEncoder))
        
        ##Thought this might skip above loops, but This produces a single string that is inserted into each record
        #json_records = df_tojson.to_json(orient='records')

        table_df[extra_attributes_column] = json_records

    return table_df

def _transform_flatten_additional_columns_to_json(gems_db_dict):
    
    for table in gems_db_dict:
        table_df = gems_db_dict[table]
        columns_to_preserve = [c for c in GEMS_TABLE_FIELD_DICT[table]]

        if SELFREFERENCEFIELD in table_df:
            columns_to_preserve.append(SELFREFERENCEFIELD)

        if table in GEMS_SPATIAL_TABLES_FIELDS:
            columns_to_preserve.append('geometry')

        gems_db_dict[table] = _transform_single_table_flatten_additional_columns_to_json(table_df,columns_to_preserve,extra_attributes_column=EXTRAITEMSFIELD)
    
    return gems_db_dict

def transform_gems_dict_of_dataframes(gems_db_dict,mapsource_id,datasources_delimiter):

    #Remap and sanitize fields names
    # print('remap fields...')
    gems_db_dict = _transform_sanitize_and_remap_gems_fields(gems_db_dict)

    #Preform any necessary spatial manipulation
    # print('spatial transform...')
    gems_db_dict = _transform_projection_spatial_manipulation(gems_db_dict)

    #Clean up concatenated datasources
    # print('concatenated datasources...')
    if not(datasources_delimiter is None):
        gems_db_dict = _transform_gems_concatenated_datasources_to_primarykeys(gems_db_dict,delimiter=datasources_delimiter,new_delimiter=DB_DELIMITER)
    
    #Filter unused gems feautres
    # print('drop unused...')
    gems_db_dict, unused_item_dict = _transform_drop_unused_gems_features(gems_db_dict)

    #######CHANGE FROM NGS - just leaving mapunit as their native, unique values
    #Update all 'mapunit' fields with new unique mapunit
    # print('uniqueify mapunit')
    # gems_db_dict = _transform_uniqueify_mapunit_values(gems_db_dict,mapsource_id) 

    #######CHANGE FROM NGS - incoming maps may not use the same geomaterials
    gems_db_dict = _transform_reset_geomaterial_values(table_df=gems_db_dict)

    #######CHANGE FROM NGS - convert is concealed to always lowercase
    gems_db_dict = _transform_lowercase_onecharacter_isconcealed(gems_db_dict)

    #Add descriptionofmapunts_id foreignkey
    # print('add domu_id fields')
    gems_db_dict = _transform_add_foreignkeyfields_to_accompany_mapunit(gems_db_dict)

    #Add that we also want to save 'geometry' if expected - though we won't insert it into the database as 'geometry' so need to flag seperately
    #check that columns match what is expected to be in table
    # print('Flatten additional to json...')
    # gems_db_dict = _transform_flatten_additional_columns_to_json(gems_db_dict)

    return gems_db_dict, unused_item_dict

###########################################################################################################################
#### LOAD
###########################################################################################################################
def _load_update_foreignkeys_with_db_primarykeys(updated_pfkey_dict,target_table:str,table_df: gpd.GeoDataFrame,do_update_in_place = True,update_errors = None):
    """
    Updates a table in a dataframe with new values of the primary keys stored in a database repository. Requires that
    new primary keys have been established to update the foreign keys in this table.

    Args:
        updated_pfkey_dict (dict of dicts): #structure is updated_pfkey_dict[(<primarytable>,<primaryfield>)] = dict[oldkey] = newkey
        target_table (str): _description_
        table_df (gpd.GeoDataFrame): _description_
        do_update_in_place (bool, optional): Whether to update the table records in place (True) or create a copy to
        update. Defaults to True.

    Returns:
        _type_: _description_
    """

    #Keep track of any errors created when trying to update foreign keys
    if update_errors is None:
        update_errors = []

    #Swap the variable of the gems_db_dict with a copy if we don't want to copy in place
    if not(do_update_in_place):
        table_df = table_df.copy()

    #Does this table have foriegn keys specified in the foreign key dict?
    if target_table in GEMS_TABLE_FK_DICT:
        #Lookup the foreign keys and the table,field they map to
        fkfields_tables = GEMS_TABLE_FK_DICT[target_table]

        #For each foreign key
        for fkfield,table_fkfield in fkfields_tables:
            #Loop through the database
            for i,row in table_df.iterrows():
                #Assign this table record the new value from the updated primary key dictionary 
                try:
                    #TODO: kludge on gems letting some datasources be null (descriptionsourceid in DMU headers)
                    #All other datasourceid fields should not be nullable in the database, so should throw an error
                    if row[fkfield] is not None:
                        new_fk = updated_pfkey_dict[table_fkfield][row[fkfield]]
                    else:
                        new_fk = None
                    table_df.loc[i,fkfield] = new_fk
                except KeyError:
                    #It's possible this record has some fields w/ weird data types (e.g., timestamps, geometries) that we haven't yet sanitized. 
                    cols_to_keep = [col for col in row if col in GEMS_TABLE_FIELD_DICT[target_table]]
                    bad_row = row[cols_to_keep].to_dict()
                    bad_row['ErrorType'] = 'Foreign key update error, no key {} found for field {}'.format(row[fkfield],fkfield)
                    update_errors.append(bad_row)
        
        #TODO: Need to add some logic to check for foreign key fields in 'additional_attributes' that would need to be updated
        #For now that might just be checking if this table has an additional_attributes that end in '...sourceid', then 
        #checking if a particular attribute is not null, then trying to lookup that value

    return table_df,update_errors

def _load_gems_table_update_keys(engine,db_metadata, updated_pfkey_dict,target_table:str,table_df, mapsourcedid: str,doAllowOnlySubsetOfGeMSFields = False):
    """ Ingest a gems database table, replacing any existing foreign key values with new values, and recording
    new primary key values.

    Args:
        engine (_type_): _description_
        db_metadata (_type_): _description_
        updated_pfkey_dict (_type_): structure is updated_pfkey_dict[(<primarytable>,<primaryfield>)] = dict[oldkey] = newkey
        target_table (str): _description_
        table_df (_type_): _description_

    Returns:
        _type_: _description_
    """
    
    #Keep track of any insertion errors
    etl_errors = []

    #Get the table object describing that table
    table_obj = get_table_object_from_gems_tablename(engine,db_metadata,target_table)
    
    #check that columns match what is expected to be in table
    columns_for_insert = GEMS_TABLE_FIELD_DICT[target_table].copy()

    #Add that we also want to save 'geometry' if expected - though we won't insert it into the database as 'geometry' so need to flag seperately
    # columns_to_preserve = [c for c in columns_for_insert]
    # if target_table in GEMS_SPATIAL_TABLES_FIELDS:
    #     columns_to_preserve.append('geometry')

    #update any foreign keys with the correct primary key values
    table_df,etl_errors = _load_update_foreignkeys_with_db_primarykeys(updated_pfkey_dict,target_table,table_df,update_errors=etl_errors)

    #Need to be sure to insert any extra items if there were any
    if EXTRAITEMSFIELD in table_df:
        columns_for_insert.append(EXTRAITEMSFIELD)

    #TODO: testing multi data source self-reference
    if SELFREFERENCEFIELD in table_df:
        columns_for_insert.append(SELFREFERENCEFIELD)

    #If we are allowing some null GeMS fields...
    #TODO: Should I allow this...
    if doAllowOnlySubsetOfGeMSFields:
        columns_for_insert = [c for c in columns_for_insert if c in table_df.columns]
    
    #identify what the primary key(s) is in this gems table - TODO: Is this necessary? Should we just force a single pkey?
    pk_fields = [v.name for v in db.inspect(table_obj).primary_key.columns.values()]

    #Preperation for inserting geometries alongside this table, if needed
    #If we are adding geometries to this table - TODO: could make this cleaner, currently this is an artifact of needing to write textual SQL statement for geometry inserts to add SDE datatypes
    insert_func = 'INSERT_NOT_EXPECTED' #If this isn't actually a spatial table, insert a dummy function that will error and alert us
    geom_field = 'NO_GEOM_EXPECTED'
    table_pk = 'NO_GEOM_EXPECTED'
    do_insert_spatial_data = False
    if target_table in GEMS_SPATIAL_TABLES_FIELDS:
        table_pk,geom_field,insert_func = GEMS_SPATIAL_TABLES_FIELDS[target_table]
        do_insert_spatial_data = True
        table_df['wkb'] = table_df.geometry.to_wkb()

    #TODO: can I streamline this now that we are pushing into postgis?
    geomUpdateStr = """UPDATE {schema:}.{table:} SET {geom_field}=ST_Force2D({insert_func}(:wkb,{EPSG:})) WHERE {table_pk:}=:id;""".format(schema=SOURCE_DATA_SCHEMA,table=target_table,geom_field=geom_field,insert_func = insert_func, EPSG=PROJ_SRID, table_pk=table_pk)
    update_statement = db.sql.text(geomUpdateStr)
    
    #insert rows, keeping track of any insertion errors
    for i,row in table_df.iterrows():
        # print(row)
        #Create a blank dict of what needs to be inserted
        to_insert = {}

        #Find columns that are not primary keys. Could just strip out the pkey columns from the list, but may want more
        #flexibility in the future.
        for col in columns_for_insert:
            #Don't insert the primary key field
            if not(col in pk_fields):
                #but that column should only be visited her if it was added to columns_for_insert above...
                to_insert[col] = row[col]

        #Add a columns for the mapsourcesid foreign key
        to_insert[MAPSOURCES_FOREIGNKEY] = mapsourcedid

        #TODO: More testing of self refencing column
        if SELFREFERENCEFIELD in columns_for_insert:
            if to_insert[SELFREFERENCEFIELD]:
                to_insert[SELFREFERENCEFIELD] = [updated_pfkey_dict[(target_table,pk_field)][selfrefid] for selfrefid in row[SELFREFERENCEFIELD]]
                # print('new self ref field: {}'.format(to_insert[SELFREFERENCEFIELD]))

        #Try to insert the data and get the new primary key, if we hit an exception from an error related to insertion, track that so we can fix issues in bulk
        try:
            res = insert_db_record(engine,db_metadata,target_table,to_insert)
            new_pkey = res.inserted_primary_key[0] #This appears to return a tuple of one item

            #Insert geometry as needed
            if do_insert_spatial_data:
                this_data = {'id':new_pkey,'wkb':row['wkb']}
                engine.execute(update_statement,this_data)

            #Update the lookup table of primary keys
            for pk_field in pk_fields:
                #If this is a primary key we need to
                if (target_table,pk_field) in updated_pfkey_dict: 
                    updated_pfkey_dict[(target_table,pk_field)][row[pk_field]] = new_pkey

        # except (DatabaseError,IntegrityError) as e:
        except Exception as e:
            bad_row = to_insert.copy()
            bad_row ['ErrorType']= repr(e)
            etl_errors.append(bad_row)
    # print('finished table: {}'.format(target_table))
    return updated_pfkey_dict, etl_errors

def _load_mapsource_poly(conn,mapsource_id,mapunitpolys_df, mapboundary_tolerance = 100):

    #Construct the sql statement that will be needed
    insert_func = 'ST_GeomFromWKB'
    geomUpdateStr = """INSERT INTO source.mapsourcepolys (mapsourceid,shape) VALUES (:msid,ST_Force2D(ST_Multi({insert_func}(:wkb,{EPSG:}))));""".format(insert_func = insert_func, EPSG=PROJ_SRID)

    update_statement = db.sql.text(geomUpdateStr)

    #Flatten mapunit polys to one bounding poly - a slow approach.
    polygon = mapunitpolys_df.geometry.unary_union #First combine all polygons into one shape
    #Currently not simplifying - so could just use the polygon above
    # df2 = gpd.GeoDataFrame(geometry=[polygon], crs=mapunitpolys_df.crs)#.simplify(tolerance = mapboundary_tolerance) #Turn this into a gdf and simplify the geometry
    # wkb = df2.geometry[0].wkb #Turn the simplified geometry into the wkb representation
    wkb = polygon.wkb
    
    this_data = {'msid':mapsource_id,'wkb':wkb}
    conn.execute(update_statement,this_data)

    return None

def _load_unused_tables_json(engine,db_metadata,mapsource_id,unused_item_dict):

    #Add unused_item_dict as json to mapunits table
    json_unused_items = json.dumps(unused_item_dict)

    #TODO: Add check that the primary key is actually present. Otherwise this seems to work.
    mapsources_primarykey = db.inspect(get_table_object_from_gems_tablename(engine,db_metadata,MAPSOURCES_TBLNM)).primary_key.columns.values()[0].name
    
    replace_db_records(engine,db_metadata,MAPSOURCES_TBLNM,mapsources_primarykey,
                        mapsource_id,{EXTRAMAPSOURCEFEATURESFIELD:json_unused_items})

def load_gems_database(engine,db_metadata,gems_db_dict,mapsource_id,etl_errors,doAllowOnlySubsetOfGeMSFields = False):
    
    #Updated primary-foreign key dict - initially empty
    updated_pfkey_dict = {
        #structure is updated_pfkey_dict[(<primarytable>,<primaryfield>)] = dict[oldkey] = newkey
    }

    #Preallocate the map to new keys with all the expected primary key fields
    for key in GEMS_TABLE_FK_DICT:
        table_key = GEMS_TABLE_FK_DICT[key]
        for tk_i in table_key:
            #tk_i is a list of two items a string and a tuple: [fk_fieldinatable, (table_hosting_pk,pk_field)]
            table_field_tuple = tk_i[1]

            #If this primarytable,primarykeyfield tuple is not already an entry in the dict, add it
            if not(table_field_tuple in updated_pfkey_dict):
                updated_pfkey_dict[table_field_tuple] = {} #Create a place to dump foreign keys

    #For each table in hierarchical order based on primary key proliferation
    for tablename in GEMS_TABLE_INGESTION_ORDER:
        #If that table was present in this database
        if tablename in gems_db_dict:
            #Ingest the table, keeping track of the mapping between old and new primary keys
            print('Working on ingesting table: {}'.format(tablename))
            table_df = gems_db_dict[tablename]

            updated_pfkey_dict, etl_errors_list = _load_gems_table_update_keys(engine,db_metadata, updated_pfkey_dict,tablename,table_df,mapsource_id,doAllowOnlySubsetOfGeMSFields = doAllowOnlySubsetOfGeMSFields)
            # print(etl_errors_list)
            #Grow the list of possible insertion errors if there were any, keeping everything formatted as json dictionaries
            if len(etl_errors_list)>=1:
                etl_errors[tablename] = _etl_format_insertion_error_list(etl_errors_list)

    return etl_errors

###########################################################################################################################
#### EXTRACT - TRANSFORM - LOAD
###########################################################################################################################

def _etl_format_insertion_error_list(etl_errors_list):
    #Convert these insertion errors to a list of unique problems
    etl_errors_dict = {}

    #Add all the types of errors in as their own dictionaries
    for err in etl_errors_list:
        if err['ErrorType'] in etl_errors_dict:
            etl_errors_dict[err['ErrorType']].append(err)
        else:
            etl_errors_dict[err['ErrorType']] = [err]

    #Drop non-unique entries
    for key in etl_errors_dict:
        table = etl_errors_dict[key]

        #Turn this into a pandas df
        etl_errors_dict[key] = pd.DataFrame(table).drop_duplicates().reset_index()
        
    return etl_errors_dict

def etl_gems_database(engine,db_metadata,path_to_gdb,mapsource_id:str,datasources_delimiter = None,doAllowOnlySubsetOfGeMSFields = False):
    #TODO: This function should probably be adjusted to take the info needed to insert a mapsource
    etl_errors = {}
    try:
        #TODO: update error catching to also occur on E and T steps 
        #Extract gems database
        # print('extract...')
        gems_db_dict = extract_gems_database_to_dict_of_dataframes(path_to_gdb)

        #Transform gems datbase
        # print('transform...')
        gems_db_dict,unused_item_dict = transform_gems_dict_of_dataframes(gems_db_dict,mapsource_id,datasources_delimiter)

        #Load unused featuresclasses into mapsources
        # print('load unused...')
        _load_unused_tables_json(engine,db_metadata,mapsource_id,unused_item_dict)

        # print('remaining load...')
        etl_errors = load_gems_database(engine,db_metadata,gems_db_dict,mapsource_id,etl_errors,doAllowOnlySubsetOfGeMSFields = doAllowOnlySubsetOfGeMSFields)
    
    except Exception as e:
        etl_errors['Overall error'] = {'Unexpected error, check GeMS Validation': pd.DataFrame({'Error':[repr(e)]})}

    #If there were any insertion errors, we do not want to preserve this record in the DB
    if len(etl_errors)>=1:
        print('Errors detected in {} tables for mapsource: {}, removing associated data...'.format(len(etl_errors),mapsource_id))
        # for table in etl_errors:
        #     print('Errors in {} table : \n'.format(table))
        #     print(etl_errors[table])
        table_obj = db_metadata.tables['source.mapsources']
        stmt = db.delete(table_obj).where(table_obj.c.mapsources_id == mapsource_id)
        engine.execute(stmt)
    #If there were no insertion errors
    else:
        #TODO: add some error checking around this?
        if 'mapunitpolys' in gems_db_dict:
            print('No mapunitpolys found to build mapsourcepolys')
            _load_mapsource_poly(engine,mapsource_id,gems_db_dict['mapunitpolys'], mapboundary_tolerance = 100)
        print('Succesfully ingested: {}'.format(mapsource_id))

    #TODO: Load metadata into database too?

    return etl_errors

def etl_multiple_gdbs(engine,db_metadata,mapsources_etl_template,datasources_delimiter = None,doAllowOnlySubsetOfGeMSFields = False):
    
    if isinstance(mapsources_etl_template,str):
        #Import the spreadsheet ingestion template
        extension = os.path.splitext(mapsources_etl_template)[-1]
        if extension == '.csv':
            ingest_df = pd.read_csv(mapsources_etl_template,index_col='datasetpath')
        elif extension == '.xlsx':
            ingest_df = pd.read_excel(mapsources_etl_template,index_col='datasetpath')
        else:
            raise KeyError('Error: ingestion template file must be either a .csv or .xlsx file')
    elif isinstance(mapsources_etl_template,pd.DataFrame):
        ingest_df = mapsources_etl_template

    #Loop through the ingestion df, keeping track of any errors
    ingestion_errors = {}
    ingested_mapsource_ids = []
    for path_to_gdb,row in ingest_df.iterrows():

        #Add this reference to the map sources table
        mapsource_entry = {}
        for col in ingest_df.columns:
            mapsource_entry[col] = row[col]

        #TODO: Should probably do these in a connection, should also add a catch for if an ingestion
        #fails (if it does, delete its mapsources entry), and one that provides
        #better detail if a record was already inserted
       
        with engine.connect().execution_options(isolation_level = 'AUTOCOMMIT') as conn:

            #Check if there is a geodatabase at the specified location
            #TODO: Should use fiona or similar to actually check if this is a .gdb... could even use gems toolbox to check thats its gems-3
            if os.path.exists(path_to_gdb):
                #TODO: should probably put this in a try/except too... to take more care that we don't ingest multiple sources
                print('Adding mapsource: {}'.format(row['source']))

                try:
                    table_obj = db_metadata.tables['source.mapsources']
                    stmt = table_obj.insert().values(mapsource_entry)
                    res = conn.execute(stmt)

                    #Get the newly inserted primary key
                    mapsource_id = res.inserted_primary_key[0]

                    # print('Ingesting gems gdb and updating keys...')
                    ingest_errors_i = etl_gems_database(conn,db_metadata,path_to_gdb,mapsource_id,datasources_delimiter=datasources_delimiter,doAllowOnlySubsetOfGeMSFields = doAllowOnlySubsetOfGeMSFields)

                    #If there are any dictionary errors
                    if ingest_errors_i:
                        ingestion_errors[mapsource_id] = ingest_errors_i
                    #If there are no errors, add this mapsource_id to the list
                    else:
                        ingested_mapsource_ids.append(mapsource_id)
                
                except Exception as e:
                    #TODO: I should think about how to enable this catch to delete mapsources that busted
                    # print('Exception occured: {}'.format(repr(e)))
                    # print('Ensure mapsource {} does not already exist.'.format(row['source']))
                    pass
            else:
                print('No gdb found for source: {} at path {}'.format(row['source'],path_to_gdb))


    return ingestion_errors, ingested_mapsource_ids