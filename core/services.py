import re, uuid, datetime as dt
import pandas as pd
from core import db
from config import *
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
def progress(raised, target): return round(100 * raised / target, 1) if target and target > 0 else 0.0
def safe_csv(df):  # blocks spreadsheet formula injection
    d = df.copy()
    for c in d.select_dtypes(include="object"):
        d[c] = d[c].map(lambda v: "'" + v if isinstance(v, str) and v[:1] in "=+-@\t\r" else v)
    return d.to_csv(index=False).encode()
def register(name, email, pw):
    email = email.strip().lower()
    if not name.strip() or not EMAIL.match(email): return "Enter a name and a valid email."
    if len(pw) < 8: return "Password must be at least 8 characters."
    if db.one("SELECT 1 FROM users WHERE email=?", (email,)): return "Could not register with those details."
    db.x("INSERT INTO users(name,email,pw_hash,role,created_at) VALUES(?,?,?,'donor',?)", (name.strip(), email, db.hash_pw(pw), db.now()))
    return None
def login(email, pw):
    u = db.one("SELECT * FROM users WHERE email=?", (email.strip().lower(),))
    if u and db.check_pw(pw, u["pw_hash"]): return {k: u[k] for k in ("id", "name", "email", "role")}
def require_admin(u):
    if not u or u.get("role") != "admin": raise PermissionError("Administrator access required.")
def campaign_stats():
    return db.df("""SELECT c.*, COALESCE(SUM(CASE WHEN d.status='successful' THEN d.amount END),0) raised,
      COUNT(CASE WHEN d.status='successful' THEN 1 END) n_don FROM campaigns c
      LEFT JOIN donations d ON d.campaign_id=c.id AND d.source='live' GROUP BY c.id ORDER BY c.id DESC""")
def accepting(c):
    return c["status"] == "active" and c["start_date"] <= str(dt.date.today()) <= c["end_date"]
def save_campaign(u, f, cid=None):
    require_admin(u)
    if not f["title"].strip() or f["target"] <= 0 or f["end"] < f["start"]: return "Title, positive target and valid dates are required."
    try:
        if cid: db.x("UPDATE campaigns SET title=?,description=?,category=?,target=?,start_date=?,end_date=? WHERE id=?",
                     (f["title"].strip(), f["desc"], f["cat"], f["target"], str(f["start"]), str(f["end"]), cid))
        else: db.x("INSERT INTO campaigns(title,description,category,target,start_date,end_date,created_at,created_by) VALUES(?,?,?,?,?,?,?,?)",
                   (f["title"].strip(), f["desc"], f["cat"], f["target"], str(f["start"]), str(f["end"]), db.now(), u["id"]))
    except Exception: return "Campaign title must be unique."
    db.audit(u["id"], "campaign_save", f["title"]); return None
def set_campaign_status(u, cid, status):
    require_admin(u); cur = db.one("SELECT status FROM campaigns WHERE id=?", (cid,))
    if not cur or cur["status"] != "active" or status not in ("completed", "closed"): return "Only active campaigns can be completed or closed."
    db.x("UPDATE campaigns SET status=? WHERE id=?", (status, cid)); db.audit(u["id"], "campaign_status", f"{cid}->{status}")
def create_donation(u, cid, amount, msg, anon, method):
    c = db.one("SELECT * FROM campaigns WHERE id=?", (cid,))
    if not u or not c or not accepting(c): return None, "This campaign is not accepting donations."
    if not (1 <= amount <= 1_000_000): return None, "Amount must be between 1 and 1,000,000."
    ref = "DON-" + uuid.uuid4().hex[:12].upper()
    db.x("INSERT INTO donations(ref,user_id,campaign_id,amount,status,method,message,anonymous,source,created_at) VALUES(?,?,?,?,'pending',?,?,?,'live',?)",
         (ref, u["id"], cid, amount, method, msg[:300], int(anon), db.now()))
    db.audit(u["id"], "donation_created", ref); return ref, None
ALLOWED = {"pending": {"successful", "failed"}, "successful": {"refunded"}}
def transition(u, ref, new, admin_only=False):
    d = db.one("SELECT * FROM donations WHERE ref=? AND source='live'", (ref,))
    if not d or not u or (d["user_id"] != u["id"] and u["role"] != "admin"): return "Donation not found."
    if new == "refunded": require_admin(u)
    if new not in ALLOWED.get(d["status"], set()): return f"Invalid transition {d['status']} -> {new}."
    db.x("UPDATE donations SET status=? WHERE ref=? AND status=?", (new, ref, d["status"]))  # guarded: counted once
    db.audit(u["id"], "donation_status", f"{ref}: {d['status']}->{new} (DEMO simulator)")
def add_expense(u, cid, desc, cat, amt, date, doc, exc):
    require_admin(u)
    if amt <= 0 or not desc.strip(): return "Description and a positive amount are required."
    raised = db.one("SELECT COALESCE(SUM(amount),0) r FROM donations WHERE campaign_id=? AND status='successful' AND source='live'", (cid,))["r"]
    spent = db.one("SELECT COALESCE(SUM(amount),0) s FROM fund_utilization WHERE campaign_id=?", (cid,))["s"]
    if spent + amt > raised and not exc.strip(): return f"Exceeds available funds ({raised-spent:,.2f}). Enter an exception note to override (audited)."
    db.x("INSERT INTO fund_utilization(campaign_id,description,category,amount,expense_date,doc_ref,exception_note,created_by,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
         (cid, desc, cat, amt, str(date), doc, exc or None, u["id"], db.now())); db.audit(u["id"], "expense_added", f"c{cid} {amt}")
