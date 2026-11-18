from datetime import date
import pandas as pd
import plotly.express as px
import streamlit as st
import api
from common import (EXPENSE_CATEGORIES, INCOME_CATEGORIES, GOAL_TYPES, CURRENCIES,
                    PALETTE, money, header)

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _ok(msg):
    st.toast(msg, icon="✅")


def _month_options(n=12):
    t = date.today()
    out = []
    y, m = t.year, t.month
    for _ in range(n):
        out.append(f"{y}-{m:02d}")
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    return out


def _available():
    """Savings of the CURRENT month (income - expenses): the only money a goal may use."""
    return round(float(api.get("/dashboard/summary")["savings"]), 2)


def _fmt(d):
    """'2026-11-18T00:00:00Z' -> 'Nov 18, 2026'"""
    return date.fromisoformat(str(d)[:10]).strftime("%b %d, %Y") if d else "—"


# ---------------------------------------------------------------- Dashboard
def dashboard():
    header("Dashboard", "Your financial overview")
    chart = api.get("/dashboard/chart")
    monthly = chart["monthly"] if isinstance(chart, dict) and "monthly" in chart else chart
    today = date.today()
    sel = st.selectbox("Month", MONTHS, index=today.month - 1)
    row = next((m for m in monthly if m["month"] == sel), None) or {}
    month_key = row.get("monthKey", today.strftime("%Y-%m"))

    c = st.columns(4)
    c[0].metric("Income", money(row.get("income", 0)))
    c[1].metric("Expenses", money(row.get("expense", 0)))
    c[2].metric("Remaining money", money(row.get("savings", 0)), f"{row.get('savings_rate', 0)}% of income left")
    c[3].metric("Budget used", f"{row.get('budget_used_pct', 0)}%",
                f"{money(row.get('budget_remaining', 0))} left", delta_color="off")

    df = pd.DataFrame(monthly)
    left, right = st.columns([3, 2])
    with left:
        st.subheader("Income vs expenses")
        if not df.empty:
            d = df.melt(id_vars="month", value_vars=["income", "expense"], var_name="type", value_name="amount")
            d["amount"] = d["amount"] * CURRENCIES[st.session_state["currency"]][1]
            fig = px.bar(d, x="month", y="amount", color="type", barmode="group",
                         color_discrete_map={"income": "#5DCAA5", "expense": "#534AB7"})
            fig.update_layout(margin=dict(t=10, b=10), legend_title=None, yaxis_title=None, xaxis_title=None)
            st.plotly_chart(fig, width="stretch")
    with right:
        st.subheader(f"Spending by category ({sel})")
        cats = row.get("categories", [])
        if cats:
            cd = pd.DataFrame(cats)
            cd["value"] = cd["value"] * CURRENCIES[st.session_state["currency"]][1]
            fig = px.pie(cd, names="name", values="value", hole=0.5, color_discrete_sequence=PALETTE)
            fig.update_layout(margin=dict(t=10, b=10))
            st.plotly_chart(fig, width="stretch")
        else:
            st.info("No expenses that month.")

    a, b = st.columns(2)
    with a:
        st.subheader(f"Recent transactions ({sel})")
        tx = api.get("/transactions", params={"month": month_key, "limit": 6})
        if tx:
            for t in tx:
                sign = "+" if t["type"] == "income" else "-"
                st.write(f"**{t['description']}** · {t['category']} · {t['date'][:10]}  \n"
                         f"{sign}{money(t['amount'])}")
        else:
            st.info("No transactions that month.")
    with b:
        st.subheader(f"Budget tracker ({sel})")
        budgets = row.get("budgets", [])
        if budgets:
            for bd in budgets:
                pct = bd["spent_amount"] / bd["limit_amount"] if bd["limit_amount"] else 0
                st.write(f"{bd['category']} — {money(bd['spent_amount'])} / {money(bd['limit_amount'])}")
                st.progress(min(pct, 1.0))
        else:
            st.info("No budgets set for this month.")


