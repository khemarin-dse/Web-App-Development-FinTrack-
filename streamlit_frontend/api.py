"""Thin client for the Laravel API. Change API_URL here (or via env var) to switch backends."""
import os
import requests
import streamlit as st

# Local Laragon:  http://127.0.0.1:8000/api   |  Deployed: https://fintrack-gvxt.onrender.com/api
API_URL = os.getenv("FINTRACK_API_URL", "http://127.0.0.1:8000/api")


class ApiError(Exception):
    pass


def call(method, path, **kw):
    headers = {"Accept": "application/json"}
    tok = st.session_state.get("token")
    if tok:
        headers["Authorization"] = f"Bearer {tok}"
    try:
        r = requests.request(method, API_URL + path, headers=headers, timeout=90, **kw)
    except requests.RequestException:
        raise ApiError(f"Cannot reach backend at {API_URL}. Is it running?")
    if r.status_code == 401 and tok:
        st.session_state.clear()
        st.rerun()
    if not r.ok:
        try:
            d = r.json()
            errs = d.get("errors")
            msg = " ".join(m for v in errs.values() for m in v) if errs else d.get("message", "Request failed")
        except ValueError:
            msg = f"Server error ({r.status_code})"
        raise ApiError(msg)
    try:
        return r.json()
    except ValueError:
        return {}


get = lambda p, **kw: call("GET", p, **kw)
post = lambda p, **kw: call("POST", p, **kw)
put = lambda p, **kw: call("PUT", p, **kw)
delete = lambda p, **kw: call("DELETE", p, **kw)
