import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import { STAFF, useAuth } from "../auth";
import { Empty, Money, Notice, PageHead, Score, formatDate } from "../components/Bits";

// Member 2's models use PaySim column names. These are the same things said
// in words an investigator can read.
const FEATURE_LABELS = {
  step: "Hour the transaction happened",
  amount: "Amount moved",
  oldbalanceOrg: "Sender balance before",
  newbalanceOrig: "Sender balance after",
  oldbalanceDest: "Receiver balance before",
  newbalanceDest: "Receiver balance after",
  isFlaggedFraud: "Already flagged by the bank",
  origin_balance_change: "Drop in the sender's balance",
  destination_balance_change: "Rise in the receiver's balance",
  origin_error: "Sender's balance does not add up",
  destination_error: "Receiver's balance does not add up",
  amount_to_origin_balance: "Amount against the sender's balance",
  amount_to_destination_balance: "Amount against the receiver's balance",
  type_CASH_IN: "Is a cash deposit",
  type_CASH_OUT: "Is a cash withdrawal",
  type_DEBIT: "Is a debit",
  type_PAYMENT: "Is a payment",
  type_TRANSFER: "Is a transfer",
};

function ShapChart({ features }) {
  const largest = Math.max(...features.map((f) => Math.abs(f.shap_value)), 0.0001);
  return (
    <>
      <div className="shap">
        {features.map((feature) => {
          const width = (Math.abs(feature.shap_value) / largest) * 50;
          const pushesUp = feature.shap_value > 0;
          return (
            <div className="shap-row" key={feature.feature}>
              <div className="shap-name" title={feature.feature}>
                {FEATURE_LABELS[feature.feature] || feature.feature}
                <span className="shap-raw">{feature.feature}</span>
              </div>
              <div className="shap-track">
                <div
                  className={`shap-bar ${pushesUp ? "up" : "down"}`}
                  style={{ width: `${width}%` }}
                />
              </div>
              <div className="shap-val">{feature.shap_value.toFixed(3)}</div>
            </div>
          );
        })}
      </div>
      <p className="shap-legend">
        Bars to the right pushed the model towards fraud, bars to the left pushed it
        away. Length shows how strongly each value mattered.
      </p>
    </>
  );
}

export default function TransactionDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const isStaff = STAFF.includes(user.role);

  const [data, setData] = useState(null);
  const [explanation, setExplanation] = useState(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  async function load() {
    try {
      const detail = await api.transaction(id);
      setData(detail);
      if (STAFF.includes(user.role)) {
        setExplanation(await api.explanation(id));
      }
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    load();
  }, [id]);

  async function openCase() {
    try {
      const created = await api.createCase({
        transaction_id: Number(id),
        title: `Review of ${data.transaction.txn_ref}`,
        priority: data.risk.risk_level === "HIGH" ? "HIGH" : "MEDIUM",
      });
      navigate(`/cases/${created.id}`);
    } catch (err) {
      setError(err.message);
    }
  }

  async function rerun() {
    setMessage("");
    try {
      await api.reanalyse(id);
      setMessage("Scored again with the latest history.");
      load();
    } catch (err) {
      setError(err.message);
    }
  }

  if (error) return <Notice bad>{error}</Notice>;
  if (!data) return <Empty>Loading the transaction…</Empty>;

  const { transaction, risk } = data;

  return (
    <>
      <PageHead
        title={transaction.txn_ref}
        subtitle={`${transaction.txn_type.replace("_", " ").toLowerCase()} recorded ${formatDate(
          transaction.timestamp
        )}`}
      >
        <button className="btn ghost" onClick={() => navigate(-1)}>
          Back
        </button>
        {["ANALYST", "ADMIN"].includes(user.role) && (
          <>
            <button className="btn ghost" onClick={rerun}>
              Score again
            </button>
            <button className="btn" onClick={openCase}>
              Open a case
            </button>
          </>
        )}
      </PageHead>

      {message && <div className="notice">{message}</div>}

      <div className={`verdict risk-${risk.risk_level}`}>
        <div className="verdict-score">
          <div className="big">{risk.final_risk_score.toFixed(2)}</div>
          <div className={`lvl level-${risk.risk_level}`}>{risk.risk_level} risk</div>
        </div>
        <div className="breakdown">
          <div>
            <div className="label">Fraud model</div>
            <div className="value">
              <Score value={risk.ml_fraud_score} />
            </div>
          </div>
          <div>
            <div className="label">Laundering</div>
            <div className="value">
              <Score value={risk.aml_score} />
            </div>
          </div>
          <div>
            <div className="label">Rules</div>
            <div className="value">
              <Score value={risk.rule_score} />
            </div>
          </div>
          <div>
            <div className="label">Behaviour</div>
            <div className="value">
              <Score value={risk.behavior_score} />
            </div>
          </div>
          <div>
            <div className="label">Account network</div>
            <div className="value">
              <Score value={risk.network_score} />
            </div>
          </div>
        </div>
      </div>

      <div className="panel">
        <h2>Transaction</h2>
        <table>
          <tbody>
            <tr>
              <td className="dim">Amount</td>
              <td>
                <Money value={transaction.amount} /> {transaction.currency}
              </td>
            </tr>
            <tr>
              <td className="dim">Sender</td>
              <td className="num">
                {transaction.name_orig} &nbsp;
                <span className="dim">
                  {transaction.oldbalance_org} → {transaction.newbalance_orig}
                </span>
              </td>
            </tr>
            <tr>
              <td className="dim">Receiver</td>
              <td className="num">
                {transaction.name_dest} &nbsp;
                <span className="dim">
                  {transaction.oldbalance_dest} → {transaction.newbalance_dest}
                </span>
              </td>
            </tr>
            <tr>
              <td className="dim">Model verdict</td>
              <td>
                {risk.ml_prediction === 1 ? "Flagged as fraud" : "Not flagged"}
                <span className="dim"> · {risk.ml_model_used || "no model"}</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      {risk.triggered_rules && risk.triggered_rules.length > 0 && (
        <div className="panel">
          <h2>Laundering rules that fired</h2>
          <div style={{ padding: "14px 18px 8px" }}>
            {risk.triggered_rules.map((rule) => (
              <span className="rule-chip" key={rule}>
                {rule.replace(/_/g, " ").toLowerCase()}
              </span>
            ))}
          </div>
        </div>
      )}

      {risk.reasons && risk.reasons.length > 0 && (
        <div className="panel">
          <h2>Why this was flagged</h2>
          <ul className="reasons">
            {risk.reasons.map((reason) => (
              <li key={reason}>{reason}</li>
            ))}
          </ul>
        </div>
      )}

      {isStaff && explanation && (
        <div className="panel">
          <h2>What the model looked at</h2>
          {explanation.available ? (
            <ShapChart features={explanation.top_features} />
          ) : (
            <Empty>
              No explanation available for this transaction. {explanation.error || ""}
            </Empty>
          )}
        </div>
      )}

      {isStaff && risk.investigation_summary && (
        <div className="panel">
          <h2>Suggested next steps</h2>
          <ul className="reasons">
            {(risk.investigation_summary.investigation_steps || []).map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ul>
          <p className="shap-legend">{risk.investigation_summary.disclaimer}</p>
        </div>
      )}
    </>
  );
}
