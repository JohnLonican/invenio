## This file is part of Invenio.
## Copyright (C) 2012 CERN.
##
## Invenio is free software; you can redistribute it and/or
## modify it under the terms of the GNU General Public License as
## published by the Free Software Foundation; either version 2 of the
## License, or (at your option) any later version.
##
## Invenio is distributed in the hope that it will be useful, but
## WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
## General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with Invenio; if not, write to the Free Software Foundation, Inc.,
## 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.

from functools import wraps
from invenio.bibworkflow_client import run_workflow, restart_workflow
from invenio.bibworkflow_engine import BibWorkflowEngine
from invenio.bibworkflow_object import BibWorkflowObject
from invenio.bibworkflow_model import Workflow, WfeObject


def set_db_context(f):
    def initialize(*args, **kwargs):
        """
        Initializes Flask and returns the given function with the
        correct context in order to run
        """
        # FIXME: This is from flaskshell.py
        # We kept the db initialization functions here instead of import *
        # as it could be good to keep it in case flaskshell will provide a function
        # instead of using import *

        # STEP 1 - Import Invenio Flask Application constructor and database object.
        from invenio.webinterface_handler_flask import create_invenio_flask_app
        from invenio.sqlalchemyutils import db

        # STEP 2 - Create application object and initialize database.
        app = create_invenio_flask_app()
        db.init_invenio()
        db.init_cfg(app)
        db.init_app(app)

        # STEP 3 - Create fake application request context and use it.
        ctx = app.test_request_context()
        ctx.push()
        # For explanation see: http://flask.pocoo.org/docs/shell/#firing-before-after-request
        app.preprocess_request()
        with app.app_context():
            return f(*args, **kwargs)
    return wraps(f)(initialize)


@set_db_context
def runit(wname, data):
    """
    Runs workflow with given name and given data.
    Data can be specified as list of objects or single id of WfeObject/BibWorkflowObjects.
    """
    wfe = BibWorkflowEngine(wname, user_id=0, module_name="aa")
    wfe.setWorkflowByName(wname)
    wfe.setCounterInitial(data)
    wfe.save()

    # do only if not this type already
    data = [BibWorkflowObject(d, wfe.db_obj.uuid) for d in data]
    run_workflow(wfe, data)
    return wfe


@set_db_context
def restartit(wid, data=None, restart_point="beginning"):
    """
    Restarts workfloe with given id (wid) and given data. If data are not
    specified then it will load all initial data for workflow. Depending on
    restart_point function can load initial or current objects.

    Data can be specified as list of objects or single id of WfeObject/BibWorkflowObjects.
    """
    if data is None:
        if isinstance(restart_point, str):
            data = WfeObject.query.filter(WfeObject.workflow_id == wid, WfeObject.version == 0)
        else:
            data = WfeObject.query.filter(WfeObject.workflow_id == wid, WfeObject.child_objects is None)
    else:
        #restart for oid, only one object
        if isinstance(data[0], (int, long)):
            data = [WfeObject.query.filter(WfeObject.id == data[0]).first()]

    workflow = Workflow.query.filter(Workflow.uuid == wid).first()
    wfe = BibWorkflowEngine(None, uuid=None, user_id=0, workflow_object=workflow, module_name="module")
    wfe.setWorkflowByName(workflow.name)

    # do only if not this type already
    data = [BibWorkflowObject(d, wfe.uuid) for d in data]
    wfe.setCounterInitial(data)
    wfe.save()
    restart_workflow(wfe, data, restart_point)