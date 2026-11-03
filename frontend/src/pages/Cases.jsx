import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { Empty, Notice, PageHead, formatDate } from "../components/Bits";

export default function Cases() {
  const navigate = useNavigate();
  const [rows, setRows] = useState([]);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    const query = status ? `?status=${status}` : "";
    api
      .cases(query)
      .then(setRows)
      .catch((err) => setError(err.message));
  }, [status]);

  return (
    <>
      <PageHead title="Cases" subtitle="Investigations opened from the alert queue.">
        <select value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">All cases</option>
          <option value="OPEN">Open</option>
          <option value="IN_PROGRESS">In progress</option>
          <option value="CLOSED">Closed</option>
        </select>
      </PageHead>

      <Notice bad>{error}</Notice>

      <div className="panel">
        {rows.length === 0 ? (
          <Empty>
            No cases yet. Open one from a flagged transaction to start an investigation.
          </Empty>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Reference</th>
                <th>Title</th>
                <th>Priority</th>
                <th>Status</th>
                <th>Opened</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr
                  key={row.id}
                  className="clickable"
                  onClick={() => navigate(`/cases/${row.id}`)}
                >
                  <td className="num">{row.case_ref}</td>
                  <td>{row.title}</td>
                  <td className="dim">{row.priority.toLowerCase()}</td>
                  <td className="dim">{row.status.replace("_", " ").toLowerCase()}</td>
                  <td className="dim num">{formatDate(row.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}
