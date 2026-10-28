"""SQLite dev / PostgreSQL prod. Existing queries use '?' placeholders."""
from __future__ import annotations
import hashlib,os,re,secrets,sqlite3
from contextlib import contextmanager
from datetime import datetime,timezone
from pathlib import Path

def utcnow():return datetime.now(timezone.utc).isoformat(timespec='seconds')
def is_postgres():return bool(os.getenv('DATABASE_URL','').strip())
def db_path():return Path(os.getenv('OSINTALPHA_DB_PATH','./instance/osintalpha.db')).resolve()
class PgConnection:
    def __init__(self,c):self.connection=c
    def execute(self,sql,args=None):
        if re.match(r'^\s*INSERT\s+OR\s+IGNORE\s+INTO\s+',sql,re.I):
            sql=re.sub(r'INSERT\s+OR\s+IGNORE\s+INTO','INSERT INTO',sql,count=1,flags=re.I).rstrip().rstrip(';')+' ON CONFLICT DO NOTHING'
        return self.connection.execute(sql.replace('?','%s'),args or ())
    def executescript(self,sql):
        for item in sql.split(';'):
            if item.strip():self.connection.execute(item)
@contextmanager
def connect():
    if is_postgres():
        import psycopg
        from psycopg.rows import dict_row
        with psycopg.connect(os.environ['DATABASE_URL'],row_factory=dict_row,connect_timeout=10) as conn:
            yield PgConnection(conn)
    else:
        p=db_path();p.parent.mkdir(parents=True,exist_ok=True)
        conn=sqlite3.connect(str(p),timeout=15)
        conn.row_factory=sqlite3.Row
        conn.execute('PRAGMA foreign_keys=ON')
        conn.execute('PRAGMA busy_timeout=15000')
        try:
            yield conn;conn.commit()
        except Exception:
            conn.rollback();raise
        finally:conn.close()
