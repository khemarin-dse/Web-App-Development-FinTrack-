import streamlit as st

EXPENSE_CATEGORIES = ["Housing", "Food", "Transport", "Entertainment", "Utilities",
                      "Healthcare", "Education", "Shopping", "Others"]
INCOME_CATEGORIES = ["Salary", "Freelance", "Investment", "Others"]
GOAL_TYPES = ["Vacation", "Emergency fund", "Electronics", "Vehicle", "Education", "Housing", "Others"]
CURRENCIES = {"USD": ("$", 1.0), "KHR": ("៛", 4082.0), "EUR": ("€", 0.92), "GBP": ("£", 0.79)}
PALETTE = ["#534AB7", "#5DCAA5", "#FAC775", "#F0997B", "#AFA9EC"]


def money(v):
    sym, rate = CURRENCIES[st.session_state.get("currency", "USD")]
    v = float(v or 0) * rate
    return f"{sym}{v:,.0f}" if rate > 100 else f"{sym}{v:,.2f}"


def header(title, sub):
    st.title(title)
    st.caption(sub)