# ------------------------------------------------------------- Transactions
def transactions():
    header("Transactions", "Add, search and manage your income and expenses")
    with st.expander("➕ Add transaction", expanded=False):
        typ = st.radio("Type", ["expense", "income"], horizontal=True)
        goals = api.get("/goals")
        with st.form("add_tx", clear_on_submit=True):
            c1, c2 = st.columns(2)
            desc = c1.text_input("Description")
            amt = c2.number_input("Amount (USD)", min_value=0.0, step=1.0)
            cat = c1.selectbox("Category", EXPENSE_CATEGORIES if typ == "expense" else INCOME_CATEGORIES)
            d = c2.date_input("Date", date.today())
            gmap = {"— none —": None, **{g["name"]: g["id"] for g in goals}}
            gname = st.selectbox("Link to goal (optional)", list(gmap)) if typ == "income" and goals else "— none —"
            note = st.text_input("Note (optional)")
            if st.form_submit_button("Save", type="primary"):
                if not desc.strip() or amt <= 0:
                    st.error("Enter a description and an amount above 0")
                else:
                    body = {"type": typ, "description": desc, "amount": amt, "category": cat,
                            "date": str(d), "note": note or None, "goal_id": gmap[gname]}
                    try:
                        api.post("/transactions", json=body)
                        _ok("Transaction added")
                        st.rerun()
                    except api.ApiError as e:
                        st.error(str(e))

    c1, c2 = st.columns([3, 1])
    q = c1.text_input("Search", placeholder="Search description or category")
    f = c2.selectbox("Filter", ["all", "income", "expense"])
    tx = api.get("/transactions")
    rows = [t for t in tx if (f == "all" or t["type"] == f)
            and (q.lower() in t["description"].lower() or q.lower() in t["category"].lower())]
    if not rows:
        st.info("No transactions found.")
        return
    for t in rows:
        c = st.columns([4, 2, 2, 1])
        c[0].write(f"**{t['description']}**  \n{t['category']} · {t['date'][:10]}")
        c[1].write(t["type"].title())
        sign = "+" if t["type"] == "income" else "-"
        c[2].write(f"{sign}{money(t['amount'])}")
        if c[3].button("🗑", key=f"dt{t['id']}"):
            api.delete(f"/transactions/{t['id']}")
            _ok("Deleted")
            st.rerun()


# ------------------------------------------------------------------- Budget
def budget():
    header("Budget", "Set monthly limits and track your spending")
    month = st.selectbox("Month", _month_options())
    bl = api.get("/budgets", params={"month": month})
    total = sum(float(b["limit_amount"]) for b in bl)
    spent = sum(float(b["spent_amount"]) for b in bl)
    c = st.columns(3)
    c[0].metric("Total budget", money(total))
    c[1].metric("Spent", money(spent))
    c[2].metric("Remaining", money(total - spent))

    with st.expander("➕ Add budget"):
        with st.form("add_budget", clear_on_submit=True):
            cat = st.selectbox("Category", EXPENSE_CATEGORIES)
            lim = st.number_input("Monthly limit (USD)", min_value=1.0, step=10.0)
            if st.form_submit_button("Save", type="primary"):
                try:
                    api.post("/budgets", json={"category": cat, "limit_amount": lim, "month": month})
                    _ok("Budget saved")
                    st.rerun()
                except api.ApiError as e:
                    st.error(str(e))
    if not bl:
        st.info("No budgets for this month.")
    for b in bl:
        lim, sp = float(b["limit_amount"]), float(b["spent_amount"])
        pct = sp / lim if lim else 0
        status = "🔴 Over budget" if pct >= 1 else "🟠 Near limit" if pct >= 0.8 else "🟢 On track"
        cols = st.columns([5, 2, 1, 1])
        cols[0].write(f"**{b['category']}** — {money(sp)} / {money(lim)} ({pct:.0%}) {status}")
        cols[0].progress(min(pct, 1.0))
        new = cols[1].number_input("Limit", value=lim, min_value=1.0, key=f"bl{b['id']}", label_visibility="collapsed")
        if cols[2].button("💾", key=f"bs{b['id']}"):
            api.put(f"/budgets/{b['id']}", json={"limit_amount": new})
            _ok("Updated")
            st.rerun()
        if cols[3].button("🗑", key=f"bd{b['id']}"):
            api.delete(f"/budgets/{b['id']}")
            _ok("Deleted")
            st.rerun()


