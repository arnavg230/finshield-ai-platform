import { useEffect, useState } from "react";
import { api } from "../api";
import { useAuth } from "../auth";
import { Empty, Notice, PageHead, formatDate } from "../components/Bits";

const ROLES = ["CUSTOMER", "ANALYST", "COMPLIANCE", "ADMIN"];

export default function Admin() {
  const { user } = useAuth();
  const isAdmin = user.role === "ADMIN";

  const [users, setUsers] = useState([]);
  const [logs, setLogs] = useState([]);
  const [rules, setRules] = useState(null);
  const [error, setError] = useState("");

  function load() {
    api
      .auditLogs("?limit=40")
      .then(setLogs)
      .catch((err) => setError(err.message));
    api.amlRules().then(setRules).catch(() => {});
    if (isAdmin) {
      api.users().then(setUsers).catch(() => {});
    }
  }

  useEffect(load, []);

  async function changeRole(id, role) {
    try {
      await api.changeRole(id, role);
      load();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <>
      <PageHead
        title="Administration"
        subtitle="Accounts, detection settings and the record of what everyone did."
      />
      <Notice bad>{error}</Notice>

      {isAdmin && (
        <div className="panel">
          <h2>People</h2>
          <table>
            <thead>
              <tr>
                <th>User</th>
                <th>Email</th>
                <th>Role</th>
                <th>Joined</th>
              </tr>
            </thead>
            <tbody>
              {users.map((person) => (
                <tr key={person.id}>
                  <td className="num">{person.username}</td>
                  <td className="dim">{person.email}</td>
                  <td>
                    <select
                      value={person.role}
                      onChange={(e) => changeRole(person.id, e.target.value)}
                    >
                      {ROLES.map((role) => (
                        <option key={role} value={role}>
                          {role.toLowerCase()}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td className="dim num">{formatDate(person.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {rules && (
        <div className="panel">
          <h2>Laundering rule thresholds</h2>
          <table>
            <tbody>
              {Object.entries(rules.thresholds).map(([key, value]) => (
                <tr key={key}>
                  <td>{key.replace(/_/g, " ")}</td>
                  <td className="num">{value}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="panel">
        <h2>Activity record</h2>
        {logs.length === 0 ? (
          <Empty>Nothing recorded yet.</Empty>
        ) : (
          <table>
            <thead>
              <tr>
                <th>User</th>
                <th>Action</th>
                <th>Record</th>
                <th>When</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log) => (
                <tr key={log.id}>
                  <td className="num">{log.username || "—"}</td>
                  <td>{log.action.replace(/_/g, " ").toLowerCase()}</td>
                  <td className="dim num">
                    {log.entity_type ? `${log.entity_type} ${log.entity_id}` : "—"}
                  </td>
                  <td className="dim num">{formatDate(log.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}
