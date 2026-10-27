import os, sys; sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from core import db, services as S
def test_progress(): assert S.progress(50, 200) == 25.0 and S.progress(5, 0) == 0.0
def test_hash(): h = db.hash_pw("secret123"); assert db.check_pw("secret123", h) and not db.check_pw("x", h) and "secret123" not in h
def test_csv_injection():
    import pandas as pd; assert b"'=1+1" in S.safe_csv(pd.DataFrame({"a": ["=1+1"]}))
def test_synthetic_reproducible(): assert S.synthetic(50).equals(S.synthetic(50))
def test_clean_flags_bad_rows():
    d = S.clean(S.synthetic(20).assign(amount=lambda x: x.amount.where(x.index > 0, -5))); assert d.problem.iloc[0] != ""
