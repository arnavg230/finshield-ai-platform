# FinShield AI — Member 3: Frontend & Investigation

React console for the FinShield AI platform, built with Vite.

## Run it

The backend must already be running on port 8000.

```bash
cd member3_frontend
npm install
npm run dev
```

Open <http://localhost:5173>.

Vite proxies `/api` and `/health` to `http://127.0.0.1:8000` (see `vite.config.js`), so
the app uses plain relative URLs and there is no CORS setup to worry about. If your
backend runs on a different port, change the proxy target there.

## Screens

| Route | Who can open it | What it shows |
| --- | --- | --- |
| `/login` | everyone | Sign in; demo account buttons fill the form |
| `/` | analyst, compliance, admin | Counts, the highest risk alerts, engine status |
| `/transactions` | everyone | Transaction list; customers see only their own |
| `/transactions/:id` | everyone | Risk breakdown, rules, reasons, SHAP chart |
| `/submit` | everyone | Submit a transaction for screening |
| `/alerts` | analyst, compliance, admin | Alert queue sorted by risk |
| `/cases` `/cases/:id` | analyst, compliance, admin | Cases, notes, outcome |
| `/admin` | admin, compliance | Users, rule thresholds, activity record |

## How it is put together

```
src/
├── api.js                  all fetch calls and token storage
├── auth.jsx                sign-in state shared through React context
├── App.jsx                 routes and the role check on each one
├── styles.css              one stylesheet
├── components/
│   ├── Layout.jsx          sidebar and page frame
│   └── Bits.jsx            small shared pieces
└── pages/                  one file per screen
```

The JWT is kept in `localStorage` and attached to every request by `api.js`. If the
backend answers 401 the session is cleared and the user is sent back to sign-in.

`App.jsx` hides screens a role is not allowed to open, and `Layout.jsx` hides the links.
This is only for tidiness — the backend enforces the real rules, so changing the role in
the browser does not grant access to anything.

## Design notes

The interface is deliberately monochrome. The only saturated colour on a screen comes
from risk: crimson for high, ochre for medium, pine for low. An analyst can read severity
from the coloured edge of a row without reading the label. Amounts, account numbers and
scores are set in a monospace face so columns of figures line up when scanning.

The SHAP chart draws bars from a centre line: to the right means that value pushed the
model towards fraud, to the left means it pushed away, and length is how much it mattered.
Each feature shows a plain-English name with Member 2's actual column name underneath.

## Not built yet

The account relationship graph. The backend does not expose a graph endpoint yet, so this
was left out rather than faked.