# ---------- import ----------
ALIAS = {"transaction_id": "external_transaction_id", "donor": "donor_reference", "campaign": "campaign_reference", "date": "donation_date",
         "status": "payment_status", "method": "payment_method"}
REQ = ["external_transaction_id", "donor_reference", "campaign_reference", "amount", "donation_date", "category", "payment_status"]
def clean(raw):
    d = raw.copy(); d.columns = [ALIAS.get(c.strip().lower().replace(" ", "_"), c.strip().lower().replace(" ", "_")) for c in d.columns]
    miss = [c for c in REQ if c not in d.columns]
    if miss: raise ValueError(f"Missing required columns: {miss}")
    if "payment_method" not in d: d["payment_method"] = "unknown"
    d["amount"] = pd.to_numeric(d["amount"], errors="coerce")
    d["donation_date"] = pd.to_datetime(d["donation_date"], errors="coerce")
    cm = {c.lower(): c for c in CATEGORIES}; d["category"] = d["category"].astype(str).str.strip().str.lower().map(cm).fillna("Other")
    d["payment_status"] = d["payment_status"].astype(str).str.strip().str.lower().replace({"success": "successful", "paid": "successful", "fail": "failed", "refund": "refunded"})
    d["external_transaction_id"] = d["external_transaction_id"].astype(str).str.strip().replace({"nan": None, "": None})
    why = pd.Series("", index=d.index)
    why[d["amount"].isna() | (d["amount"] <= 0)] += "bad amount; "
    why[d["donation_date"].isna()] += "bad date; "
    why[~d["payment_status"].isin(STATUSES)] += "bad status; "
    why[d[["donor_reference", "campaign_reference"]].isna().any(axis=1)] += "missing reference; "
    d["dup_in_file"] = d["external_transaction_id"].notna() & d.duplicated("external_transaction_id")
    d["problem"] = why
    d["maybe_duplicate"] = d.duplicated(["donor_reference", "amount", "donation_date"], keep=False) & d["external_transaction_id"].isna()
    return d
def commit_import(u, d, filename, source):
    require_admin(u); ok = d[(d.problem == "") & ~d.dup_in_file]; n = 0; dup_db = 0
    job = db.x("INSERT INTO data_import_jobs(filename,source,total_rows,valid_rows,invalid_rows,duplicate_rows,created_by,created_at) VALUES(?,?,?,?,?,?,?,?)",
               (filename, source, len(d), len(ok), int((d.problem != "").sum()), int(d.dup_in_file.sum()), u["id"], db.now()))
    cids = {}
    for r in ok.itertuples():
        k = str(r.campaign_reference).strip().lower()
        if k not in cids:
            row = db.one("SELECT id FROM campaigns WHERE title=?", (str(r.campaign_reference).strip(),))
            cids[k] = row["id"] if row else db.x("INSERT INTO campaigns(title,description,category,target,start_date,end_date,status,created_at,created_by) VALUES(?,?,?,?,?,?,'closed',?,?)",
                (str(r.campaign_reference).strip(), f"[{source}] auto-created by import", r.category, 100000, "2000-01-01", "2000-01-02", db.now(), u["id"]))
        try:
            db.x("INSERT INTO donations(ref,donor_ref,campaign_id,amount,status,method,source,external_id,import_job_id,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
                 ("IMP-" + uuid.uuid4().hex[:12].upper(), str(r.donor_reference), cids[k], float(r.amount), r.payment_status, r.payment_method, source,
                  r.external_transaction_id, job, r.donation_date.isoformat())); n += 1
        except Exception: dup_db += 1  # already imported (unique source+external_id)
    db.x("UPDATE data_import_jobs SET imported_rows=?, duplicate_rows=duplicate_rows+? WHERE id=?", (n, dup_db, job))
    db.audit(u["id"], "import", f"{filename}: {n} rows as {source}"); return n, dup_db
def synthetic(n=10000, seed=42):
    import numpy as np
    r = np.random.default_rng(seed); camps = [f"Synthetic Campaign {i+1}" for i in range(8)]
    cats = [CATEGORIES[i % len(CATEGORIES)] for i in range(8)]; donors = r.integers(1, max(n // 4, 10), n)
    dates = pd.Timestamp("2025-01-01") + pd.to_timedelta(r.integers(0, 400, n), unit="D")
    ci = r.integers(0, 8, n)
    return pd.DataFrame({"external_transaction_id": [f"SYN-{seed}-{i}" for i in range(n)], "donor_reference": [f"SD{x:05d}" for x in donors],
        "campaign_reference": [camps[i] for i in ci], "amount": np.round(r.lognormal(5, 1, n).clip(10, 100000), 2),
        "donation_date": dates.strftime("%Y-%m-%d"), "category": [cats[i] for i in ci],
        "payment_status": r.choice(["successful", "pending", "failed", "refunded"], n, p=[.82, .05, .1, .03]),
        "payment_method": r.choice(["upi", "card", "netbanking"], n)})