SCHEMA="""
CREATE TABLE IF NOT EXISTS users (
 id TEXT PRIMARY KEY, username TEXT UNIQUE NOT NULL,
 passhash TEXT NOT NULL,salt TEXT NOT NULL,role TEXT NOT NULL DEFAULT 'analyst',
 active INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS auth_failed_attempts (
 id TEXT PRIMARY KEY,
 account_digest TEXT NOT NULL,
 peer_digest TEXT NOT NULL,
 observed_at BIGINT NOT NULL
);
CREATE INDEX IF NOT EXISTS auth_failed_attempts_account ON auth_failed_attempts(account_digest,observed_at);
CREATE INDEX IF NOT EXISTS auth_failed_attempts_peer ON auth_failed_attempts(peer_digest,observed_at);
CREATE TABLE IF NOT EXISTS user_security_state (
 user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
 must_change_password INTEGER NOT NULL DEFAULT 0,
 password_changed_at TEXT,
 changed_by TEXT
);
CREATE TABLE IF NOT EXISTS sessions (
 token_hash TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id),expires_at BIGINT NOT NULL
);
CREATE TABLE IF NOT EXISTS cases (
 id TEXT PRIMARY KEY,title TEXT NOT NULL,subject_type TEXT NOT NULL,
 query TEXT NOT NULL,purpose TEXT NOT NULL,authority_confirmed INTEGER NOT NULL,
 ai_opt_in INTEGER NOT NULL DEFAULT 0,created_by TEXT NOT NULL REFERENCES users(id),
 created_at TEXT NOT NULL,last_collected TEXT
);
CREATE TABLE IF NOT EXISTS evidence (
 id TEXT PRIMARY KEY,case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
 provider TEXT NOT NULL,label TEXT NOT NULL,summary TEXT NOT NULL,source_url TEXT NOT NULL,
 source_ref TEXT NOT NULL DEFAULT '',fetched_at TEXT NOT NULL,observed_at TEXT,
 sha256 TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'candidate',
 reviewer_notes TEXT NOT NULL DEFAULT '',reviewed_by TEXT,reviewed_at TEXT,raw_json TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS uniq_evidence ON evidence(case_id,provider,source_ref);
CREATE INDEX IF NOT EXISTS evidence_case_idx ON evidence(case_id);
CREATE TABLE IF NOT EXISTS collection_runs (
 id TEXT PRIMARY KEY,case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
 provider TEXT NOT NULL,state TEXT NOT NULL,result_count INTEGER NOT NULL,
 message TEXT NOT NULL,ran_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit_events (
 id TEXT PRIMARY KEY,actor TEXT NOT NULL,action TEXT NOT NULL,
 object_type TEXT NOT NULL,object_id TEXT NOT NULL,details TEXT NOT NULL,created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS case_context (
 case_id TEXT PRIMARY KEY REFERENCES cases(id) ON DELETE CASCADE,
 city TEXT NOT NULL DEFAULT '',organization TEXT NOT NULL DEFAULT '',
 profession TEXT NOT NULL DEFAULT '',public_handle TEXT NOT NULL DEFAULT '',
 updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS research_sessions (
 id TEXT PRIMARY KEY,case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
 owner_id TEXT NOT NULL REFERENCES users(id),title TEXT NOT NULL,
 created_at TEXT NOT NULL,updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS research_sessions_case ON research_sessions(case_id,created_at);
CREATE TABLE IF NOT EXISTS research_messages (
 id TEXT PRIMARY KEY,session_id TEXT NOT NULL REFERENCES research_sessions(id) ON DELETE CASCADE,
 role TEXT NOT NULL,content TEXT NOT NULL,provider TEXT NOT NULL DEFAULT '',
 evidence_ids_json TEXT NOT NULL DEFAULT '[]',web_leads_json TEXT NOT NULL DEFAULT '[]',
 created_at TEXT NOT NULL, message_index INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS research_messages_session ON research_messages(session_id,created_at);
CREATE TABLE IF NOT EXISTS research_response_snapshots(
 id TEXT PRIMARY KEY,case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
 session_id TEXT NOT NULL REFERENCES research_sessions(id) ON DELETE CASCADE,
 assistant_message_id TEXT NOT NULL UNIQUE REFERENCES research_messages(id) ON DELETE CASCADE,
 snapshot_json TEXT NOT NULL,content_sha256 TEXT NOT NULL,created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS response_snapshots_case
 ON research_response_snapshots(case_id,created_at);
CREATE TABLE IF NOT EXISTS search_history (
 id TEXT PRIMARY KEY,case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
 user_id TEXT NOT NULL REFERENCES users(id),search_query TEXT NOT NULL,
 subject_type TEXT NOT NULL,providers_json TEXT NOT NULL,results_count INTEGER NOT NULL,
 errors_count INTEGER NOT NULL,created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS search_history_case ON search_history(case_id,created_at);
CREATE TABLE IF NOT EXISTS claim_links (
 id TEXT PRIMARY KEY,case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
 evidence_id TEXT NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
 claim_text TEXT NOT NULL,stance TEXT NOT NULL DEFAULT 'supports',
 created_by TEXT NOT NULL REFERENCES users(id),created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS claim_links_case ON claim_links(case_id);
CREATE TABLE IF NOT EXISTS research_queries(
 id TEXT PRIMARY KEY,case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
 actor_id TEXT NOT NULL REFERENCES users(id),run_id TEXT NOT NULL,
 provider TEXT NOT NULL,query_text TEXT NOT NULL,status TEXT NOT NULL,
 returned_count INTEGER NOT NULL DEFAULT 0,new_count INTEGER NOT NULL DEFAULT 0,
 message TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS research_queries_case ON research_queries(case_id,created_at);
CREATE TABLE IF NOT EXISTS identity_pair_reviews(
 id TEXT PRIMARY KEY,
 case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
 left_evidence_id TEXT NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
 right_evidence_id TEXT NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
 decision TEXT NOT NULL,
 rationale TEXT NOT NULL,
 reviewer_id TEXT NOT NULL REFERENCES users(id),
 reviewed_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS identity_pair_reviews_case ON identity_pair_reviews(case_id,reviewed_at);
CREATE INDEX IF NOT EXISTS identity_pair_reviews_pair ON identity_pair_reviews(case_id,left_evidence_id,right_evidence_id,reviewed_at);

CREATE TABLE IF NOT EXISTS candidate_profiles(
 id TEXT PRIMARY KEY,case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
 display_name TEXT NOT NULL,reason TEXT NOT NULL DEFAULT '',
 classification TEXT NOT NULL DEFAULT 'unresolved',created_by TEXT NOT NULL REFERENCES users(id),
 created_at TEXT NOT NULL,updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS candidate_profiles_case ON candidate_profiles(case_id,updated_at);
CREATE TABLE IF NOT EXISTS candidate_public_identifiers (
 id TEXT PRIMARY KEY,
 case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
 profile_id TEXT NOT NULL REFERENCES candidate_profiles(id) ON DELETE CASCADE,
 evidence_id TEXT NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
 kind TEXT NOT NULL,
 canonical_value TEXT NOT NULL,
 asserted_url TEXT NOT NULL,
 review_state TEXT NOT NULL DEFAULT 'unverified_identifier',
 created_by TEXT NOT NULL REFERENCES users(id),
 created_at TEXT NOT NULL,
 UNIQUE(case_id,profile_id,evidence_id,kind,canonical_value)
);
CREATE INDEX IF NOT EXISTS candidate_public_identifiers_case ON candidate_public_identifiers(case_id,profile_id,kind);
CREATE TABLE IF NOT EXISTS candidate_evidence(
 profile_id TEXT NOT NULL REFERENCES candidate_profiles(id) ON DELETE CASCADE,
 evidence_id TEXT NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
 rationale TEXT NOT NULL DEFAULT '',
 PRIMARY KEY(profile_id,evidence_id)
);

CREATE TABLE IF NOT EXISTS case_members(
 case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
 user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 granted_by TEXT NOT NULL REFERENCES users(id),
 granted_at TEXT NOT NULL,
 PRIMARY KEY(case_id,user_id)
);
CREATE INDEX IF NOT EXISTS case_members_user ON case_members(user_id,case_id);

CREATE TABLE IF NOT EXISTS investigation_tasks(
 id TEXT PRIMARY KEY,
 case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
 title TEXT NOT NULL,
 description TEXT NOT NULL DEFAULT '',
 status TEXT NOT NULL DEFAULT 'todo',
 priority TEXT NOT NULL DEFAULT 'normal',
 assigned_to TEXT REFERENCES users(id),
 due_date TEXT NOT NULL DEFAULT '',
 created_by TEXT NOT NULL REFERENCES users(id),
 created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS investigation_tasks_case ON investigation_tasks(case_id,status,due_date);
CREATE TABLE IF NOT EXISTS investigation_task_events(
 id TEXT PRIMARY KEY,
 task_id TEXT NOT NULL REFERENCES investigation_tasks(id) ON DELETE CASCADE,
 case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
 actor_id TEXT NOT NULL REFERENCES users(id),
 old_status TEXT NOT NULL,
 new_status TEXT NOT NULL,
 details TEXT NOT NULL,
 created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS investigation_task_events_task ON investigation_task_events(task_id,created_at);

CREATE TABLE IF NOT EXISTS source_observations(
 id TEXT PRIMARY KEY,
 case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
 evidence_id TEXT NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
 run_id TEXT NOT NULL,
 query_text TEXT NOT NULL,
 provider TEXT NOT NULL,
 source_ref TEXT NOT NULL,
 content_sha256 TEXT NOT NULL,
 label TEXT NOT NULL,
 summary TEXT NOT NULL,
 source_url TEXT NOT NULL,
 raw_json TEXT NOT NULL,
 disposition TEXT NOT NULL,
 captured_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS source_observations_case ON source_observations(case_id,captured_at);
CREATE INDEX IF NOT EXISTS source_observations_evidence ON source_observations(evidence_id,captured_at);

CREATE TABLE IF NOT EXISTS source_captures(
 id TEXT PRIMARY KEY,case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
 evidence_id TEXT NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
 source_url TEXT NOT NULL,content_type TEXT NOT NULL,
 extracted_text TEXT NOT NULL,content_sha256 TEXT NOT NULL,
 fetched_at TEXT NOT NULL,fetch_status TEXT NOT NULL,
 error_message TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS source_captures_evidence ON source_captures(evidence_id,fetched_at);
CREATE TABLE IF NOT EXISTS review_decisions(
 id TEXT PRIMARY KEY,case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
 evidence_id TEXT REFERENCES evidence(id) ON DELETE CASCADE,
 actor_id TEXT NOT NULL REFERENCES users(id),
 old_status TEXT NOT NULL,new_status TEXT NOT NULL,
 rationale TEXT NOT NULL,created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS review_decisions_case ON review_decisions(case_id,created_at);


CREATE TABLE IF NOT EXISTS research_jobs(
 id TEXT PRIMARY KEY,
 case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
 owner_id TEXT NOT NULL REFERENCES users(id),
 objective TEXT NOT NULL,
 mode TEXT NOT NULL,
 allow_web INTEGER NOT NULL DEFAULT 0,
 status TEXT NOT NULL DEFAULT 'ready',
 max_steps INTEGER NOT NULL,
 completed_steps INTEGER NOT NULL DEFAULT 0,
 last_error TEXT NOT NULL DEFAULT '',
 created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS research_jobs_case ON research_jobs(case_id,created_at);
CREATE TABLE IF NOT EXISTS research_job_steps(
 id TEXT PRIMARY KEY,
 job_id TEXT NOT NULL REFERENCES research_jobs(id) ON DELETE CASCADE,
 case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
 step_number INTEGER NOT NULL,
 provider TEXT NOT NULL,
 query_text TEXT NOT NULL,
 rationale TEXT NOT NULL,
 status TEXT NOT NULL,
 returned_count INTEGER NOT NULL DEFAULT 0,
 new_count INTEGER NOT NULL DEFAULT 0,
 changed_count INTEGER NOT NULL DEFAULT 0,
 error_message TEXT NOT NULL DEFAULT '',
 started_at TEXT NOT NULL,
 finished_at TEXT NOT NULL DEFAULT '',
 UNIQUE(job_id,step_number)
);
CREATE INDEX IF NOT EXISTS research_job_steps_job ON research_job_steps(job_id,step_number);
CREATE TABLE IF NOT EXISTS verified_excerpts(
 id TEXT PRIMARY KEY,
 case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
 evidence_id TEXT NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
 capture_id TEXT NOT NULL REFERENCES source_captures(id) ON DELETE CASCADE,
 quote_text TEXT NOT NULL,
 interpretation TEXT NOT NULL,
 content_sha256 TEXT NOT NULL,
 review_status TEXT NOT NULL DEFAULT 'excerpt_matched',
 created_by TEXT NOT NULL REFERENCES users(id),
 created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS verified_excerpts_case ON verified_excerpts(case_id,created_at);

CREATE TABLE IF NOT EXISTS claim_passage_proofs (
 id TEXT PRIMARY KEY,
 case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
 claim_id TEXT NOT NULL REFERENCES claim_links(id) ON DELETE CASCADE,
 excerpt_id TEXT NOT NULL REFERENCES verified_excerpts(id) ON DELETE CASCADE,
 evidence_id TEXT NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
 link_status TEXT NOT NULL DEFAULT 'text_match_only',
 reviewed_by TEXT NOT NULL REFERENCES users(id),
 created_at TEXT NOT NULL,
 UNIQUE(case_id,claim_id,excerpt_id)
);
CREATE INDEX IF NOT EXISTS claim_passage_proofs_case ON claim_passage_proofs(case_id,created_at);
CREATE TABLE IF NOT EXISTS case_search_plans (
 case_id TEXT PRIMARY KEY REFERENCES cases(id) ON DELETE CASCADE,
 original_question TEXT NOT NULL, plan_json TEXT NOT NULL,
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS research_grounding (
 id TEXT PRIMARY KEY,
 case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
 session_id TEXT REFERENCES research_sessions(id) ON DELETE CASCADE,
 provider TEXT NOT NULL, query_text TEXT NOT NULL,
 source_url TEXT NOT NULL, source_title TEXT NOT NULL,
 published_at TEXT NOT NULL DEFAULT '',
 excerpt_sha256 TEXT NOT NULL, retrieved_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS research_grounding_case
 ON research_grounding(case_id,retrieved_at);
CREATE TABLE IF NOT EXISTS research_excerpt_samples(
 id TEXT PRIMARY KEY,
 grounding_id TEXT NOT NULL REFERENCES research_grounding(id) ON DELETE CASCADE,
 case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
 source_url TEXT NOT NULL,
 excerpt_text TEXT NOT NULL,
 excerpt_sha256 TEXT NOT NULL,
 retention_basis TEXT NOT NULL,
 review_state TEXT NOT NULL DEFAULT 'unverified_search_excerpt',
 created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS research_excerpt_samples_case ON research_excerpt_samples(case_id,created_at);

CREATE TABLE IF NOT EXISTS case_assessments(
 case_id TEXT PRIMARY KEY REFERENCES cases(id) ON DELETE CASCADE,
 executive_summary TEXT NOT NULL DEFAULT '',assessment TEXT NOT NULL DEFAULT '',
 limitations TEXT NOT NULL DEFAULT '',next_actions TEXT NOT NULL DEFAULT '',
 status TEXT NOT NULL DEFAULT 'open',updated_by TEXT REFERENCES users(id),
 updated_at TEXT NOT NULL
);


CREATE TABLE IF NOT EXISTS assessment_review_baselines (
 case_id TEXT PRIMARY KEY REFERENCES cases(id) ON DELETE CASCADE,
 evidence_digest TEXT NOT NULL,
 saved_at TEXT NOT NULL,
 saved_by TEXT NOT NULL REFERENCES users(id)
);
CREATE TABLE IF NOT EXISTS research_aliases (
 id TEXT PRIMARY KEY, case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
 alias TEXT NOT NULL, alias_type TEXT NOT NULL, source_url TEXT NOT NULL DEFAULT '',
 rationale TEXT NOT NULL DEFAULT '', created_by TEXT NOT NULL REFERENCES users(id),
 created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS research_alias_case ON research_aliases(case_id,created_at);
CREATE TABLE IF NOT EXISTS agency_recipes (
 id TEXT PRIMARY KEY,owner_id TEXT NOT NULL REFERENCES users(id),
 title TEXT NOT NULL,description TEXT NOT NULL DEFAULT '',question TEXT NOT NULL,
 version INTEGER NOT NULL DEFAULT 1,created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS agency_recipes_owner ON agency_recipes(owner_id,updated_at);
CREATE TABLE IF NOT EXISTS sourced_relationships (
 id TEXT PRIMARY KEY,case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
 left_name TEXT NOT NULL,right_name TEXT NOT NULL,relationship TEXT NOT NULL,
 evidence_id TEXT NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
 rationale TEXT NOT NULL,review_state TEXT NOT NULL DEFAULT 'proposed',
 created_by TEXT NOT NULL REFERENCES users(id),created_at TEXT NOT NULL,
 reviewed_by TEXT,reviewed_at TEXT);
CREATE INDEX IF NOT EXISTS sourced_relationship_case ON sourced_relationships(case_id,created_at);
CREATE TABLE IF NOT EXISTS case_signoffs (
 id TEXT PRIMARY KEY, case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
 actor_id TEXT NOT NULL REFERENCES users(id), decision TEXT NOT NULL,
 note TEXT NOT NULL, signed_at TEXT NOT NULL,
 review_digest TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS case_signoffs_case ON case_signoffs(case_id,signed_at);
CREATE TABLE IF NOT EXISTS case_research_approvals (
 id TEXT PRIMARY KEY,
 case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
 approved_by TEXT NOT NULL REFERENCES users(id),
 purpose_snapshot TEXT NOT NULL,
 specific_scope TEXT NOT NULL,
 authorization_category TEXT NOT NULL,
 approval_reference TEXT NOT NULL,
 retention_days INTEGER NOT NULL,
 approved_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS case_research_approvals_case
 ON case_research_approvals(case_id,approved_at);
CREATE TABLE IF NOT EXISTS evidence_source_reviews (
 id TEXT PRIMARY KEY,case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
 evidence_id TEXT NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
 source_kind TEXT NOT NULL,assertion_owner TEXT NOT NULL,
 publisher_authentication TEXT NOT NULL,
 relation_to_subject TEXT NOT NULL,
 rationale TEXT NOT NULL,
 reviewed_by TEXT NOT NULL REFERENCES users(id),reviewed_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS evidence_source_reviews_case ON evidence_source_reviews(case_id,evidence_id,reviewed_at);
CREATE TABLE IF NOT EXISTS claim_conflict_reviews (
 id TEXT PRIMARY KEY,case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
 left_claim_id TEXT NOT NULL REFERENCES claim_links(id) ON DELETE CASCADE,
 right_claim_id TEXT NOT NULL REFERENCES claim_links(id) ON DELETE CASCADE,
 classification TEXT NOT NULL,
 right_of_reply TEXT NOT NULL,
 review_note TEXT NOT NULL,
 reviewer_id TEXT NOT NULL REFERENCES users(id),reviewed_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS claim_conflict_reviews_case ON claim_conflict_reviews(case_id,reviewed_at);
CREATE TABLE IF NOT EXISTS source_document_archives (
 id TEXT PRIMARY KEY,case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
 evidence_id TEXT NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
 capture_id TEXT REFERENCES source_captures(id) ON DELETE SET NULL,
 original_url TEXT NOT NULL,asset_kind TEXT NOT NULL,
 original_sha256 TEXT NOT NULL,byte_count INTEGER NOT NULL,
 content_b64 TEXT NOT NULL,extracted_text_sha256 TEXT NOT NULL DEFAULT '',
 stored_at TEXT NOT NULL,expires_at TEXT NOT NULL,
 uploaded_by TEXT NOT NULL REFERENCES users(id)
);
CREATE INDEX IF NOT EXISTS source_document_archives_case
 ON source_document_archives(case_id,evidence_id,stored_at);
CREATE TABLE IF NOT EXISTS source_link_checks (
 id TEXT PRIMARY KEY,case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
 evidence_id TEXT NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
 original_url TEXT NOT NULL,request_method TEXT NOT NULL,
 http_status INTEGER,check_state TEXT NOT NULL,
 response_class TEXT NOT NULL,
 checked_at TEXT NOT NULL,checked_by TEXT NOT NULL REFERENCES users(id)
);
CREATE INDEX IF NOT EXISTS source_link_checks_case ON source_link_checks(case_id,evidence_id,checked_at);
CREATE TABLE IF NOT EXISTS time_qualified_affiliations (
 id TEXT PRIMARY KEY,case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
 candidate_id TEXT NOT NULL REFERENCES candidate_profiles(id) ON DELETE CASCADE,
 evidence_id TEXT NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
 excerpt_id TEXT NOT NULL REFERENCES verified_excerpts(id) ON DELETE CASCADE,
 organization_name TEXT NOT NULL,role_title TEXT NOT NULL,
 start_date TEXT NOT NULL,end_date TEXT NOT NULL DEFAULT '',
 date_precision TEXT NOT NULL,rationale TEXT NOT NULL,
 created_by TEXT NOT NULL REFERENCES users(id),created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS affiliations_case ON time_qualified_affiliations(case_id,candidate_id,created_at);
CREATE TABLE IF NOT EXISTS candidate_refinements (
 id TEXT PRIMARY KEY,case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
 candidate_id TEXT NOT NULL REFERENCES candidate_profiles(id) ON DELETE CASCADE,
 original_question TEXT NOT NULL,clue_kind TEXT NOT NULL,
 clue_value TEXT NOT NULL,search_query TEXT NOT NULL,
 reviewed_by TEXT NOT NULL REFERENCES users(id),reviewed_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS candidate_refinements_case ON candidate_refinements(case_id,candidate_id,reviewed_at);
CREATE TABLE IF NOT EXISTS external_api_call_ledger (
 id TEXT PRIMARY KEY,case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
 provider TEXT NOT NULL,reserved_at TEXT NOT NULL,
 by_user TEXT NOT NULL REFERENCES users(id)
);
CREATE INDEX IF NOT EXISTS external_api_usage_case ON external_api_call_ledger(case_id,provider,reserved_at);
CREATE TABLE IF NOT EXISTS external_api_daily_counters (
 case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
 provider TEXT NOT NULL,day TEXT NOT NULL,used INTEGER NOT NULL DEFAULT 0,
 PRIMARY KEY(case_id,provider,day)
);
CREATE TABLE IF NOT EXISTS provider_health_events (
 id TEXT PRIMARY KEY,provider TEXT NOT NULL,outcome TEXT NOT NULL,
 status_code INTEGER,latency_ms INTEGER NOT NULL,observed_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS provider_health_index ON provider_health_events(provider,observed_at);
CREATE TABLE IF NOT EXISTS source_feedback (
 id TEXT PRIMARY KEY,case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
 evidence_id TEXT NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
 actor_id TEXT NOT NULL REFERENCES users(id), relevance TEXT NOT NULL,
 rationale TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS source_feedback_case ON source_feedback(case_id,created_at);
CREATE TABLE IF NOT EXISTS translation_notes (
 id TEXT PRIMARY KEY,case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
 evidence_id TEXT NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
 language TEXT NOT NULL,source_quote TEXT NOT NULL,translation TEXT NOT NULL,
 translator TEXT NOT NULL,created_by TEXT NOT NULL REFERENCES users(id),
 created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS translation_notes_case ON translation_notes(case_id,created_at);

"""
def hash_password(password):
    salt=secrets.token_hex(16)
    digest=hashlib.scrypt(password.encode(),salt=bytes.fromhex(salt),n=16384,r=8,p=1).hex()
    return salt,digest
