# DonateTrack Analytics
Streamlit + SQLite + Pandas + Plotly donation tracker (DEMO payments only).
## Run
    python -m venv venv && source venv/bin/activate    # Windows: venv\Scripts\activate
    pip install -r requirements.txt
    export ADMIN_EMAIL=admin@example.com ADMIN_PASSWORD='ChooseAStrongOne'   # Windows: set VAR=value
    streamlit run app.py
    pytest
Admin is created only from these env vars (never via registration). Rename the app in `config.py`.
## Use
Admin: create campaign -> Data Import (download synthetic CSV, upload, confirm) -> Big Data Analytics (pick source).
Donor: register -> Donate -> simulator -> My Donations.
## Deploy (Streamlit Community Cloud)
Push to GitHub, create app with main file `app.py`, set ADMIN_EMAIL / ADMIN_PASSWORD in Secrets. Note: SQLite on free hosting is ephemeral.
## Scope note
Single-node analytics (Pandas/SQL); not distributed Big Data. A real gateway needs server-side verification, webhooks, refunds, secrets.
