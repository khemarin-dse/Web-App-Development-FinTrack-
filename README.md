# FinTrack — Personal Finance Tracking System

Full-stack personal finance app: **Streamlit** frontend, **Laravel** REST API backend, **MySQL** database.
Track income and expenses, set monthly budgets, save towards goals, view reports, and predict future spending.

> The original React + Vite frontend is still in `frontend/` as a fallback. The main frontend is `streamlit_frontend/`.

---

## Tech Stack

| Layer    | Tool                                     |
|----------|------------------------------------------|
| Frontend | Streamlit (Python), Plotly, pandas       |
| Backend  | Laravel 13 (PHP 8.4+), REST API          |
| Database | MySQL                                    |
| Auth     | Laravel Sanctum (token-based)            |

---

## Features

- Register, login, logout, forgot password (demo reset code is written to the Laravel log)
- **Dashboard** — pick a month to see income, expenses, **remaining money**, budget used, charts and recent transactions
- **Transactions** — add, search, filter and delete income and expenses
- **Budget** — monthly limit per category with progress and over-budget warnings
- **Goals** — target, start date, deadline, progress, needed per month and deposit history
  - Money for a goal can only come from **this month's remaining money** (income − expenses), up to today
  - Past and future months are not allowed, and a deposit can't be more than what is available
- **Reports** — 6 months / this year / last year, charts and CSV export
- **Prediction** — predicts spending for tomorrow, the next 7 / 30 days or a chosen date, from your own past expenses (linear regression on weekday pattern + trend)
- **Settings** — profile, password, display currency (USD, KHR, EUR, GBP), clear data, delete account
- All data is per user

---

## Prerequisites

- **PHP 8.4+** and **Composer** (Laragon includes both). Enable the `zip` extension in PHP.
- **MySQL** running on port 3306 (Laragon)
- **Python 3.10+** with `pip`

---

## Setup

### 1. Create the database

In HeidiSQL (or any MySQL tool) create an empty database, for example `fintrack_streamlit`.
(Or run `database/setup.sql`, which creates a database named `fintrack`.)

### 2. Backend (Laravel)

```bash
cd backend
composer install
copy .env.example .env        # macOS/Linux: cp .env.example .env
php artisan key:generate
```

Open `backend/.env` and set:

```
DB_CONNECTION=mysql
DB_HOST=127.0.0.1
DB_PORT=3306
DB_DATABASE=fintrack_streamlit
DB_USERNAME=root
DB_PASSWORD=
SESSION_DRIVER=file
```

Then create the tables and start the server:

```bash
php artisan migrate
php artisan db:seed       # optional demo user
php artisan serve
```

The API runs at **http://127.0.0.1:8000/api**. Leave this terminal open.

### 3. Frontend (Streamlit)

Open a second terminal:

```bash
cd streamlit_frontend
pip install -r requirements.txt
python -m streamlit run app.py
```

The app opens at **http://localhost:8501**. Register a new account to start.

> Refreshing the browser page logs you out (the login token lives in the Streamlit session).

### Use the deployed backend instead

Skip steps 1–2 and point Streamlit at the hosted API:

```powershell
$env:FINTRACK_API_URL="https://fintrack-gvxt.onrender.com/api"
python -m streamlit run app.py
```

The free Render server sleeps when idle, so the first request can take 30–60 seconds.

---

## Demo login (after `php artisan db:seed`)

| Field    | Value           |
|----------|-----------------|
| Email    | khem@email.com  |
| Password | password123     |

---

## Project Structure

```
fintrack/
├── streamlit_frontend/      # Streamlit app (main frontend)
│   ├── app.py               # login/register + sidebar navigation
│   ├── api.py               # API client (API_URL set here or via FINTRACK_API_URL)
│   ├── views.py             # Dashboard, Transactions, Budget, Goals, Reports, Settings
│   ├── prediction.py        # Spending prediction page
│   ├── common.py            # categories, currencies, helpers
│   └── requirements.txt
├── backend/                 # Laravel API
│   ├── app/Http/Controllers/
│   ├── app/Models/
│   ├── app/Support/GoalFunding.php   # rules for moving money into goals
│   ├── database/migrations/
│   └── routes/api.php
├── frontend/                # Old React + Vite frontend (fallback)
└── database/setup.sql       # creates the MySQL database
```

---

## API Endpoints

| Method | Endpoint                    | Description                    |
|--------|-----------------------------|--------------------------------|
| POST   | /api/register               | Register                       |
| POST   | /api/login                  | Login                          |
| POST   | /api/forgot-password        | Send reset code (demo: logged) |
| POST   | /api/reset-password         | Reset password with code       |
| POST   | /api/logout                 | Logout                         |
| GET    | /api/dashboard/summary      | Current month summary          |
| GET    | /api/dashboard/chart        | Monthly chart data             |
| GET    | /api/transactions           | List (filters: month, limit)   |
| POST   | /api/transactions           | Add transaction                |
| PUT    | /api/transactions/{id}      | Update transaction             |
| DELETE | /api/transactions/{id}      | Delete transaction             |
| GET    | /api/budgets                | List budgets for a month       |
| POST   | /api/budgets                | Set a budget                   |
| PUT    | /api/budgets/{id}           | Update budget                  |
| DELETE | /api/budgets/{id}           | Delete budget                  |
| GET    | /api/goals                  | List goals                     |
| POST   | /api/goals                  | Create a goal                  |
| GET    | /api/goals/{id}             | Goal detail + history          |
| PUT    | /api/goals/{id}             | Update goal                    |
| DELETE | /api/goals/{id}             | Delete goal                    |
| POST   | /api/goals/{id}/add-money   | Add money to a goal            |
| GET    | /api/reports/summary        | Reports (period: 6months, year, lastyear) |
| PUT    | /api/user/profile           | Update profile                 |
| PUT    | /api/user/password          | Change password                |
| DELETE | /api/user/data              | Clear all data                 |
| DELETE | /api/user/account           | Delete account                 |

---

## Troubleshooting

- **"Cannot reach backend"** in Streamlit — `php artisan serve` isn't running, or `API_URL` points to the wrong place.
- **`streamlit` is not recognized** — use `python -m streamlit run app.py`.
- **`composer install` complains about zip** — enable the `zip` extension in PHP (Laragon → PHP → Extensions).
- **`php artisan migrate` says "Nothing to migrate" but HeidiSQL is empty** — `.env` is still using `DB_CONNECTION=sqlite` or the old database name. Set the `DB_*` lines above, then run `php artisan config:clear`.
- **Error about a missing `sessions` table** — set `SESSION_DRIVER=file` in `.env`, then `php artisan config:clear`.
- **Prediction says "not enough data"** — it needs at least 5 expense transactions spread over 14+ days.
