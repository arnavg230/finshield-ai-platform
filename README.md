# FinShield AI

FinShield AI is a local web application for transaction screening and AML investigation. It combines a React/Vite frontend, a FastAPI backend, saved PaySim machine-learning models, and rule, behaviour, and network based AML analysis.

## Requirements

- Python 3.10 or 3.11
- Node.js 18 or newer (npm is included)
- Windows, macOS, or Linux

The default local setup uses SQLite, so PostgreSQL is not required.

## Run locally on Windows

Open **two PowerShell windows** from the project directory.

### 1. Set up and start the backend

In the first window:

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
Copy-Item .env.example .env
```

Open `backend/.env` and replace `SECRET_KEY` with a long random value. The example config uses a local SQLite database. Then install dependencies and create the database tables and demo users:

```powershell
pip install -r requirements.txt
python seed.py
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The backend health endpoint is <http://127.0.0.1:8000/health> and the API docs are at <http://127.0.0.1:8000/docs>.

### 2. Set up and start the frontend

In the second PowerShell window:

```powershell
cd frontend
npm ci
npm run dev
```

Open <http://127.0.0.1:5173/login>.

### Demo logins

| Username | Password | Role |
| --- | --- | --- |
| `admin` | `Admin@123` | Admin |
| `analyst` | `Analyst@123` | Analyst |
| `officer` | `Officer@123` | Compliance |
| `customer` | `Customer@123` | Customer |

These accounts are for local demonstration. The seed command leaves existing accounts untouched if they already exist.

## Run locally on macOS or Linux

In the first terminal:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
cp .env.example .env
```

Set a private `SECRET_KEY` in `backend/.env`, then:

```bash
pip install -r requirements.txt
python seed.py
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

In a second terminal:

```bash
cd frontend
npm ci
npm run dev
```

Open <http://127.0.0.1:5173/login>.

## Tests and reports

Run these from the `code/` directory after installing the backend dependencies:

```bash
python -u ml/tests/test_paysim_scenarios.py
python -u ml/test_aml_scenarios_15.py
```

The PaySim runner checks all three saved models and writes a CSV with their predictions and generated features to `ml/reports/paysim_scenario_results.csv`. The AML runner checks the 15 functional scenarios and writes CSV and text reports under `ml/reports/`. The AML Testing screen also runs its 15 scenarios; those test records are rolled back and not saved.

## Troubleshooting

- **The UI says the API is unavailable:** confirm the backend is running on port `8000`, then check `/health`.
- **The ML models do not load:** make sure the files in `ml/models/` are present. The backend finds them in that folder by default.
- **The frontend cannot reach the backend:** start Vite on port `5173`; its development proxy forwards `/api` and `/health` to `127.0.0.1:8000`.
- **PowerShell blocks virtual-environment activation:** use `\.venv\Scripts\python.exe -m pip install -r requirements.txt` and `\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000` from `backend` without activating the environment.

## Project layout

```text
backend/   FastAPI API, database models, auth, and demo seed script
frontend/  React/Vite web interface
ml/        AML and PaySim analysis code, model files, and test reports
```

`backend/.env` and the local database are machine-specific and should not be committed. The tracked `.env.example` contains only local development defaults.
