import json
import logging
from pathlib import Path
from shlex import split as split_
from subprocess import run

from click import secho
from mapboard.topology_manager.cli import operation_command
from mapboard.topology_manager.commands.create_tables import _create_tables
from mapboard.topology_manager.commands.update import _update
from sqlalchemy.exc import IntegrityError, ProgrammingError
from sqlparse import format, split

from macrostrat.database import Database

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


def run_topology_command(db: Database, project_id, command):
    """
    Possible Commands:
    update
    reset
    delete
    create_tables
    """

    # Invoke typer app commands directly

    if command == "update":
        return _update(db)
    elif command == "reset":
        return operation_command(db, "reset", ask=False)
    elif command == "create_tables":
        return _create_tables(db)
    elif command == "delete":
        return operation_command(db, "delete", ask=False)
    else:
        raise ValueError(f"Unknown command: {command}")


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


def create_project_config(project):
    project_id = project.id
    name = project.name
    description = project.description
    config = {}
    config["project_schema"] = f"project_{project_id}"
    config["project_id"] = project_id
    config["name"] = name
    config["description"] = description
    config["data_schema"] = f"project_{project_id}_data"
    config["topo_schema"] = f"project_{project_id}_topology"
    config["tolerance"] = 0.0001
    ## these are the 'defaults'
    config["connection"] = {
        "database": "geologic_map",
        "port": 5432,
        "host": "db",
        "user": "postgres",
    }

    # fn = config_dir / f"project_{project_id}.json"
    # with open(fn, "w") as f:
    #     json.dump(config, f)
    # print("Configuration file sucessfully created")
    return config


def config_check(project):
    if not hasattr(project, "id"):
        return {}
    # project_id = project.id
    # config_fn = config_dir / f"project_{project_id}.json"
    #
    # if config_fn.exists():
    #     print("Configuration file exists")
    #     return get_config(project_id)
    # else:
    #     print("Config does not exist")
    return create_project_config(project)


def get_config(project_id):
    config_fn = config_dir / f"project_{project_id}.json"
    config_json = json.load(open(config_fn))
    return config_json


def delete_config(project_id):
    config_fn = config_dir / f"project_{project_id}.json"
    try:
        config_fn.unlink()
    except OSError as e:
        print(f"Error:{ e.strerror}")


def id_check(id_: int = None):
    def project_exists(func):
        """custom decorator to check if project exists on db instance"""

        def check(*args, **kwargs):
            if id_ is not None:
                func(*args, **kwargs)
            else:
                raise AttributeError(
                    "Database needs a project_id attribute for this method"
                )

        return check

    return project_exists