def init_db():
    with connect() as c:
        if not is_postgres():c.execute('PRAGMA journal_mode=WAL')
        c.executescript(SCHEMA)
        if is_postgres():
            c.execute('ALTER TABLE users ADD COLUMN IF NOT EXISTS active INTEGER NOT NULL DEFAULT 1')
            c.execute('ALTER TABLE research_messages ADD COLUMN IF NOT EXISTS message_index INTEGER NOT NULL DEFAULT 0')
        else:
            columns={r['name'] for r in c.execute('PRAGMA table_info(users)')}
            if 'active' not in columns:c.execute('ALTER TABLE users ADD COLUMN active INTEGER NOT NULL DEFAULT 1')
            msg_columns={r['name'] for r in c.execute('PRAGMA table_info(research_messages)')}
            if 'message_index' not in msg_columns:c.execute('ALTER TABLE research_messages ADD COLUMN message_index INTEGER NOT NULL DEFAULT 0')
        password=os.getenv('OSINTALPHA_ADMIN_PASSWORD','')
        if len(password)<12:raise RuntimeError('Set OSINTALPHA_ADMIN_PASSWORD to >=12 characters')
        if not c.execute('SELECT id FROM users WHERE username=?',('admin',)).fetchone():
            salt,digest=hash_password(password)
            c.execute('INSERT INTO users(id,username,passhash,salt,role,active) VALUES (?,?,?,?,?,?)',
              (secrets.token_hex(16),'admin',digest,salt,'admin',1))
def verify_password(password,row):
    return secrets.compare_digest(hashlib.scrypt(password.encode(),salt=bytes.fromhex(row['salt']),n=16384,r=8,p=1),bytes.fromhex(row['passhash']))
def audit(actor,action,object_type,object_id,details=''):
    with connect() as c:
        c.execute('INSERT INTO audit_events VALUES (?,?,?,?,?,?,?)',
                  (secrets.token_hex(12),actor,action,object_type,object_id,details[:500],utcnow()))
