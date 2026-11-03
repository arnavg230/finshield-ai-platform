import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import { Empty, Level, Notice, PageHead, Score, formatDate } from "../components/Bits";

export default function Alerts() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [rows, setRows] = useState([]);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");

  function load() {
    const query = status ? `?status=${status}` : "";
    api
      .alerts(query)
      .then(setRows)
      .catch((err) => setError(err.message));
  }

  useEffect(load, [status]);

  async function setAlertStatus(event, id, next) {
    event.stopPropagation();
    try {
      await api.updateAlertStatus(id, next);
      load();
    } catch (err) {
      setError(err.message);
    }
  }

  const canEdit = ["ANALYST", "ADMIN"].includes(user.role);

  return (
    <>
      <PageHead
        title="Alert queue"
        subtitle="Sorted by risk, so the worst transactions are handled first."
      >
        <select value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">All alerts</option>
          <option value="OPEN">Awaiting review</option>
          <option value="IN_REVIEW">Being reviewed</option>
          <option value="CLOSED">Closed</option>
        </select>
      </PageHead>

      <Notice bad>{error}</Notice>

      <div className="panel">
        {rows.length === 0 ? (
          <Empty>The queue is clear. Nothing needs review right now.</Empty>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Level</th>
                <th>Score</th>
                <th>Why it was raised</th>
                <th>Status</th>
                <th>Raised</th>
                {canEdit && <th />}
              </tr>
            </thead>
            <tbody>
              {rows.map((alert) => (
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
                  {canEdit && (
                    <td>
                      {alert.status !== "CLOSED" && (
                        <button
                          className="btn ghost"
                          onClick={(e) =>
                            setAlertStatus(
                              e,
                              alert.id,
                              alert.status === "OPEN" ? "IN_REVIEW" : "CLOSED"
                            )
                          }
                        >
                          {alert.status === "OPEN" ? "Start review" : "Close"}
                        </button>
                      )}
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}
