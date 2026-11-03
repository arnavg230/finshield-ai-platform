# FinShield AI — Member 1: Backend & Security

FastAPI + PostgreSQL backend for the FinShield AI platform (UCS503P).

This service stores transactions, runs them through **Member 2's trained ML models**
and **Member 4's AML module**, combines both into a hybrid risk score, raises alerts,
and supports the investigation case workflow with a full audit trail.

---

## 1. Expected repository layout

The backend imports the teammates' code from sibling folders, so the repo looks like this:

```
FinShield-AI/
├── member1_backend/     <- this folder
├── member2_ml/          <- Member 2's .pkl files
├── member3_frontend/    <- Member 3's React app (pending)
└── member4_aml/         <- Member 4's aml/ python package
```

If your folders are named differently, set `ML_MODELS_DIR` and `AML_PACKAGE_DIR`
in `.env` instead of renaming anything.

---

## 2. Setup

### 2.1 Create the database

```bash
psql -U postgres -c "CREATE DATABASE finshield;"
```

### 2.2 Install dependencies

```bash
cd member1_backend
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux

pip install -r requirements.txt
```

### 2.3 Configure

```bash
copy .env.example .env         # Windows
# cp .env.example .env         # macOS / Linux
```

Edit `DATABASE_URL` with your PostgreSQL password.

### 2.4 Create the demo users

```bash
python seed.py
```

| Username   | Password       | Role       |
| ---------- | -------------- | ---------- |
| `admin`    | `Admin@123`    | ADMIN      |
| `analyst`  | `Analyst@123`  | ANALYST    |
| `officer`  | `Officer@123`  | COMPLIANCE |
| `customer` | `Customer@123` | CUSTOMER   |

### 2.5 Run

```bash
uvicorn app.main:app --reload
```

* Swagger UI — <http://127.0.0.1:8000/docs>
* ReDoc — <http://127.0.0.1:8000/redoc>
* Health check — <http://127.0.0.1:8000/health>

`/health` confirms that the ML models and the AML module actually loaded. Check it first
if anything looks wrong.

---

## 3. How the members' code is integrated

### Member 2 — ML models (`app/services/ml_service.py`)

Member 2 supplied four pickle files and no code, so the service works out the calling
contract from the files themselves:

* The **18 feature names and their order** come from `paysim_scaler.feature_names_in_`.
* Six features are derived in `build_features()`:

  | Feature | Formula |
  | --- | --- |
  | `origin_balance_change` | `oldbalanceOrg - newbalanceOrig` |
  | `destination_balance_change` | `newbalanceDest - oldbalanceDest` |
  | `origin_error` | `newbalanceOrig + amount - oldbalanceOrg` |
  | `destination_error` | `oldbalanceDest + amount - newbalanceDest` |
  | `amount_to_origin_balance` | `amount / (oldbalanceOrg + 1)` |
  | `amount_to_destination_balance` | `amount / (oldbalanceDest + 1)` |

  The first four were confirmed against the means stored inside the scaler, which match
  these formulas exactly.

* **Random Forest and XGBoost get raw features; Logistic Regression gets scaled features.**
  The tree models' split thresholds are in amount units (for example `amount < 454881.65`),
  which means they were trained before scaling. Scaling them anyway pushes a normal payment
  from 0.00 to 0.46, so this distinction matters.

* `type` is one-hot encoded into `type_CASH_IN … type_TRANSFER`.

Sanity check on known PaySim patterns:

| Transaction | RF | XGB | LR |
| --- | --- | --- | --- |
| TRANSFER emptying the account | 1.00 | 1.00 | 0.999 |
| CASH_OUT of the full balance | 0.93 | 1.00 | 0.999 |
| Small retail PAYMENT | 0.00 | 0.00 | 0.00 |
| CASH_IN deposit | 0.00 | 0.00 | 0.00 |

The active model is set by `ML_MODEL_NAME` in `.env` (default `xgboost`).

### Member 4 — AML module (`app/services/aml_service.py`)

Member 4's package is imported unchanged; the folder is added to `sys.path` rather than
copied, so their code stays in their folder. The service only does the translation work:

* Maps database columns to their field names (`name_orig → sender_id`, and so on).
* Formats timestamps as `%Y/%m/%d %H:%M`, which is the **only** format their
  `rules.py` parser accepts — other formats make every time-based rule silently skip.
* Loads the sender's previous transactions from PostgreSQL and passes them as
  `transaction_history`. Without this, their behaviour and network analysis has nothing
  to compare against and every transaction looks like a first-time customer.

Their `analyze_aml()` returns the AML score, rule/behaviour/network sub-scores, triggered
rules, reasons, an investigation summary and a notification payload. All of it is stored
in the `risk_results` table.

### Member 1 — hybrid score (`app/risk.py`)

```
final_risk_score = 0.6 × ml_fraud_score + 0.4 × aml_score

HIGH   >= 0.70
MEDIUM >= 0.40
LOW     < 0.40
```

