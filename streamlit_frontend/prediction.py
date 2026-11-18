"""Spending prediction page: learns from the user's own past expenses (weekday pattern + trend)."""
from datetime import date, timedelta
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import api
from common import EXPENSE_CATEGORIES, CURRENCIES, money, header

MIN_DAYS = 14      # need at least this many days of history
MIN_TX = 5         # and at least this many expense transactions
MAX_AHEAD = 90


def _daily_series(tx, category):
    """Daily expense totals from first expense to today (days without spending = 0).
    Goal deposits (category 'Savings') are not spending, so they are left out."""
    rows = [(t["date"][:10], float(t["amount"])) for t in tx
            if t["type"] == "expense" and t["category"] != "Savings"
            and (category == "All expenses" or t["category"] == category)]
    if not rows:
        return None, 0
    df = pd.DataFrame(rows, columns=["date", "amount"])
    df["date"] = pd.to_datetime(df["date"])
    s = df.groupby("date")["amount"].sum()
    idx = pd.date_range(s.index.min(), max(s.index.max(), pd.Timestamp(date.today())), freq="D")
    return s.reindex(idx, fill_value=0.0), len(rows)


def _features(dates, start):
    d = pd.DatetimeIndex(dates)
    X = np.zeros((len(d), 8))
    X[np.arange(len(d)), d.weekday] = 1.0            # weekday effect (Mon..Sun)
    X[:, 7] = (d - start).days / 30.0                # slow trend
    return X


def _fit_predict(series, future_dates):
    """Ridge-regularised linear regression: weekday dummies + trend. Returns (pred, resid_std)."""
    start = series.index[0]
    X = _features(series.index, start)
    y = series.values
    lam = 1.0
    w = np.linalg.solve(X.T @ X + lam * np.eye(X.shape[1]), X.T @ y)
    resid = y - X @ w
    if len(y) > 2:
        # ignore the most extreme 5% each side so one-off big days don't blow up the range
        lo, hi = np.percentile(resid, [5, 95])
        std = float(np.clip(resid, lo, hi).std())
    else:
        std = float(y.std())
    pred = np.clip(_features(future_dates, start) @ w, 0, None)
    return pred, std


def prediction():
    header("Spending Prediction", "Estimate how much you'll spend, based on your own past transactions")
    today = date.today()
    tx = api.get("/transactions")

    c1, c2 = st.columns(2)
    horizon = c1.selectbox("Predict spending for", ["Tomorrow", "Next 7 days", "Next 30 days", "Pick a date"])
    cat = c2.selectbox("Category", ["All expenses"] + EXPENSE_CATEGORIES)
    target = None
    if horizon == "Pick a date":
        target = st.date_input("Date", today + timedelta(days=1), min_value=today + timedelta(days=1),
                               max_value=today + timedelta(days=MAX_AHEAD))
    go_btn = st.button("Predict", type="primary")
    if not go_btn:
        st.info("Choose what to predict, then press **Predict**.")
        return

    series, n_tx = _daily_series(tx, cat)
    if series is None:
        st.warning("No expenses found yet" + ("" if cat == "All expenses" else f" for {cat}") +
                   ". Add some transactions first.")
        return
    days = len(series)
    if days < MIN_DAYS or n_tx < MIN_TX:
        st.warning(f"Not enough data yet: you have {n_tx} expense transactions over {days} days. "
                   f"I need at least {MIN_TX} transactions spread over {MIN_DAYS}+ days for a decent prediction.")
        return

    if horizon == "Tomorrow":
        future = [today + timedelta(days=1)]
    elif horizon == "Next 7 days":
        future = [today + timedelta(days=i) for i in range(1, 8)]
    elif horizon == "Next 30 days":
        future = [today + timedelta(days=i) for i in range(1, 31)]
    else:
        future = [today + timedelta(days=i) for i in range(1, (target - today).days + 1)]

    pred, std = _fit_predict(series, future)
    day_total = float(pred[-1]) if horizon in ("Tomorrow", "Pick a date") else float(pred.sum())
    n = 1 if horizon in ("Tomorrow", "Pick a date") else len(future)
    spread = std * (n ** 0.5)
    low, high = max(day_total - spread, 0.0), day_total + spread
    if horizon == "Pick a date":
        label = f"Predicted spending on {target:%b %d}"
    elif horizon == "Tomorrow":
        label = f"Predicted spending tomorrow ({future[0]:%b %d})"
    else:
        label = f"Predicted spending, {horizon.lower()}"

    last30 = series[series.index >= pd.Timestamp(today - timedelta(days=29))]
    avg30 = float(last30.mean()) if len(last30) else 0.0
    expected_avg = day_total / n
    diff = ((expected_avg - avg30) / avg30 * 100) if avg30 > 0 else 0
    conf = "high" if days >= 60 else "medium" if days >= 30 else "low"

    m = st.columns(3)
    m[0].metric(label, money(day_total), f"likely {money(low)} – {money(high)}".replace("$", "\\$"), delta_color="off")
    m[1].metric("Your daily average (last 30 days)", money(avg30), f"{diff:+.0f}% vs predicted day", delta_color="off")
    m[2].metric("Data used", f"{n_tx} transactions", f"{days} days · confidence: {conf}", delta_color="off")

    # chart: last 14 days actual + forecast
    rate = CURRENCIES[st.session_state["currency"]][1]
    past = series.iloc[-14:]
    chart_future = future if len(future) > 1 else [today + timedelta(days=i) for i in range(1, 4)]
    cpred, _ = _fit_predict(series, chart_future)
    fig = go.Figure()
    fig.add_bar(x=past.index, y=past.values * rate, name="Actual spending", marker_color="#534AB7")
    fx = [pd.Timestamp(d) for d in chart_future]
    fig.add_scatter(x=fx, y=np.clip(cpred + std, 0, None) * rate, mode="lines", line=dict(width=0),
                    showlegend=False, hoverinfo="skip")
    fig.add_scatter(x=fx, y=np.clip(cpred - std, 0, None) * rate, mode="lines", line=dict(width=0),
                    fill="tonexty", fillcolor="rgba(93,202,165,0.18)", name="Likely range", hoverinfo="skip")
    fig.add_scatter(x=fx, y=cpred * rate, mode="lines+markers", name="Predicted",
                    line=dict(color="#5DCAA5", dash="dash", width=3))
    fig.update_layout(margin=dict(t=10, b=10), legend_title=None, xaxis_title=None, yaxis_title=None)
    st.subheader("Past 14 days and forecast")
    st.plotly_chart(fig, width="stretch")

    # breakdown by category (share of the last 30 days), only for "All expenses"
    if cat == "All expenses":
        cutoff = str(today - timedelta(days=29))
        sub = pd.DataFrame([(t["category"], float(t["amount"])) for t in tx
                            if t["type"] == "expense" and t["category"] != "Savings" and t["date"][:10] >= cutoff],
                           columns=["category", "amount"])
        if not sub.empty:
            share = sub.groupby("category")["amount"].sum().sort_values(ascending=False)
            st.subheader("Where it will likely go")
            for name, v in share.head(5).items():
                p = v / share.sum()
                st.write(f"{name} — {money(day_total * p)} ({p:.0%})")
                st.progress(float(p))

    with st.expander("How does this work?"):
        st.write(
            "The model is a ridge-regularised **linear regression** trained on your own daily spending. "
            "It uses two things: the **day of the week** (e.g. weekends usually cost more) and a slow **trend** "
            "over time. The 'likely range' is one standard deviation of how far past days were from the model. "
            "Goal deposits (category *Savings*) are not counted as spending. More history means a better prediction."
        )
