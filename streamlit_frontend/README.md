# FinTrack — Streamlit frontend

Talks to the existing Laravel API (backend + MySQL unchanged).

## Run (3 steps)
1. Start the backend (Laragon terminal): `cd backend` → `php artisan serve`  (API at http://127.0.0.1:8000/api)
2. `cd streamlit_frontend` → `pip install -r requirements.txt`
3. `streamlit run app.py`  → opens http://localhost:8501

## Use the deployed backend instead
- PowerShell: `$env:FINTRACK_API_URL="https://fintrack-gvxt.onrender.com/api"; streamlit run app.py`
- (Render free tier sleeps — open the URL once a minute before the demo.)

Or edit the default `API_URL` in `api.py`.
Note: refreshing the browser logs you out (token lives in session state).
