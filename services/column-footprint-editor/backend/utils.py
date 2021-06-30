from click import secho
from sqlparse import split, format
from sqlalchemy.exc import ProgrammingError, IntegrityError
from shlex import split as split_
from subprocess import run
from pathlib import Path
import json
import logging

here = Path(__file__).parent
config_dir = here / "config"

def get_logger(name=None, level=logging.DEBUG, handler=None):
    log = logging.getLogger(name)
    log.setLevel(level)
    if handler:
        log.addHandler(handler)
    return log

log = get_logger(__name__)

def split_args(*args):
    return split_(" ".join(args))

def cmd(*v, **kwargs):
    logger = kwargs.pop("logger", log)
    val = " ".join(v)
    logger.debug(val)
    return run(split_(val), **kwargs)

def run_docker_config(project_id, command):
    """
    Possible Commands:
    update
    reset
    delete
    create_tables 
    """
    exec_ = f"docker exec -it -e GEOLOGIC_MAP_CONFIG=/var/config/project_{project_id}.json postgis-geologic-map_app_1" 
    base = exec_ + " bin/geologic-map"
    update = base + " update"
    reset = base + " reset"
    delete = base + " delete"
    create_tables = base + " create-tables --all"

    if command == "update":
        cmd_ = update
    if command == "reset":
        cmd_ = reset
    if command == "create_tables":
        cmd_ = create_tables
    if command == "delete":
        cmd_ = delete

    return cmd(cmd_)

# The below functions are stolen from sparrow; we should place them in a utility module


def pretty_print(sql, **kwargs):
    for line in sql.split("\n"):
        for i in ["SELECT", "INSERT", "UPDATE", "CREATE", "DROP", "DELETE", "ALTER"]:
            if not line.startswith(i):
                continue
            start = line.split("(")[0].strip().rstrip(";").replace(" AS", "")
            secho(start, **kwargs)
            return


def run_sql(sql, params=None, session=None):
    queries = split(sql)
    for q in queries:
        sql = format(q, strip_comments=True).strip()
        if sql == "":
            continue
        try:
            session.execute(sql, params=params)
            session.commit()
            pretty_print(sql, dim=True)
        except (ProgrammingError, IntegrityError) as err:
            err = str(err.orig).strip()
            dim = "already exists" in err
            session.rollback()
            pretty_print(sql, fg=None if dim else "red", dim=True)
            if dim:
                err = "  " + err
            secho(err, fg="red", dim=dim)


def change_set_clean(change_set):
    '''
    This function cleans the change_set passed from frontend

    The goal is to condense changes to similar features. This is most important 
    when creating a new feature and then continuing to edit it before saving because it doesn't 
    have a postgres ID yet. But it does have an internal id from mapbox draw. 

    draw_id = object['feature']['id']

    params:
        :change_set: array of objects that are changes
    
    returns:
        :change_set: array of objects


    Idea of how to do this:
        look for "draw.create", get the internal id and then find other indices where they occur.

        then get the coordinates from the last occurence and replace the original coordinates.

        can remove those other indices then

    '''
    id_objects = [] # list of objects {id: "internal id", occurences: [indexes]}

    for line in change_set:
        if line['action'] == "draw.create":
            obj = {"id": "", "occurences": []}
            draw_id = line['feature']['id']
            obj['id'] = draw_id
            for index, l in enumerate(change_set):
                if 'id' in l['feature'] and draw_id == l['feature']['id']:
                    obj['occurences'].append(index) # add the indexes to occurneces
            id_objects.append(obj)

    for obj in id_objects:
        if len(obj['occurences']) > 1:
            first_index = obj['occurences'][0]
            final_index = obj['occurences'][-1]
            
            first_line = change_set[first_index]
            last_line = change_set[final_index]
            
            if line['action'] == "draw.delete":
                # remove all the lines
                for i in sorted(obj['occurences'], reverse=True):
                    del change_set[i] ## remove all lines by indexes in occurences
                    ## have to do it in reverse order to not throw off earlier indexes
            geom = last_line['feature']['geometry']
            first_line['feature']['geometry'] = geom
            for i in sorted(obj['occurences'][1:], reverse=True):
                # remove all occurences except for the first, which we changed to have 
                ## the coordinates of the last one.
                del change_set[i] 
        
    return change_set

def create_project_config(project_id):
    config = {}
    config['project_schema'] = f'project_{project_id}'
    config['data_schema'] = f'project_{project_id}_data'
    config['topo_schema'] = f'project_{project_id}_topology'
    config['tolerance'] = 0.0001
    ## these are the 'defaults'
    config['connection'] = {"database": "geologic_map", "port": 5432, "host": "db","user": "postgres"}

    fn = config_dir / f'project_{project_id}.json'
    with open(fn, 'w') as f:
        json.dump(config, f)
    print("Configuration file sucessfully created")
    return config

def config_check(project_id):
    config_fn = config_dir / f'project_{project_id}.json' 
    
    if config_fn.exists():
        print("Configuration file exists")
        return get_config(project_id)
    else:
        print("Config does not exist")
        return create_project_config(project_id)

def get_config(project_id):
    config_fn = config_dir / f'project_{project_id}.json'
    config_json = json.load(open(config_fn))
    return config_json

def delete_config(project_id):
    config_fn = config_dir / f'project_{project_id}.json'
    try:
        config_fn.unlink()
    except OSError as e:
        print(f"Error:{ e.strerror}")

    


        
 
    


