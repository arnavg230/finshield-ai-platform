import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { Notice, PageHead } from "../components/Bits";

const BLANK = {
  step: 1,
  type: "TRANSFER",
  amount: "",
  nameOrig: "",
  oldbalanceOrg: "",
  newbalanceOrig: "",
  nameDest: "",
  oldbalanceDest: "",
  newbalanceDest: "",
};

// Filling eight balance fields by hand during a demo is slow, so two known
// PaySim shapes are one click away.
const PRESETS = {
  "Suspicious transfer": {
    step: 7,
    type: "TRANSFER",
    amount: 181000,
    nameOrig: "C1231006815",
    oldbalanceOrg: 181000,
    newbalanceOrig: 0,
    nameDest: "C1666544295",
    oldbalanceDest: 0,
    newbalanceDest: 0,
  },
  "Routine payment": {
    step: 1,
    type: "PAYMENT",
    amount: 9839.64,
    nameOrig: "C1231006815",
    oldbalanceOrg: 170136,
    newbalanceOrig: 160296.36,
    nameDest: "M1979787155",
    oldbalanceDest: 0,
    newbalanceDest: 0,
  },
};

export default function SubmitTransaction() {
  const navigate = useNavigate();
  const [form, setForm] = useState(BLANK);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  function update(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      const payload = {
        step: Number(form.step),
        type: form.type,
        amount: Number(form.amount),
        nameOrig: form.nameOrig,
        oldbalanceOrg: Number(form.oldbalanceOrg || 0),
        newbalanceOrig: Number(form.newbalanceOrig || 0),
        nameDest: form.nameDest,
        oldbalanceDest: Number(form.oldbalanceDest || 0),
        newbalanceDest: Number(form.newbalanceDest || 0),
      };
      const result = await api.submitTransaction(payload);
      navigate(`/transactions/${result.transaction.id}`);
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  }

  return (
    <>
      <PageHead
        title="Submit a transaction"
        subtitle="The fraud model and the laundering rules run as soon as you save."
      >
        {Object.keys(PRESETS).map((name) => (
          <button
            key={name}
            className="btn ghost"
            onClick={() => setForm({ ...BLANK, ...PRESETS[name] })}
          >
            {name}
          </button>
        ))}
      </PageHead>

      <Notice bad>{error}</Notice>

      <div className="panel">
        <form className="form-body" onSubmit={handleSubmit}>
          <div className="field-grid">
            <label>
              <span className="caption">Type</span>
              <select value={form.type} onChange={(e) => update("type", e.target.value)}>
                {["TRANSFER", "CASH_OUT", "CASH_IN", "PAYMENT", "DEBIT"].map((type) => (
                  <option key={type} value={type}>
                    {type.replace("_", " ").toLowerCase()}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span className="caption">Amount</span>
              <input
                type="number"
                step="0.01"
                value={form.amount}
                onChange={(e) => update("amount", e.target.value)}
                required
              />
            </label>
            <label>
              <span className="caption">Hour of the simulation</span>
              <input
                type="number"
                min="1"
                value={form.step}
                onChange={(e) => update("step", e.target.value)}
              />
            </label>
          </div>

          <div className="field-grid">
            <label>
              <span className="caption">Sender account</span>
              <input
                value={form.nameOrig}
                onChange={(e) => update("nameOrig", e.target.value)}
                required
              />
            </label>
            <label>
              <span className="caption">Sender balance before</span>
              <input
                type="number"
                step="0.01"
                value={form.oldbalanceOrg}
                onChange={(e) => update("oldbalanceOrg", e.target.value)}
              />
            </label>
            <label>
              <span className="caption">Sender balance after</span>
              <input
                type="number"
                step="0.01"
                value={form.newbalanceOrig}
                onChange={(e) => update("newbalanceOrig", e.target.value)}
              />
            </label>
          </div>

          <div className="field-grid">
            <label>
              <span className="caption">Receiver account</span>
              <input
                value={form.nameDest}
                onChange={(e) => update("nameDest", e.target.value)}
                required
              />
            </label>
            <label>
              <span className="caption">Receiver balance before</span>
              <input
                type="number"
                step="0.01"
                value={form.oldbalanceDest}
                onChange={(e) => update("oldbalanceDest", e.target.value)}
              />
            </label>
            <label>
              <span className="caption">Receiver balance after</span>
              <input
                type="number"
                step="0.01"
                value={form.newbalanceDest}
                onChange={(e) => update("newbalanceDest", e.target.value)}
              />
            </label>
          </div>

          <button className="btn" type="submit" disabled={busy}>
            {busy ? "Screening…" : "Screen this transaction"}
          </button>
        </form>
      </div>
    </>
  );
}
