import streamlit as st, pandas as pd, plotly.express as px, datetime as dt, os
from core import db, services as S, analytics as A
from config import *
U = lambda: st.session_state.get("user")
def need(role=None):
    u = U()
    if not u: st.warning("Please log in."); st.stop()
    if role and u["role"] != role: st.error("Not authorized."); st.stop()
    return u
def home():
    st.markdown(f"# 💚 {APP_NAME}\n### Give with confidence. See where every rupee goes.")
    st.caption("Donor-facing donation tracking with an analytics pipeline. Payments are DEMO simulations only.")
    cs = S.campaign_stats(); r = db.one("SELECT COALESCE(SUM(amount),0) t, COUNT(*) n FROM donations WHERE status='successful' AND source='live'")
    a = st.columns(4); a[0].metric("Successful donations", f"{r['t']:,.0f}"); a[1].metric("Donors", db.one("SELECT COUNT(*) n FROM users WHERE role='donor'")["n"])
    a[2].metric("Active campaigns", int((cs.status == "active").sum()) if len(cs) else 0); a[3].metric("Completed", int((cs.status == "completed").sum()) if len(cs) else 0)
    st.subheader("Featured campaigns")
    if cs.empty: st.info("No campaigns yet. An administrator can create the first one.")
    for c in cs[cs.status == "active"].head(3).itertuples():
        with st.container(border=True):
            st.markdown(f"**{c.title}** · {c.category}"); st.progress(min(S.progress(c.raised, c.target) / 100, 1.0), text=f"{S.progress(c.raised, c.target)}% of {c.target:,.0f}")
    st.subheader("How it works"); st.markdown("1. Register  2. Pick a campaign  3. Donate (demo)  4. Track history and fund utilization")
    st.caption("Utilization shown is *recorded* by admins, not independently verified.")
def auth():
    t1, t2 = st.tabs(["Log in", "Register"])
    with t1:
        e = st.text_input("Email", key="le"); p = st.text_input("Password", type="password", key="lp")
        if st.button("Log in"):
            u = S.login(e, p)
            if u: st.session_state["user"] = u; st.rerun()
            else: st.error("Invalid email or password.")
    with t2:
        n = st.text_input("Name"); e = st.text_input("Email", key="re"); p = st.text_input("Password (min 8)", type="password", key="rp")
        if st.button("Create donor account"):
            err = S.register(n, e, p); st.error(err) if err else st.success("Registered. Please log in.")
def campaigns():
    cs = S.campaign_stats(); k = st.text_input("Search"); cat = st.selectbox("Category", ["All"] + CATEGORIES); stt = st.selectbox("Status", ["All", "active", "completed", "closed"])
    if k: cs = cs[cs.title.str.contains(k, case=False)]
    if cat != "All": cs = cs[cs.category == cat]
    if stt != "All": cs = cs[cs.status == stt]
    if cs.empty: st.info("No campaigns match."); return
    for c in cs.to_dict("records"):
        with st.container(border=True):
            st.markdown(f"### {c['title']}  `{c['status']}`"); st.write(c["description"] or ""); p = S.progress(c["raised"], c["target"])
            st.progress(min(p / 100, 1.0), text=f"{p}% · raised {c['raised']:,.0f} of {c['target']:,.0f} · remaining {max(c['target']-c['raised'],0):,.0f} · {c['n_don']} donations · ends {c['end_date']}")
            ex = db.one("SELECT COALESCE(SUM(amount),0) s FROM fund_utilization WHERE campaign_id=?", (c["id"],))["s"]
            st.caption(f"Recorded expenditure: {ex:,.0f} ({S.progress(ex, c['raised'])}% of funds raised)")
def donate():
    u = need(); cs = S.campaign_stats(); cs = cs[(cs.status == "active")]
    st.warning("DEMO ONLY: no real money is transferred.")
    if cs.empty: st.info("No campaigns are open."); return
    opt = dict(zip(cs.title, cs.id)); t = st.selectbox("Campaign", list(opt)); amt = st.number_input("Amount", 1.0, 1_000_000.0, 500.0)
    msg = st.text_area("Message (optional)", max_chars=300); an = st.checkbox("Hide my name publicly"); m = st.selectbox("Payment method (demo)", ["UPI", "Card", "Net banking"])
    if st.button("Create donation") :
        ref, err = S.create_donation(u, opt[t], amt, msg, an, m); st.error(err) if err else st.session_state.update(pending=ref)
    ref = st.session_state.get("pending")
    if ref:
        d = db.one("SELECT status FROM donations WHERE ref=? AND user_id=?", (ref, u["id"]))
        if d and d["status"] == "pending":
            st.info(f"Reference **{ref}** is pending. Demo payment simulator:"); a, b = st.columns(2)
            if a.button("Simulate SUCCESS"): S.transition(u, ref, "successful"); st.rerun()
            if b.button("Simulate FAILURE"): S.transition(u, ref, "failed"); st.rerun()
        elif d: st.success(f"{ref}: {d['status']}")
