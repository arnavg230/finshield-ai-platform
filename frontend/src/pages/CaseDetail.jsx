import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import { Empty, Notice, PageHead, formatDate } from "../components/Bits";

export default function CaseDetail() {
  const { id } = useParams();
  const { user } = useAuth();
  const [record, setRecord] = useState(null);
  const [note, setNote] = useState("");
  const [resolution, setResolution] = useState("");
  const [error, setError] = useState("");

  function load() {
    api
      .caseDetail(id)
      .then((data) => {
        setRecord(data);
        setResolution(data.resolution || "");
      })
      .catch((err) => setError(err.message));
  }

  useEffect(load, [id]);

  async function addNote(event) {
    event.preventDefault();
    if (!note.trim()) return;
    try {
      await api.addCaseNote(id, note);
      setNote("");
      load();
    } catch (err) {
      setError(err.message);
    }
  }

  async function changeStatus(status) {
    try {
      await api.updateCase(id, { status, resolution: resolution || undefined });
      load();
    } catch (err) {
      setError(err.message);
    }
  }

  if (error) return <Notice bad>{error}</Notice>;
  if (!record) return <Empty>Loading the case…</Empty>;

  const canEdit = ["ANALYST", "ADMIN"].includes(user.role);
  const isClosed = record.status === "CLOSED";

  return (
    <>
      <PageHead
        title={record.case_ref}
        subtitle={`${record.title} · ${record.status.replace("_", " ").toLowerCase()}`}
      >
        <Link className="btn ghost" to={`/transactions/${record.transaction_id}`}>
          View the transaction
        </Link>
        {canEdit && !isClosed && (
          <>
            {record.status === "OPEN" && (
              <button className="btn ghost" onClick={() => changeStatus("IN_PROGRESS")}>
                Start work
              </button>
            )}
            <button className="btn" onClick={() => changeStatus("CLOSED")}>
              Close the case
            </button>
          </>
        )}
      </PageHead>

      <div className="panel">
        <h2>Case file</h2>
        <table>
          <tbody>
            <tr>
              <td className="dim">Priority</td>
              <td>{record.priority.toLowerCase()}</td>
            </tr>
            <tr>
              <td className="dim">Opened</td>
              <td className="num">{formatDate(record.created_at)}</td>
            </tr>
            <tr>
              <td className="dim">Closed</td>
              <td className="num">{record.closed_at ? formatDate(record.closed_at) : "—"}</td>
            </tr>
            <tr>
              <td className="dim">Outcome</td>
              <td>{record.resolution || "Not recorded yet"}</td>
            </tr>
          </tbody>
        </table>
      </div>

      {canEdit && !isClosed && (
        <div className="panel">
          <h2>Outcome</h2>
          <div className="form-body">
            <label>
              <span className="caption">
                What did the investigation find? Saved when you close the case.
              </span>
              <textarea
                rows="2"
                value={resolution}
                onChange={(e) => setResolution(e.target.value)}
              />
            </label>
          </div>
        </div>
      )}

      <div className="panel">
        <h2>Investigation notes</h2>
        {record.notes.length === 0 ? (
          <Empty>No notes yet. Record what you check as you go.</Empty>
        ) : (
          <ul className="reasons">
            {record.notes.map((entry) => (
              <li key={entry.id}>
                {entry.note}
                <div className="dim num" style={{ fontSize: 12, marginTop: 3 }}>
                  {formatDate(entry.created_at)}
                </div>
              </li>
            ))}
          </ul>
        )}

        {canEdit && !isClosed && (
          <form className="form-body" onSubmit={addNote}>
            <label>
              <span className="caption">Add a note</span>
              <textarea
                rows="2"
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="Checked the sender's history for the last 30 days."
              />
            </label>
            <button className="btn" type="submit">
              Save the note
            </button>
          </form>
        )}
      </div>
    </>
  );
}
