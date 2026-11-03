import { useState } from "react";
import { api } from "../api";

export default function AMLTesting() {
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const runTests = async () => {
    setLoading(true);
    setError("");
    setMessage("");
    setResults([]);

    try {
      const response = await api.runAmlTests();
      setResults(response.results || []);
      setMessage(response.message || "Tests completed.");
    } catch (err) {
      setError(err.message || "Unable to run AML tests.");
    } finally {
      setLoading(false);
    }
  };

  const formatScore = (score) =>
    `${(Number(score || 0) * 100).toFixed(2)}%`;

  const riskColor = (level) => {
    if (level === "HIGH") return "#dc2626";
    if (level === "MEDIUM") return "#d97706";
    return "#16a34a";
  };

  return (
    <div style={{ padding: "24px", maxWidth: "1100px", margin: "0 auto" }}>
      <h1>AML Scenario Testing</h1>
      <p>
        Run the 15 AML functional scenarios for thresholds, behaviour,
        transaction frequency, and account networks. Test records are rolled back.
      </p>

      <button
        onClick={runTests}
        disabled={loading}
        style={{
          padding: "12px 20px",
          border: "none",
          borderRadius: "8px",
          background: loading ? "#94a3b8" : "#2563eb",
          color: "white",
          cursor: loading ? "not-allowed" : "pointer",
          fontWeight: "bold",
        }}
      >
        {loading ? "Running tests..." : "Run All AML Tests"}
      </button>

      {message && (
        <p style={{ color: "#16a34a", marginTop: "16px" }}>
          {message}
        </p>
      )}

      {error && (
        <p style={{ color: "#dc2626", marginTop: "16px" }}>
          {error}
        </p>
      )}

      {results.length > 0 && (
        <>
          <h2 style={{ marginTop: "28px" }}>
            Results ({results.length}/15)
          </h2>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
              gap: "18px",
            }}
          >
            {results.map((item, index) => (
              <div
                key={`${item.scenario}-${index}`}
                style={{
                  border: "1px solid #d1d5db",
                  borderRadius: "12px",
                  padding: "18px",
                  background: "var(--card-bg, white)",
                }}
              >
                <h3>{item.scenario}</h3>
                <p>{item.description}</p>
                <p><strong>Amount:</strong> ${Number(item.transaction.amount).toLocaleString()}</p>

                <hr />

                <p><strong>ML Score:</strong> {formatScore(item.ml_score)}</p>
                <p><strong>ML Prediction:</strong> {item.ml_prediction}</p>
                <p>
                  <strong>AML Score:</strong> {formatScore(item.aml_score)}
                </p>
                <p>
                  <strong>AML Risk:</strong>{" "}
                  <span style={{ color: riskColor(item.aml_risk_level), fontWeight: "bold" }}>
                    {item.aml_risk_level}
                  </span>
                </p>
                <p><strong>Rule / Behaviour / Network:</strong>{" "}
                  {formatScore(item.rule_score)} / {formatScore(item.behavior_score)} / {formatScore(item.network_score)}
                </p>
                <p>
                  <strong>Hybrid Score:</strong> {formatScore(item.hybrid_score)}
                </p>
                <p>
                  <strong>Final Risk:</strong>{" "}
                  <span style={{ color: riskColor(item.hybrid_risk_level), fontWeight: "bold" }}>
                    {item.hybrid_risk_level}
                  </span>
                </p>

                <hr />

                <strong>Triggered Rules</strong>
                {item.triggered_rules?.length ? (
                  <ul>
                    {item.triggered_rules.map((rule) => (
                      <li key={rule}>{rule}</li>
                    ))}
                  </ul>
                ) : (
                  <p>None</p>
                )}

                <strong>Reasons</strong>
                {item.reasons?.length ? (
                  <ul>
                    {item.reasons.map((reason, i) => (
                      <li key={i}>{reason}</li>
                    ))}
                  </ul>
                ) : (
                  <p>No additional reasons.</p>
                )}

                {item.investigation_summary?.summary && (
                  <>
                    <strong>Investigation Summary</strong>
                    <p>{item.investigation_summary.summary}</p>
                  </>
                )}

                {item.aml_explanation && (
                  <details>
                    <summary>View Detailed AML Explanation</summary>
                    <pre style={{ whiteSpace: "pre-wrap", fontSize: "12px" }}>
                      {item.aml_explanation}
                    </pre>
                  </details>
                )}
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