# -------------------------------------------------------------------- Goals
def goals():
    if st.session_state.get("goal_id"):
        return goal_detail(st.session_state["goal_id"])
    header("Goals", "Save towards the things that matter")
    with st.expander("➕ New goal"):
        avail = _available()
        st.caption(f"Available this month: **{money(max(avail, 0))}** — 'Already saved' comes out of this month's remaining money.")
        with st.form("new_goal", clear_on_submit=True):
            c1, c2 = st.columns(2)
            name = c1.text_input("Goal name")
            typ = c2.selectbox("Type", GOAL_TYPES)
            target = c1.number_input("Target (USD)", min_value=1.0, step=50.0)
            saved = c2.number_input("Already saved (USD)", min_value=0.0, max_value=max(avail, 0.0), step=10.0)
            dl = c1.date_input("Deadline (required)", value=None, min_value=date.today())
            note = c2.text_input("Note (optional)")
            if st.form_submit_button("Create", type="primary"):
                if not name.strip():
                    st.error("Please enter a goal name.")
                elif target <= 0:
                    st.error("Target must be above 0.")
                elif saved > target:
                    st.error("Already saved can't be more than the target.")
                elif saved > max(avail, 0.0):
                    st.error(f"Not enough remaining money this month. Available: {money(max(avail, 0))}.")
                elif dl is None:
                    st.warning("Please pick a deadline so we can work out how much to save each month.")
                elif dl < date.today():
                    st.error("Deadline can't be in the past. Pick today or a future date.")
                else:
                    try:
                        api.post("/goals", json={"name": name.strip(), "type": typ, "target_amount": target,
                                                 "saved_amount": saved, "deadline": str(dl),
                                                 "note": note or None})
                        _ok("Goal created")
                        st.rerun()
                    except api.ApiError as e:
                        st.error(str(e))
    gl = api.get("/goals")
    if not gl:
        st.info("No goals yet.")
    cols = st.columns(2)
    for i, g in enumerate(gl):
        t, s = float(g["target_amount"]), float(g["saved_amount"])
        with cols[i % 2].container(border=True):
            st.markdown(f"**{g['name']}** · {g['type']}")
            st.progress(min(s / t, 1.0) if t else 0)
            st.caption(f"{money(s)} of {money(t)} ({(s / t if t else 0):.0%})")
            st.caption(f"Started {_fmt(g.get('created_at'))} · Deadline {_fmt(g.get('deadline'))}")
            if st.button("Open", key=f"og{g['id']}"):
                st.session_state["goal_id"] = g["id"]
                st.rerun()


def goal_detail(gid):
    if st.button("← Back to goals"):
        st.session_state.pop("goal_id")
        st.rerun()
    d = api.get(f"/goals/{gid}")
    g, hist = d["goal"], d["history"]
    t, s = float(g["target_amount"]), float(g["saved_amount"])
    header(g["name"], f"{g['type']} · Started {_fmt(g.get('created_at'))} · Deadline {_fmt(g.get('deadline'))}")
    st.progress(min(s / t, 1.0) if t else 0)
    c = st.columns(4)
    c[0].metric("Saved", money(s))
    c[1].metric("Target", money(t))
    c[2].metric("Remaining", money(max(t - s, 0)))
    if g.get("deadline"):
        dl = date.fromisoformat(g["deadline"][:10])
        months = max((dl.year - date.today().year) * 12 + dl.month - date.today().month, 0)
        c[3].metric("Needed / month", money(max(t - s, 0) / months) if months else "—", f"{months} mo left", delta_color="off")

    st.subheader("Add money")
    avail = _available()
    today = date.today()
    st.caption("This is moved out of this month's remaining money — it does not count as new income. "
               "You can only use this month's remaining money (up to today).")
    if avail > 0:
        st.info(f"Available this month: {money(avail)}")
    else:
        st.warning("No remaining money this month. Add income first, or wait for next month.")
    with st.form("addmoney", clear_on_submit=True):
        a, b = st.columns(2)
        amt = a.number_input("Amount (USD)", min_value=0.0, max_value=max(avail, 0.0), step=5.0)
        dt = b.date_input("Date", today, min_value=today.replace(day=1), max_value=today)
        note = st.text_input("Note (optional)")
        if st.form_submit_button("Add to goal", type="primary", disabled=avail <= 0):
            if amt <= 0:
                st.error("Enter an amount above 0")
            elif amt > avail:
                st.error(f"Not enough remaining money this month. Available: {money(avail)}.")
            else:
                try:
                    api.post(f"/goals/{gid}/add-money", json={"amount": amt, "date": str(dt), "note": note or None})
                    _ok("Money added")
                    st.rerun()
                except api.ApiError as e:
                    st.error(str(e))

    st.subheader("History")
    if hist:
        for h in hist:
            st.write(f"{str(h['date'])[:10]} · {h['description']} · **+{money(h['amount'])}** ({h['source']})")
    else:
        st.info("No deposits yet.")

    with st.expander("✏️ Edit / delete goal"):
        with st.form("editgoal"):
            n = st.text_input("Name", g["name"])
            tg = st.number_input("Target (USD)", min_value=1.0, value=t)
            cur_dl = date.fromisoformat(g["deadline"][:10]) if g.get("deadline") else None
            ndl = st.date_input("Deadline (required)", value=cur_dl,
                                min_value=min(date.today(), cur_dl) if cur_dl else date.today())
            if st.form_submit_button("Save changes"):
                if not n.strip():
                    st.error("Please enter a goal name.")
                elif tg < s:
                    st.error("Target can't be lower than what you've already saved.")
                elif ndl is None:
                    st.warning("Please pick a deadline.")
                elif ndl < date.today() and ndl != cur_dl:
                    st.error("Deadline can't be in the past.")
                else:
                    try:
                        api.put(f"/goals/{gid}", json={"name": n.strip(), "target_amount": tg, "deadline": str(ndl)})
                        _ok("Updated")
                        st.rerun()
                    except api.ApiError as e:
                        st.error(str(e))
        if st.button("Delete goal", type="primary"):
            api.delete(f"/goals/{gid}")
            st.session_state.pop("goal_id")
            st.rerun()