def my_donations():
    u = need(); d = db.df("SELECT d.ref,c.title campaign,d.amount,d.created_at date,d.status,d.method,d.anonymous FROM donations d JOIN campaigns c ON c.id=d.campaign_id WHERE d.user_id=? ORDER BY d.created_at DESC", (u["id"],))
    if d.empty: st.info("You have no donations yet."); return
    c1, c2 = st.columns(2); sf = c1.multiselect("Status", STATUSES); cf = c2.multiselect("Campaign", sorted(d.campaign.unique()))
    if sf: d = d[d.status.isin(sf)]
    if cf: d = d[d.campaign.isin(cf)]
    st.dataframe(d, use_container_width=True); st.download_button("Download CSV", S.safe_csv(d), "my_donations.csv", "text/csv")
    ok = d[d.status == "successful"]
    if len(ok):
        r = st.selectbox("Receipt for", ok.ref); row = ok[ok.ref == r].iloc[0]
        st.code(f"SIMULATED RECEIPT (not a real transaction)\nRef: {r}\nCampaign: {row.campaign}\nAmount: {row.amount:,.2f}\nDate: {row.date}")
def admin_campaigns():
    u = need("admin"); st.subheader("Create / edit campaign"); cs = S.campaign_stats(); opt = {"New": None, **dict(zip(cs.title, cs.id))}
    sel = st.selectbox("Campaign", list(opt)); cur = cs[cs.id == opt[sel]].iloc[0] if opt[sel] else None
    f = {"title": st.text_input("Title", cur.title if cur is not None else ""), "desc": st.text_area("Description", (cur.description or "") if cur is not None else ""),
         "cat": st.selectbox("Category", CATEGORIES), "target": st.number_input("Target", 0.0, 1e9, float(cur.target) if cur is not None else 10000.0),
         "start": st.date_input("Start", dt.date.today()), "end": st.date_input("End", dt.date.today() + dt.timedelta(days=60))}
    if st.button("Save"): e = S.save_campaign(u, f, opt[sel]); st.error(e) if e else (st.success("Saved"), st.rerun())
    if cur is not None and cur.status == "active":
        a, b = st.columns(2)
        if a.button("Mark completed"): S.set_campaign_status(u, opt[sel], "completed"); st.rerun()
        if b.button("Close"): S.set_campaign_status(u, opt[sel], "closed"); st.rerun()
def admin_funds():
    u = need("admin"); cs = S.campaign_stats()
    if cs.empty: st.info("Create a campaign first."); return
    opt = dict(zip(cs.title, cs.id)); t = st.selectbox("Campaign", list(opt)); ds = st.text_input("Description"); cat = st.selectbox("Category", EXPENSE_CATS)
    amt = st.number_input("Amount", 0.0, 1e9, 0.0); dd = st.date_input("Date"); doc = st.text_input("Supporting document ref"); ex = st.text_input("Exception note (only if exceeding funds)")
    if st.button("Record expense"): e = S.add_expense(u, opt[t], ds, cat, amt, dd, doc, ex); st.error(e) if e else st.success("Recorded (self-reported, not independently verified).")
    r = cs[cs.id == opt[t]].iloc[0]; sp = db.one("SELECT COALESCE(SUM(amount),0) s FROM fund_utilization WHERE campaign_id=?", (opt[t],))["s"]
    a = st.columns(3); a[0].metric("Raised", f"{r.raised:,.0f}"); a[1].metric("Recorded spend", f"{sp:,.0f}"); a[2].metric("Remaining", f"{r.raised-sp:,.0f}")
    st.dataframe(db.df("SELECT expense_date,category,description,amount,doc_ref,exception_note FROM fund_utilization WHERE campaign_id=? ORDER BY id DESC", (opt[t],)), use_container_width=True)
