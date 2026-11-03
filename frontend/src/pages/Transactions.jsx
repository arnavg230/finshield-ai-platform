import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { useAuth, STAFF } from "../auth";
import { Empty, Money, Notice, PageHead, formatDate } from "../components/Bits";

export default function Transactions() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [rows, setRows] = useState([]);
  const [level, setLevel] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    const query = level ? `?risk_level=${level}` : "";
    api
      .transactions(query)
      .then(setRows)
      .catch((err) => setError(err.message));
  }, [level]);

  return (
    <>
      <PageHead
        title="Transactions"
        subtitle={
          STAFF.includes(user.role)
            ? "Everything that has been screened."
            : "The transactions you have submitted."
        }
      >
        <select value={level} onChange={(e) => setLevel(e.target.value)}>
          <option value="">All risk levels</option>
          <option value="HIGH">High only</option>
          <option value="MEDIUM">Medium only</option>
          <option value="LOW">Low only</option>
        </select>
        <button className="btn" onClick={() => navigate("/submit")}>
          Submit a transaction
        </button>
      </PageHead>

      <Notice bad>{error}</Notice>

      <div className="panel">
        {rows.length === 0 ? (
          <Empty>No transactions match this filter yet.</Empty>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Reference</th>
                <th>Type</th>
                <th>Amount</th>
                <th>From</th>
                <th>To</th>
                <th>Recorded</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr
                  key={row.id}
                  className="clickable"
                  onClick={() => navigate(`/transactions/${row.id}`)}
                >
                  <td className="num">{row.txn_ref}</td>
                  <td className="dim">{row.txn_type.replace("_", " ").toLowerCase()}</td>
                  <td>
                    <Money value={row.amount} />
                  </td>
                  <td className="num">{row.name_orig}</td>
                  <td className="num">{row.name_dest}</td>
                  <td className="dim num">{formatDate(row.timestamp)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}
