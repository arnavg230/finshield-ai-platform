import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { Empty, Level, Money, Notice, PageHead, Score, formatDate } from "../components/Bits";

export default function Dashboard() {
  const navigate = useNavigate();
  const [summary, setSummary] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [health, setHealth] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      try {
        const [summaryData, alertData] = await Promise.all([
          api.summary(),
          api.alerts("?limit=8"),
        ]);
        setSummary(summaryData);
        setAlerts(alertData);
        const healthResponse = await fetch("/health");
        setHealth(await healthResponse.json());
      } catch (err) {
        setError(err.message);
      }
    }
    load();
  }, []);

  return (
    <>
      <PageHead
        title="Overview"
        subtitle="Monitoring activity across the whole transaction queue."
      />
      <Notice bad>{error}</Notice>

      {summary && (
        <div className="stats">
          <div className="stat">
            <div className="label">Transactions screened</div>
            <div className="figure">{summary.total_transactions}</div>
          </div>
          <div className="stat">
            <div className="label">High risk alerts</div>
            <div className="figure">{summary.alerts_by_level.HIGH}</div>
          </div>
          <div className="stat">
            <div className="label">Medium risk alerts</div>
            <div className="figure">{summary.alerts_by_level.MEDIUM}</div>
          </div>
          <div className="stat">
            <div className="label">Alerts awaiting review</div>
            <div className="figure">{summary.open_alerts}</div>
          </div>
          <div className="stat">
            <div className="label">Flagged by the model</div>
            <div className="figure">{summary.ml_flagged_count}</div>
          </div>
          <div className="stat">
            <div className="label">Average risk score</div>
            <div className="figure">{summary.average_risk_score.toFixed(3)}</div>
          </div>
        </div>
      )}

      <div className="panel">
        <h2>Highest risk alerts</h2>
        {alerts.length === 0 ? (
          <Empty>
            Nothing has been flagged yet. Submit a transaction to see the queue fill up.
          </Empty>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Level</th>
                <th>Score</th>
                <th>Why it was raised</th>
                <th>Status</th>
                <th>Raised</th>
              </tr>
            </thead>
            <tbody>
              {alerts.map((alert) => (
                <tr
                  key={alert.id}
                  className={`clickable risk-${alert.risk_level}`}
                  onClick={() => navigate(`/transactions/${alert.transaction_id}`)}
                >
                  <td className="edge">
                    <Level value={alert.risk_level} />
                  </td>
                  <td>
                    <Score value={alert.final_risk_score} />
                  </td>
                  <td>{alert.message}</td>
                  <td className="dim">{alert.status.replace("_", " ").toLowerCase()}</td>
                  <td className="dim num">{formatDate(alert.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {summary && (
        <div className="panel">
          <h2>Case workload</h2>
          <table>
            <tbody>
              {Object.entries(summary.cases_by_status).map(([status, count]) => (
                <tr key={status}>
                  <td>{status.replace("_", " ").toLowerCase()}</td>
                  <td className="num">{count}</td>
                </tr>
              ))}
              <tr>
                <td>Total value screened</td>
                <td>
                  <Money value={summary.total_amount} />
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      )}

      {health && (
        <div className="panel">
          <h2>Detection engines</h2>
          <table>
            <tbody>
              <tr>
                <td>Fraud models loaded</td>
                <td className="num">{health.ml_models_loaded.join(", ") || "none"}</td>
              </tr>
              <tr>
                <td>Model in use</td>
                <td className="num">{health.ml_active_model}</td>
              </tr>
              <tr>
                <td>Money laundering engine</td>
                <td className="num">
                  {health.aml_module_available ? "running" : "unavailable"}
                </td>
              </tr>
              <tr>
                <td>Score weighting</td>
                <td className="num">
                  fraud {health.hybrid_weights.ml} / laundering {health.hybrid_weights.aml}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
