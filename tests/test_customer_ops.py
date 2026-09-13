import os, tempfile
fd, path = tempfile.mkstemp(prefix='customer_ops_', suffix='.db'); os.close(fd)
os.environ['AGENT_COMPANY_DB'] = path

from app.db import db, init_db
from app.customer_ops import CustomerOps
from app.communication_pipeline import CommunicationPipeline
from app.operations import OperationsMonitor


def approved_opportunity():
    with db() as conn:
        cur=conn.execute("INSERT INTO opportunities(title,brief,score,status) VALUES(?,?,?,?)", ('API project','Build a production API',90,'proposal_approved'))
        return cur.lastrowid


def test_intake_scope_approval_creates_project():
    init_db(); ops=CustomerOps(); oid=approved_opportunity()
    eng=ops.onboard(oid,'Client','c@example.com','ACME','Build API and tests',['API works'],[{'title':'M1','deliverable':'API'}],1000,'2026-10-01')
    assert eng['status']=='awaiting_scope_approval'
    approved=ops.approve_scope(eng['id'],eng['approvals'][0]['id'],True)
    assert approved['status']=='active' and approved['project_id']


def test_change_request_is_pending_and_gated():
    init_db(); ops=CustomerOps(); oid=approved_opportunity()
    eng=ops.onboard(oid,'Client','','','Build API safely',['Pass tests'],[{'title':'M1','deliverable':'Code'}])
    change=ops.request_change(eng['id'],'Add another integration',250,3)
    assert change['status']=='pending'


def test_customer_status_is_draft_only():
    init_db(); ops=CustomerOps(); oid=approved_opportunity()
    eng=ops.onboard(oid,'Client','','','Build API safely',['Pass tests'],[{'title':'M1','deliverable':'Code'}])
    eng=ops.approve_scope(eng['id'],eng['approvals'][0]['id'],True)
    draft=CommunicationPipeline().draft_status(eng['id'])
    assert draft['status']=='draft'
    assert 'pending human approval' in draft['body'].lower()


def test_unhealthy_ops_check_opens_incident():
    init_db(); monitor=OperationsMonitor()
    result=monitor.record_check('api','local-api',False,'health endpoint failed')
    assert result['incident_id'] is not None
    assert monitor.dashboard()['open_incidents']