Weights are in `.env` (`ML_WEIGHT`, `AML_WEIGHT`). The thresholds match the ones Member 4
uses, so the two scores stay comparable. If one side is unavailable the other is used on
its own, so a transaction is never scored 0 just because a model failed to load.

An alert is created automatically whenever the level is **not** LOW.

---

## 4. Request flow

```
POST /api/transactions
        |
        v
  save transaction (PostgreSQL)
        |
        +--> Member 2: build 18 features -> predict_proba -> ml_fraud_score
        |                                -> SHAP TreeExplainer -> top features
        |
        +--> Member 4: load sender history -> analyze_aml() -> aml_score,
        |                                     rules, behaviour, network, reasons
        v
  hybrid score -> risk level -> alert if not LOW
        |
        v
  audit log entry -> response
```

---

## 5. API endpoints

### Authentication
| Method | Path | Roles | Description |
| --- | --- | --- | --- |
| POST | `/api/auth/register` | public | Create an account (ADMIN role is blocked) |
| POST | `/api/auth/login` | public | Get a JWT |
| GET | `/api/auth/me` | any | Current user profile |

### Transactions
| Method | Path | Roles | Description |
| --- | --- | --- | --- |
| POST | `/api/transactions` | any | Submit and analyse a transaction |
| GET | `/api/transactions` | any | List (customers see only their own) |
| GET | `/api/transactions/{id}` | any | Detail with risk breakdown |
| GET | `/api/transactions/{id}/explanation` | staff | SHAP explanation |
| POST | `/api/transactions/{id}/reanalyse` | ANALYST, ADMIN | Score again |

### Alerts
| Method | Path | Roles |
| --- | --- | --- |
| GET | `/api/alerts` | ANALYST, COMPLIANCE, ADMIN |
| GET | `/api/alerts/{id}` | ANALYST, COMPLIANCE, ADMIN |
| PATCH | `/api/alerts/{id}/status` | ANALYST, ADMIN |

### Cases
| Method | Path | Roles |
| --- | --- | --- |
| POST | `/api/cases` | ANALYST, ADMIN |
| GET | `/api/cases` | ANALYST, COMPLIANCE, ADMIN |
| GET | `/api/cases/{id}` | ANALYST, COMPLIANCE, ADMIN |
| PATCH | `/api/cases/{id}` | ANALYST, ADMIN |
| POST | `/api/cases/{id}/notes` | ANALYST, ADMIN |

### Analytics and administration
| Method | Path | Roles |
| --- | --- | --- |
| GET | `/api/analytics/summary` | ANALYST, COMPLIANCE, ADMIN |
| GET | `/api/admin/users` | ADMIN |
| PATCH | `/api/admin/users/{id}/role` | ADMIN |
| GET | `/api/admin/audit-logs` | ADMIN, COMPLIANCE |
| GET | `/api/admin/aml-rules` | ADMIN, COMPLIANCE |
| GET | `/api/admin/ml-models` | ADMIN, COMPLIANCE |

---

## 6. Database tables

| Table | Purpose |
| --- | --- |
| `users` | Accounts, hashed passwords, role |
| `transactions` | PaySim fields for ML + sender/receiver fields for AML |
| `risk_results` | ML score, SHAP features, AML sub-scores, hybrid score |
| `alerts` | Created automatically for MEDIUM and HIGH risk |
| `cases` | Investigation cases |
| `case_notes` | Notes added by investigators |
| `audit_logs` | Audit trail of important actions |

Tables are created automatically at startup by `Base.metadata.create_all()`. Alembic is
not used because the schema is fixed for this prototype.

---

## 7. Testing

```bash
pytest -v
```

18 tests cover registration, login, JWT rejection, all four RBAC roles, fraud and normal
scoring, the AML rule output, SHAP, the case workflow and the audit log. They run against
a temporary SQLite file so your PostgreSQL data is untouched.

For a scripted walkthrough during the demo, run the server and then:

```bash
python demo.py
```

---

## 8. Security notes

* Passwords hashed with bcrypt; the plain password is never stored.
* JWT is signed with `SECRET_KEY` and expires after `ACCESS_TOKEN_EXPIRE_MINUTES`.
* RBAC is enforced by the `require_roles()` dependency on each route.
* A customer can only read back their own transactions.
* Self-registration cannot grant the ADMIN role.
* Pydantic validates every request body.
* Login successes and failures, transaction analysis, case changes and role changes are
  all written to `audit_logs`.

---

## 9. Status and what is left

**Done:** authentication, JWT, RBAC, transaction APIs, ML integration, SHAP, AML
integration, hybrid scoring, alerts, cases and notes, audit logging, analytics, Swagger
docs, tests.

**Frontend:** built and working in `../member3_frontend`. It calls this API through a Vite
proxy, so CORS does not come into it during development; the CORS settings here are kept
for the case where the frontend is served separately.

**Not in this prototype:** real email/SMS sending (Member 4's module builds the payload
but does not send), the account relationship graph endpoint, and the real-time simulator.
