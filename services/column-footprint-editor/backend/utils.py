from subprocess import run as _run
from click import secho
from sqlparse import split, format
from sqlalchemy.exc import ProgrammingError, IntegrityError


def run(*args, **kwargs):
    command = " ".join(args)
    if kwargs.pop("echo", True):
        secho(command, fg="cyan")
    kwargs["shell"] = True
    return _run(command, **kwargs)


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


def run_sql_file(sql_file, **kwargs):
    sql = open(sql_file).read()
    return run_sql(sql, **kwargs)


def run_query(db, filename_or_query, **kwargs):
    """
    Run a query on a SQL database (represented by
    a SQLAlchemy database object) and turn it into a
    `Pandas` dataframe.
    """
    from pandas import read_sql        
    
    if "SELECT" in str(filename_or_query):
        # We are working with a query string instead of
        # an SQL file.
        sql = filename_or_query
    else:
        with open(filename_or_query) as f:
            sql = f.read()

    return read_sql(sql, db, **kwargs)

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

        
 
    