def admin_donations():
    u = need("admin"); d = A.load()
    if d.empty: st.info("No donations."); return
    k = st.text_input("Search reference/campaign"); 
    if k: d = d[d.ref.str.contains(k, case=False) | d.campaign.str.contains(k, case=False)]
    st.dataframe(d[["ref", "campaign", "amount", "status", "source", "created_at"]].head(500), use_container_width=True)
    ref = st.text_input("Refund live donation (ref)")
    if st.button("Refund") and ref: e = S.transition(u, ref.strip(), "refunded"); st.error(e) if e else st.success("Refunded")
    st.subheader("Audit log"); st.dataframe(db.df("SELECT created_at,actor_id,action,detail FROM audit_logs ORDER BY id DESC LIMIT 100"), use_container_width=True)
def data_import():
    u = need("admin"); st.subheader("Import dataset"); src = st.radio("Label data as", ["imported", "synthetic"], horizontal=True)
    c1, c2 = st.columns(2); n = c1.number_input("Synthetic rows", 100, 100000, 10000)
    syn = S.synthetic(int(n)); c2.download_button("Download synthetic CSV (seed 42)", syn.to_csv(index=False), "synthetic_donations.csv")
    f = st.file_uploader("CSV or Excel", type=["csv", "xlsx"])
    if not f: return
    if f.size > MAX_UPLOAD_MB * 1024 * 1024: st.error("File too large."); return
    try: d = S.clean(pd.read_csv(f) if f.name.endswith(".csv") else pd.read_excel(f, engine="openpyxl"))
    except Exception as e: st.error(f"Could not read file: {e}"); return
    bad = d[d.problem != ""]; a = st.columns(5); a[0].metric("Rows", len(d)); a[1].metric("Invalid", len(bad)); a[2].metric("Dup IDs in file", int(d.dup_in_file.sum()))
    a[3].metric("Possible dups (review)", int(d.maybe_duplicate.sum())); a[4].metric("Importable", int(((d.problem == "") & ~d.dup_in_file).sum()))
    st.write("Missing values", d.isna().sum()[lambda s: s > 0].to_dict()); st.dataframe(d.head(50)); st.dataframe(bad.head(100))
    st.download_button("Download cleaned data", S.safe_csv(d), "cleaned.csv")
    if st.button("Confirm import"): imp, dup = S.commit_import(u, d, f.name, src); st.success(f"Imported {imp}; {dup} already existed.")
    st.dataframe(db.df("SELECT * FROM data_import_jobs ORDER BY id DESC LIMIT 20"))
