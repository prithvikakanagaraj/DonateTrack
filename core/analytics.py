import pandas as pd, numpy as np
from core import db
def load():
    d = db.df("""SELECT d.id,d.ref,d.amount,d.status,d.method,d.source,d.created_at,d.campaign_id,c.title campaign,c.category,c.target,c.end_date,
      COALESCE('U'||d.user_id, d.donor_ref) donor FROM donations d JOIN campaigns c ON c.id=d.campaign_id""")
    d["date"] = pd.to_datetime(d["created_at"]); return d
def insights(d, camp, cfg):
    s = d[d.status == "successful"]; out = []
    if s.empty: return ["No successful donations in the current selection."]
    t = s.groupby("campaign").amount.sum().sort_values(ascending=False); out.append(f"Top campaign: **{t.index[0]}** with {t.iloc[0]:,.0f} collected.")
    m = s.groupby(s.date.dt.to_period("M")).amount.sum(); out.append(f"Busiest month: **{m.idxmax()}** ({m.max():,.0f}).")
    if len(m) > 1: out.append(f"Latest month vs previous: {100*(m.iloc[-1]-m.iloc[-2])/m.iloc[-2]:+.1f}% (partial months can mislead).")
    c = s.groupby("category").amount.sum(); out.append(f"Largest category share: **{c.idxmax()}** ({100*c.max()/c.sum():.1f}%).")
    f = s.groupby("donor").size(); out.append(f"Repeat donors: {100*(f>=2).mean():.1f}% of {len(f)} donors in this period.")
    return out
def attention(camp, days, pct):
    c = camp[camp.status == "active"].copy(); c["days_left"] = (pd.to_datetime(c.end_date) - pd.Timestamp.today().normalize()).dt.days
    c["pct"] = np.where(c.target > 0, 100 * c.raised / c.target, 0)
    c = c[(c.days_left <= days) & (c.pct < pct)]
    c["reason"] = c.apply(lambda r: f"{r.days_left} days left and only {r.pct:.1f}% of target (rule: <= {days} days & < {pct}%)", axis=1)
    return c[["title", "days_left", "pct", "reason"]]
