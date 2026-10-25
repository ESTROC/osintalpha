"""Case-scoped research tasks: assignments, deadlines, priority, audit and review."""
from __future__ import annotations
from datetime import date,datetime,timezone
from typing import Literal
from fastapi import APIRouter,Depends,HTTPException,Query
from pydantic import BaseModel,Field
from . import main as core,db

router=APIRouter()
Status=Literal['todo','in_progress','blocked','awaiting_review','done','cancelled']
Priority=Literal['low','normal','high','critical']
class TaskInput(BaseModel):
    title:str=Field(min_length=3,max_length=180)
    description:str=Field(default='',max_length=2500)
    priority:Priority='normal'
    status:Status='todo'
    assigned_to:str|None=Field(default=None,max_length=60)
    due_date:str=Field(default='',max_length=10)
class TaskChange(BaseModel):
    status:Status
    note:str=Field(min_length=8,max_length=1200)

def check_date(value):
    if not value:return ''
    try:
        if date.fromisoformat(value).isoformat()!=value:raise ValueError('invalid')
    except ValueError as exc:raise HTTPException(422,'Due date must be YYYY-MM-DD') from exc
    return value

def assignee(conn,id,case,actor):
    if not id:return None
    row=conn.execute('SELECT id FROM users WHERE id=? AND active=1',(id,)).fetchone()
    if not row:raise HTTPException(422,'Choose an existing active analyst.')
    if id!=case['created_by'] and not (actor['role']=='admin' and id==actor['id']):
        raise HTTPException(422,'Only the case owner or the administrator managing this case may be assigned. Cross-user sharing is not enabled.')
    return id

@router.get('/api/cases/{case_id}/tasks')
def list_tasks(case_id:str,status:Literal['all','todo','in_progress','blocked','awaiting_review','done','cancelled']='all',
               page:int=Query(default=1,ge=1,le=100000),page_size:int=Query(default=50,ge=1,le=100),
               actor=Depends(core.actor_from_cookie)):
    with db.connect() as c:
        core.case_or_404(c,case_id,actor)
        clause='case_id=?'+(' AND status=?' if status!='all' else '')
        args=[case_id]+([status] if status!='all' else [])
        total=c.execute('SELECT count(*) n FROM investigation_tasks WHERE '+clause,args).fetchone()['n']
        rows=c.execute('''SELECT t.*,u.username assignee_name FROM investigation_tasks t
            LEFT JOIN users u ON u.id=t.assigned_to WHERE t.'''+clause+
            ' ORDER BY CASE t.priority WHEN \'critical\' THEN 0 WHEN \'high\' THEN 1 WHEN \'normal\' THEN 2 ELSE 3 END,'+
            ' CASE WHEN t.due_date=\'\' THEN 1 ELSE 0 END,t.due_date,t.created_at DESC,t.id LIMIT ? OFFSET ?',
            args+[page_size,(page-1)*page_size])
        return {'items':[dict(x) for x in rows], 'total':total, 'page':page,
                'totalPages':(total+page_size-1)//page_size}

@router.post('/api/cases/{case_id}/tasks',status_code=201)
def create_task(case_id:str,body:TaskInput,actor=Depends(core.protect)):
    due=check_date(body.due_date)
    with db.connect() as c:
        case=core.case_or_404(c,case_id,actor)
        who=assignee(c,body.assigned_to,case,actor)
        id=core.uid();now=core.iso_now()
        c.execute('INSERT INTO investigation_tasks VALUES (?,?,?,?,?,?,?,?,?,?,?)',
          (id,case_id,body.title.strip(),body.description.strip(),body.status,body.priority,
           who,due,actor['id'],now,now))
        c.execute('INSERT INTO investigation_task_events VALUES (?,?,?,?,?,?,?,?)',
          (core.uid(),id,case_id,actor['id'],'',body.status,'Research task created.',now))
    core.write_audit(actor['id'],'task_create','case',case_id,id)
    return {'id':id,'status':body.status}

@router.patch('/api/cases/{case_id}/tasks/{task_id}')
def change_task(case_id:str,task_id:str,body:TaskChange,actor=Depends(core.protect)):
    with db.connect() as c:
        core.case_or_404(c,case_id,actor)
        record=c.execute('SELECT * FROM investigation_tasks WHERE case_id=? AND id=?',(case_id,task_id)).fetchone()
        if not record:raise HTTPException(404,'Research task not found')
        # Completed reviews require an explicit review event, not a silent status update.
        if body.status=='done' and record['status'] not in ('in_progress','awaiting_review'):
            raise HTTPException(422,'Move this task into progress or review before marking it done.')
        if body.status=='done' and len(body.note.strip())<20:
            raise HTTPException(422,'Record the reviewed result or limitation (at least 20 characters).')
        c.execute('UPDATE investigation_tasks SET status=?,updated_at=? WHERE id=?',
                  (body.status,core.iso_now(),task_id))
        c.execute('INSERT INTO investigation_task_events VALUES (?,?,?,?,?,?,?,?)',
                  (core.uid(),task_id,case_id,actor['id'],record['status'],
                   body.status,body.note.strip(),datetime.now(timezone.utc).isoformat(timespec='microseconds')))
    core.write_audit(actor['id'],'task_status','task',task_id,body.status)
    return {'ok':True,'status':body.status}

@router.get('/api/cases/{case_id}/tasks/{task_id}/history')
def task_history(case_id:str,task_id:str,actor=Depends(core.actor_from_cookie)):
    with db.connect() as c:
        core.case_or_404(c,case_id,actor)
        if not c.execute('SELECT id FROM investigation_tasks WHERE case_id=? AND id=?',(case_id,task_id)).fetchone():
            raise HTTPException(404,'Research task not found')
        rows=c.execute('''SELECT e.old_status,e.new_status,e.details,e.created_at,u.username actor
            FROM investigation_task_events e JOIN users u ON u.id=e.actor_id
            WHERE e.task_id=? AND e.case_id=? ORDER BY e.created_at DESC,e.id DESC LIMIT 200''',(task_id,case_id))
        return {'items':[dict(x) for x in rows]}

@router.get('/api/cases/{case_id}/task-assignees')
def task_assignees(case_id:str,actor=Depends(core.actor_from_cookie)):
    with db.connect() as c:
        core.case_or_404(c,case_id,actor)
        case=core.case_or_404(c,case_id,actor)
        identifiers=[case['created_by']]
        if actor['role']=='admin':identifiers.append(actor['id'])
        rows=c.execute('SELECT id,username FROM users WHERE active=1 AND id IN ('+
                       ','.join('?' for _ in identifiers)+') ORDER BY username',identifiers)
        return {'items':[dict(x) for x in rows]}
