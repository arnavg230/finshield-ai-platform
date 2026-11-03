import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth";

// Shown next to the form so the sign-in screen opens with the thing the
// product actually does: scored transactions, worst first.
const SAMPLE_LEDGER = [
  { ref: "TXN-8F42A1", party: "C1231006815 > C1666544295", level: "HIGH", score: "0.91" },
  { ref: "TXN-2C90E7", party: "C1305486145 > C1590550415", level: "HIGH", score: "0.78" },
  { ref: "TXN-55B310", party: "C0442918153 > C0997608398", level: "MEDIUM", score: "0.52" },
  { ref: "TXN-A7D004", party: "C1231006815 > M1979787155", level: "LOW", score: "0.07" },
  { ref: "TXN-19E663", party: "C2048537720 > M0553264065", level: "LOW", score: "0.04" },
];

const DEMO_ACCOUNTS = [
  ["admin", "Admin@123"],
  ["analyst", "Analyst@123"],
  ["officer", "Officer@123"],
  ["customer", "Customer@123"],
];

export default function Login() {
  const { signIn } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      const session = await signIn(username, password);
      navigate(session.role === "CUSTOMER" ? "/transactions" : "/");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  function useDemoAccount(name, pass) {
    setUsername(name);
    setPassword(pass);
  }

  return (
    <div className="login">
      <section className="login-visual">
        <h1>Every transaction, scored and explained.</h1>
        <p>
          Fraud models and money-laundering rules run on the same queue, so an
          investigator sees one risk score and the reasons behind it.
        </p>
        <div className="ledger">
          {SAMPLE_LEDGER.map((row) => (
            <div key={row.ref} className={`ledger-row r-${row.level}`}>
              <span>{row.party}</span>
              <span>{row.ref}</span>
              <span className="s">{row.score}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="login-form">
        <h2>Sign in</h2>
        <p>Use your FinShield account.</p>

        {error && <div className="notice bad">{error}</div>}

        <form onSubmit={handleSubmit}>
          <label>
            <span className="caption">Username</span>
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              required
            />
          </label>
          <label>
            <span className="caption">Password</span>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
          </label>
          <button className="btn" type="submit" disabled={busy}>
            {busy ? "Signing in…" : "Sign in"}
          </button>
        </form>

        <div className="demo-users">
          Demo accounts for the review:
          <div>
            {DEMO_ACCOUNTS.map(([name, pass]) => (
              <button key={name} onClick={() => useDemoAccount(name, pass)}>
                {name}
              </button>
            ))}
          </div>
        </div>

      </section>
    </div>
  );
}
