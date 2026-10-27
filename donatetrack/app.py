import streamlit as st
from config import APP_NAME
from core import db
import views as v
st.set_page_config(page_title=APP_NAME, page_icon="💚", layout="wide")
db.init()
st.markdown("<style>h1,h2,h3{color:#14532d}div[data-testid=stMetric]{background:#f4faf6;border-radius:14px;padding:12px;box-shadow:0 1px 4px #0002}"
            "div[data-testid=stVerticalBlockBorderWrapper]{border-radius:14px}.stButton>button{background:#14532d;color:#fff;border-radius:10px}</style>", unsafe_allow_html=True)
u = st.session_state.get("user"); P = st.Page
pages = [P(v.home, title="Home", url_path="home", default=True), P(v.campaigns, title="Campaigns", url_path="campaigns")]
if not u: pages.append(P(v.auth, title="Login / Register", url_path="login"))
elif u["role"] == "donor": pages += [P(v.donate, title="Donate", url_path="donate"), P(v.my_donations, title="My Donations", url_path="mine")]
else: pages += [P(v.admin_campaigns, title="Manage Campaigns", url_path="manage"), P(v.admin_donations, title="Donations & Audit", url_path="donations"),
                P(v.admin_funds, title="Fund Utilization", url_path="funds"), P(v.data_import, title="Data Import", url_path="import"), P(v.analytics, title="Big Data Analytics", url_path="analytics")]
if u:
    st.sidebar.write(f"👤 {u['name']} ({u['role']})")
    if st.sidebar.button("Log out"): st.session_state.clear(); st.rerun()
st.navigation(pages).run()