# ------------------------------------------------------------------ Reports
def reports():
    header("Reports", "Understand your habits over time")
    labels = {"Last 6 months": "6months", "This year": "year", "Last year": "lastyear"}
    p = st.selectbox("Period", list(labels))
    r = api.get("/reports/summary", params={"period": labels[p]})
    tot = r["totals"]
    c = st.columns(4)
    c[0].metric("Income", money(tot["income"]))
    c[1].metric("Expenses", money(tot["expense"]))
    c[2].metric("Remaining money", money(tot["savings"]), f"{tot['savings_rate']}% of income left")
    c[3].metric("Avg monthly spend", money(tot["avg_monthly"]))
    df = pd.DataFrame(r["monthly"])
    if df.empty:
        st.info("No data for this period.")
        return
    rate = CURRENCIES[st.session_state["currency"]][1]
    for col in ("income", "expense", "savings"):
        df[col] = df[col] * rate
    l, rr = st.columns(2)
    with l:
        st.subheader("Income vs expenses")
        d = df.melt(id_vars="month_label", value_vars=["income", "expense"], var_name="type", value_name="amount")
        fig = px.bar(d, x="month_label", y="amount", color="type", barmode="group",
                     color_discrete_map={"income": "#5DCAA5", "expense": "#534AB7"})
        fig.update_layout(legend_title=None, xaxis_title=None, yaxis_title=None, margin=dict(t=10))
        st.plotly_chart(fig, width="stretch")
    with rr:
        st.subheader("Remaining money trend")
        fig = px.line(df, x="month_label", y="savings", markers=True, color_discrete_sequence=["#534AB7"])
        fig.update_layout(xaxis_title=None, yaxis_title=None, margin=dict(t=10))
        st.plotly_chart(fig, width="stretch")
    st.download_button("⬇ Export CSV", df.to_csv(index=False), "fintrack_report.csv", "text/csv")


# ----------------------------------------------------------------- Settings
def settings():
    header("Settings", "Manage your account and preferences")
    u = st.session_state["user"]
    l, r = st.columns(2)
    with l:
        st.subheader("Profile")
        with st.form("profile"):
            n = st.text_input("Full name", u["name"])
            e = st.text_input("Email", u["email"])
            if st.form_submit_button("Save profile"):
                try:
                    res = api.put("/user/profile", json={"name": n, "email": e})
                    st.session_state["user"] = res["user"]
                    _ok("Profile updated")
                    st.rerun()
                except api.ApiError as ex:
                    st.error(str(ex))
    with r:
        st.subheader("Password")
        with st.form("pw", clear_on_submit=True):
            cur = st.text_input("Current password", type="password")
            new = st.text_input("New password (min 6)", type="password")
            conf = st.text_input("Confirm new password", type="password")
            if st.form_submit_button("Update password"):
                if len(new) < 6 or new != conf:
                    st.error("Min 6 characters and both must match")
                else:
                    try:
                        api.put("/user/password", json={"current_password": cur, "password": new,
                                                        "password_confirmation": conf})
                        _ok("Password updated")
                    except api.ApiError as ex:
                        st.error(str(ex))
    st.subheader("Danger zone")
    d1, d2 = st.columns(2)
    with d1:
        ok = st.checkbox("I understand — clear all my transactions, budgets and goals")
        if st.button("Clear all data", disabled=not ok):
            api.delete("/user/data")
            _ok("All data cleared")
    with d2:
        ok2 = st.checkbox("I understand — permanently delete my account")
        if st.button("Delete account", disabled=not ok2, type="primary"):
            api.delete("/user/account")
            st.session_state.clear()
            st.rerun()
