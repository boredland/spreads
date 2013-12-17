import json
import logging
import os
import sqlite3
from collections import namedtuple

from flask import g
from spreads.workflow import Workflow

from spreadsplug.web import app

SCHEMA = """
create table workflow (
    id              integer primary key autoincrement not null,
    name            text,
    step            text,
    step_done       boolean,
    capture_start   integer,
    config          text
);
"""

DbWorkflow = namedtuple('DbWorkflow', ['id', 'name', 'step', 'step_done',
                                       'capture_start', 'images', 'config',
                                       'out_files'])
logger = logging.getLogger('spreadsplug.web.database')


@app.before_request
def open_connection():
    db_path = app.config['database']
    logger.debug('Opening database connection to \"{0}\"'.format(db_path))
    db_is_new = not os.path.exists(db_path)
    db = g.db = sqlite3.connect(db_path)
    if db_is_new:
        logger.info('Initializing database.')
        db.executescript(SCHEMA)


@app.teardown_appcontext
def close_connection(exception):
    logger.debug('Closing database connection')
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


def save_workflow(workflow):
    cursor = g.db.cursor()
    cursor.execute(
        "insert into workflow values (?,?,?,?,?,?)",
        DbWorkflow(id=None, name=os.path.basename(workflow.path),
                   step=workflow.step, step_done=workflow.step_done,
                   capture_start=workflow.capture_start,
                   config=json.dumps(workflow.config.flatten()))
    )


def update_workflow_config(id, config_data):
    cursor = g.db.cursor()
    cursor.execute("update workflow set config=:config where id=:id",
                   dict(config=config_data, id=id))


def get_workflow(workflow_id):
    cursor = g.db.cursor()
    db_data = cursor.execute("select * from workflow where workflow.id=?",
                             (workflow_id,)).fetchone()
    if db_data is None:
        return None

    db_workflow = DbWorkflow(*db_data)
    # FIXME: Configuration can't be passed like this
    workflow = Workflow(
        config=json.loads(db_workflow.config),
        path=os.path.join(app.config['base_path'], db_workflow.name),
        step=db_workflow.step,
        step_done=bool(db_workflow.step_done))
    return workflow


def get_workflow_list():
    result = g.db.cursor().execute(
        "select id, name, step, step_done from workflow").fetchall()
    return [dict(id=x[0], name=x[1], step=x[2], step_done=bool(x[3]))
            for x in result]
