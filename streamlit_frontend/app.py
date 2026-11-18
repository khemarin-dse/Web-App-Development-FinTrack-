import streamlit as st
import api
from common import CURRENCIES

st.set_page_config(page_title="FinTrack", page_icon="💰", layout="wide")
st.session_state.setdefault("currency", "USD")


def auth_page():
    st.markdown("## 💰 FinTrack")
    st.caption("Personal finance tracking — income, budgets, goals and reports.")
    t_login, t_reg, t_forgot = st.tabs(["Log in", "Register", "Forgot password"])
    with t_login:
        with st.form("login"):
            email = st.text_input("Email")
            pw = st.text_input("Password", type="password")
            if st.form_submit_button("Log in", type="primary"):
                try:
                    d = api.post("/login", json={"email": email, "password": pw})
                    st.session_state.update(token=d["token"], user=d["user"])
                    st.rerun()
                except api.ApiError as e:
                    st.error(str(e))
    with t_reg:
        with st.form("register"):
            name = st.text_input("Full name")
            email = st.text_input("Email", key="r_email")
            pw = st.text_input("Password (min 6)", type="password", key="r_pw")
            pw2 = st.text_input("Confirm password", type="password")
            if st.form_submit_button("Create account", type="primary"):
                if pw != pw2:
                    st.error("Passwords do not match")
                else:
                    try:
                        d = api.post("/register", json={"name": name, "email": email,
                                                         "password": pw, "password_confirmation": pw2})
                        st.session_state.update(token=d["token"], user=d["user"])
                        st.rerun()
                    except api.ApiError as e:
                        st.error(str(e))
    with t_forgot:
        st.caption("Demo: the 6-digit code is written to the backend log (storage/logs/laravel.log).")
        fe = st.text_input("Account email", key="f_email")
        if st.button("Send reset code"):
            try:
                st.success(api.post("/forgot-password", json={"email": fe}).get("message", "Sent"))
            except api.ApiError as e:
                st.error(str(e))
        code = st.text_input("6-digit code")
        np_ = st.text_input("New password", type="password", key="f_pw")
        if st.button("Reset password"):
            try:
                api.post("/reset-password", json={"email": fe, "code": code, "token": code,
                                                   "password": np_, "password_confirmation": np_})
                st.success("Password reset. You can log in now.")
            except api.ApiError as e:
                st.error(str(e))


if "token" not in st.session_state:
    auth_page()
    st.stop()

import views  # noqa: E402
import prediction  # noqa: E402

PAGES = {"📊 Dashboard": views.dashboard, "💸 Transactions": views.transactions,
         "🎯 Budget": views.budget, "🏆 Goals": views.goals,
         "📈 Reports": views.reports, "🔮 Prediction": prediction.prediction,
         "⚙️ Settings": views.settings}

with st.sidebar:
    st.markdown("## 💰 FinTrack")
    st.caption(f"Hi, {st.session_state['user']['name']}")
    page = st.radio("Menu", list(PAGES), label_visibility="collapsed")
    st.selectbox("Currency", list(CURRENCIES), key="currency")
    if st.button("Log out", width="stretch"):
        try:
            api.post("/logout")
        except api.ApiError:
            pass
        st.session_state.clear()
        st.rerun()

try:
    PAGES[page]()
except api.ApiError as e:
    st.error(str(e))
