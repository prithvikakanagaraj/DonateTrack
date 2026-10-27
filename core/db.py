import sqlite3, os, hashlib, hmac, secrets, datetime as dt
import pandas as pd
DB = os.environ.get("DB_PATH", "donate.db")
SCHEMA = """
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL UNIQUE,
 pw_hash TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN('donor','admin')), created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS campaigns(id INTEGER PRIMARY KEY, title TEXT NOT NULL UNIQUE COLLATE NOCASE, description TEXT,
 category TEXT NOT NULL, image TEXT, target REAL NOT NULL CHECK(target>=0), start_date TEXT NOT NULL, end_date TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'active' CHECK(status IN('active','completed','closed')), created_at TEXT NOT NULL,
 created_by INTEGER REFERENCES users(id));
CREATE TABLE IF NOT EXISTS data_import_jobs(id INTEGER PRIMARY KEY, filename TEXT, source TEXT, total_rows INT, valid_rows INT,
 invalid_rows INT, duplicate_rows INT, imported_rows INT, created_by INTEGER REFERENCES users(id), created_at TEXT);
CREATE TABLE IF NOT EXISTS donations(id INTEGER PRIMARY KEY, ref TEXT NOT NULL UNIQUE, user_id INTEGER REFERENCES users(id),
 donor_ref TEXT, campaign_id INTEGER NOT NULL REFERENCES campaigns(id), amount REAL NOT NULL CHECK(amount>0),
 status TEXT NOT NULL CHECK(status IN('pending','successful','failed','refunded')), method TEXT, message TEXT,
 anonymous INTEGER NOT NULL DEFAULT 0, source TEXT NOT NULL DEFAULT 'live' CHECK(source IN('live','imported','synthetic')),
 external_id TEXT, import_job_id INTEGER REFERENCES data_import_jobs(id), created_at TEXT NOT NULL);
CREATE UNIQUE INDEX IF NOT EXISTS ux_ext ON donations(source, external_id) WHERE external_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS ix_don_c ON donations(campaign_id, status);
CREATE INDEX IF NOT EXISTS ix_don_u ON donations(user_id);
CREATE TABLE IF NOT EXISTS fund_utilization(id INTEGER PRIMARY KEY, campaign_id INTEGER NOT NULL REFERENCES campaigns(id),
 description TEXT NOT NULL, category TEXT NOT NULL, amount REAL NOT NULL CHECK(amount>0), expense_date TEXT NOT NULL,
 doc_ref TEXT, exception_note TEXT, created_by INTEGER REFERENCES users(id), created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS audit_logs(id INTEGER PRIMARY KEY, actor_id INTEGER, action TEXT NOT NULL, detail TEXT, created_at TEXT NOT NULL);
"""
def now(): return dt.datetime.now().isoformat(timespec="seconds")
def conn():
    c = sqlite3.connect(DB); c.row_factory = sqlite3.Row; c.execute("PRAGMA foreign_keys=ON"); return c
def q(sql, p=()):
    with conn() as c: return [dict(r) for r in c.execute(sql, p).fetchall()]
def one(sql, p=()):
    r = q(sql, p); return r[0] if r else None
def x(sql, p=()):
    c = conn()
    try:
        with c: return c.execute(sql, p).lastrowid
    finally: c.close()
def df(sql, p=()):
    c = conn()
    try: return pd.read_sql_query(sql, c, params=p)
    finally: c.close()
def audit(actor, action, detail=""): x("INSERT INTO audit_logs(actor_id,action,detail,created_at) VALUES(?,?,?,?)", (actor, action, detail, now()))
def hash_pw(pw):
    s = secrets.token_hex(16)
    return s + "$" + hashlib.scrypt(pw.encode(), salt=s.encode(), n=2**14, r=8, p=1).hex()
def check_pw(pw, stored):
    try: s, h = stored.split("$")
    except ValueError: return False
    return hmac.compare_digest(hashlib.scrypt(pw.encode(), salt=s.encode(), n=2**14, r=8, p=1).hex(), h)
def init():
    c = conn(); c.executescript(SCHEMA); c.close()
    em, pw = os.environ.get("ADMIN_EMAIL"), os.environ.get("ADMIN_PASSWORD")  # admin is only created from env/secrets
    if em and pw and not one("SELECT 1 FROM users WHERE email=?", (em.lower(),)):
        x("INSERT INTO users(name,email,pw_hash,role,created_at) VALUES('Administrator',?,?,'admin',?)", (em.lower(), hash_pw(pw), now()))