def analytics():
    u = need("admin"); d = A.load()
    src = st.sidebar.selectbox("Data source", list(SOURCES), format_func=SOURCES.get); d = d[d.source == src]
    if d.empty: st.info("No data for this source. Generate/import a dataset or make live donations."); return
    r = st.sidebar.date_input("Date range", (d.date.min().date(), d.date.max().date()))
    cf = st.sidebar.multiselect("Campaign", sorted(d.campaign.unique())); cat = st.sidebar.multiselect("Category", sorted(d.category.unique()))
    stf = st.sidebar.multiselect("Payment status (affects payment analysis)", STATUSES); lo, hi = st.sidebar.slider("Amount range", 0.0, float(d.amount.max()), (0.0, float(d.amount.max())))
    if len(r) == 2: d = d[(d.date.dt.date >= r[0]) & (d.date.dt.date <= r[1])]
    if cf: d = d[d.campaign.isin(cf)]
    if cat: d = d[d.category.isin(cat)]
    d = d[(d.amount >= lo) & (d.amount <= hi)]; pay = d[d.status.isin(stf)] if stf else d; s = d[d.status == "successful"]
    st.caption(f"Source: **{SOURCES[src]}**. Pandas + SQLite single-node analytics, not distributed Big Data processing.")
    k = st.columns(4); k[0].metric("Successful total", f"{s.amount.sum():,.0f}"); k[1].metric("Transactions", len(s)); k[2].metric("Mean", f"{s.amount.mean():,.0f}" if len(s) else "-"); k[3].metric("Median", f"{s.amount.median():,.0f}" if len(s) else "-")
    st.subheader("Insights"); [st.markdown("- " + i) for i in A.insights(d, None, None)]
    t = st.tabs(["Time series", "Campaigns", "Donors", "Categories", "Distribution", "Payments", "Funds & attention", "Reports"])
    with t[0]:
        g = st.radio("Grain", ["D", "W", "M"], index=2, horizontal=True); ts = s.set_index("date").amount.resample(g).agg(["sum", "count"]).reset_index()
        ts["pct_change"] = ts["sum"].pct_change() * 100; st.plotly_chart(px.line(ts, x="date", y="sum", markers=True), use_container_width=True)
        st.caption("Resampling inserts empty periods as 0 only for display; absence of records is not proof of no activity."); st.dataframe(ts)
    cp = s.groupby(["campaign", "target"]).agg(total=("amount", "sum"), n=("amount", "size"), donors=("donor", "nunique"), avg=("amount", "mean")).reset_index()
    cp["achieved_%"] = (100 * cp.total / cp.target.replace(0, pd.NA)).round(1); cp["remaining"] = (cp.target - cp.total).clip(lower=0); cp["rank"] = cp.total.rank(ascending=False).astype(int)
    with t[1]: st.plotly_chart(px.bar(cp.sort_values("total"), x="total", y="campaign", orientation="h"), use_container_width=True); st.dataframe(cp.sort_values("rank"))
    fr = s.groupby("donor").agg(n=("amount", "size"), total=("amount", "sum")).reset_index(); rep = int((fr.n >= 2).sum())
    with t[2]:
        a = st.columns(3); a[0].metric("First-time (1 txn)", len(fr) - rep); a[1].metric("Repeat (>=2)", rep); a[2].metric("Repeat %", f"{100*rep/max(len(fr),1):.1f}%")
        st.caption("Repeat = >=2 successful, non-refunded donations inside the selected date range; a wider range finds more repeats. Donor IDs are not shown.")
        st.plotly_chart(px.histogram(fr, x="n", nbins=20, title="Donations per donor"), use_container_width=True)
    ct = s.groupby("category").agg(total=("amount", "sum"), n=("amount", "size"), avg=("amount", "mean")).reset_index(); ct["share_%"] = (100 * ct.total / ct.total.sum()).round(1)
    with t[3]: c = st.columns(2); c[0].plotly_chart(px.bar(ct, x="category", y="total"), use_container_width=True); c[1].plotly_chart(px.pie(ct, names="category", values="total", hole=.5), use_container_width=True); st.dataframe(ct)
    with t[4]:
        if len(s):
            st.write(s.amount.describe(percentiles=[.25, .5, .75, .9, .99]).round(2).to_frame().T); cap = s.amount.quantile(.99)
            st.plotly_chart(px.histogram(s[s.amount <= cap], x="amount", nbins=st.slider("Bins", 5, 100, 30)), use_container_width=True)
            st.caption("Histogram clips the top 1% (99th percentile) for readability; median is preferred over mean because amounts are right-skewed.")
    with t[5]:
        pc = pay.status.value_counts().reset_index(); pc.columns = ["status", "count"]; st.plotly_chart(px.bar(pc, x="status", y="count"), use_container_width=True)
        den = d.status.isin(["successful", "failed"]).sum(); st.metric("Success rate", f"{100*(d.status=='successful').sum()/den:.1f}%" if den else "-")
        st.caption("Success rate = successful / (successful + failed). Pending and refunded are excluded from the denominator.")
    with t[6]:
        ex = db.df("SELECT campaign_id, SUM(amount) spent FROM fund_utilization GROUP BY campaign_id"); cs = S.campaign_stats()
        if src == "live" and not cs.empty:
            m = cs.merge(ex, left_on="id", right_on="campaign_id", how="left").fillna({"spent": 0}); m["utilization_%"] = [S.progress(b, a) for a, b in zip(m.raised, m.spent)]
            st.dataframe(m[["title", "raised", "spent", "utilization_%"]])
            days = st.number_input("Deadline within (days)", 1, 365, ATTN_DAYS); pct = st.number_input("Achieved below (%)", 1.0, 100.0, ATTN_PCT); att = A.attention(cs, days, pct)
            st.dataframe(att) if len(att) else st.success("No campaigns flagged."); st.caption("Rule-based indicator only; it does not predict failure.")
        else: st.info("Fund utilization and attention flags apply to live campaigns (expenses are recorded only for live data).")
    with t[7]:
        for n, x in {"transactions": d.drop(columns=["donor"]), "campaign_performance": cp, "category_analysis": ct, "donor_behavior": fr.assign(donor=range(len(fr))).drop(columns="donor")}.items():
            st.download_button(f"{n}.csv", S.safe_csv(x), f"{n}_{src}.csv", key=n)
        st.caption("Reports contain the selected filters' data only; donor IDs are excluded.")
