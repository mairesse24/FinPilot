import { useEffect, useRef, useState } from "react";
import { AlertTriangle, ReceiptText, X } from "lucide-react";
import { post, type Account, type Alert } from "./api";

type Result = {
  mode: "simulation";
  executed: false;
  account_id: string;
  account_name: string;
  amount: number;
  balance_before: number;
  balance_after: number;
  total_liquid_before: number;
  total_liquid_after: number;
  account_share_percent: number;
  liquid_share_percent: number;
  alerts: Alert[];
};

const money = (value: number) =>
  value.toLocaleString("en-US", { style: "currency", currency: "USD" });

export default function LiveTransactionDemo({ accounts }: { accounts: Account[] }) {
  const eligible = accounts.filter((account) => ["checking", "savings"].includes(account.account_type));
  const dialog = useRef<HTMLDialogElement>(null);
  const [accountId, setAccountId] = useState(eligible[0]?.id ?? "");
  const [amount, setAmount] = useState("");
  const [description, setDescription] = useState("Judge demo purchase");
  const [result, setResult] = useState<Result | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!eligible.some((account) => account.id === accountId)) setAccountId(eligible[0]?.id ?? "");
  }, [accounts, accountId, eligible]);

  const open = () => {
    setResult(null);
    setError("");
    dialog.current?.showModal();
  };
  const close = () => dialog.current?.close();
  const run = async () => {
    const parsed = Number(amount);
    if (!Number.isFinite(parsed) || parsed <= 0) {
      setError("Enter a transaction amount greater than $0.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const next = await post<Result>("demo/transaction", {
        account_id: accountId,
        amount: parsed,
        description: description.trim() || "Synthetic purchase",
        category: "shopping",
      });
      setResult(next);
      if (next.alerts[0])
        window.dispatchEvent(new CustomEvent<Alert>("finpilot:demo-alert", { detail: next.alerts[0] }));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "The simulation could not run.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <button className="transaction-demo-trigger" onClick={open}>
        <ReceiptText size={17} /> Simulate live transaction
      </button>
      <dialog
        ref={dialog}
        className="transaction-dialog"
        aria-label="Live transaction simulator"
        onCancel={close}
        onClick={(event) => {
          if (event.target === event.currentTarget) close();
        }}
      >
        <div className="dialog-heading">
          <div>
            <span className="eyebrow">Judge demo · no money moves</span>
            <h2>Simulate a live transaction</h2>
          </div>
          <button aria-label="Close transaction simulator" onClick={close}><X size={17} /></button>
        </div>
        <p>
          Preview any purchase against an imported checking or savings balance. The backend evaluates
          the transaction, but it does not write to Nessie or change a bank account.
        </p>
        <div className="transaction-fields">
          <label>
            Funding account
            <select value={accountId} onChange={(event) => setAccountId(event.target.value)}>
              {eligible.map((account) => (
                <option value={account.id} key={account.id}>{account.name} · {money(account.balance)}</option>
              ))}
            </select>
          </label>
          <label>
            Purchase amount
            <input
              type="number"
              min="0.01"
              step="0.01"
              value={amount}
              onChange={(event) => setAmount(event.target.value)}
              placeholder="2500.00"
            />
          </label>
          <label className="transaction-description">
            Description
            <input value={description} maxLength={100} onChange={(event) => setDescription(event.target.value)} />
          </label>
        </div>
        <button className="run-transaction" disabled={busy || !eligible.length} onClick={() => void run()}>
          {busy ? "Evaluating…" : "Run transaction simulation"}
        </button>
        {error && <p className="form-error" role="alert">{error}</p>}
        {result && (
          <section className="transaction-result" aria-label="Transaction simulation result">
            <div className="transaction-balance-change">
              <span><small>Before</small><strong>{money(result.balance_before)}</strong></span>
              <span aria-hidden="true">→</span>
              <span><small>After</small><strong>{money(result.balance_after)}</strong></span>
            </div>
            <p>
              {money(result.amount)} uses {result.account_share_percent.toFixed(1)}% of this account
              and {result.liquid_share_percent.toFixed(1)}% of total checking and savings.
            </p>
            {result.alerts.length ? result.alerts.map((alert) => (
              <article className={`transaction-alert severity-${alert.severity}`} role="alert" key={alert.id}>
                <AlertTriangle size={18} />
                <div><strong>{alert.title}</strong><p>{alert.cause}</p><small>{alert.recommended_action}</small></div>
              </article>
            )) : (
              <p className="transaction-clear">No configured transaction threshold triggered. This is not purchase approval.</p>
            )}
            <small className="demo-disclaimer">Simulation only · nothing was executed or saved.</small>
          </section>
        )}
      </dialog>
    </>
  );
}
