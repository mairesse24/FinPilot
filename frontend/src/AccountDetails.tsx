import { useEffect, useRef, useState } from "react";
import type { Account } from "./api";
const money = (n: number) => n.toLocaleString("en-US", { style: "currency", currency: "USD" });
const groups = [
  { id: "all", label: "All accounts" },
  { id: "checking", label: "Checking" },
  { id: "savings", label: "Savings" },
  { id: "loan", label: "Loans" },
  { id: "credit_card", label: "Credit cards" },
];

export default function AccountDetails({
  selected,
  accounts,
  close,
}: {
  selected: string | null;
  accounts: Account[];
  close: () => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [filter, setFilter] = useState("all");
  useEffect(() => {
    if (!selected) {
      dialog.current?.close();
      return;
    }
    setFilter(selected);
    dialog.current?.showModal();
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previous;
    };
  }, [selected]);
  const rows = accounts.filter(
    (a) =>
      filter === "all" ||
      a.account_type === filter ||
      (filter === "debt" && ["loan", "credit_card"].includes(a.account_type)),
  );
  const title = groups.find((g) => g.id === filter)?.label ?? "Loans & credit cards";
  const total = rows.reduce(
    (sum, a) =>
      sum +
      (filter === "all" && ["loan", "credit_card"].includes(a.account_type)
        ? -a.balance
        : a.balance),
    0,
  );
  return (
    <dialog
      ref={dialog}
      className="account-dialog"
      onCancel={close}
      onClose={close}
      onClick={(e) => {
        if (e.target === e.currentTarget) close();
      }}
      aria-label="Account details"
    >
      <div className="dialog-heading">
        <div>
          <span className="eyebrow">Your connected accounts</span>
          <h2>{title}</h2>
        </div>
        <button autoFocus aria-label="Close account details" onClick={close}>
          Close
        </button>
      </div>
      <div className="account-tabs" aria-label="Filter accounts">
        {groups.map((g) => (
          <button key={g.id} aria-pressed={filter === g.id} onClick={() => setFilter(g.id)}>
            {g.label}
          </button>
        ))}
      </div>
      <p className="account-total">
        {rows.length} {rows.length === 1 ? "account" : "accounts"} · <strong>{money(total)}</strong>{" "}
        {filter === "all"
          ? "net worth across imported accounts"
          : filter === "debt" || filter === "loan" || filter === "credit_card"
            ? "owed"
            : "total recorded balance"}
      </p>
      {rows.length ? (
        rows.map((a) => (
          <article className="account-detail-row" key={a.id}>
            <div>
              <h3>{a.name}</h3>
              <p>
                {a.account_type.replace(/_/g, " ")} · ID ending {a.id.slice(-6)}
              </p>
            </div>
            <strong>{money(a.balance)}</strong>
            {["loan", "credit_card"].includes(a.account_type) && (
              <dl>
                <div>
                  <dt>Account minimum payment</dt>
                  <dd>
                    {a.min_payment == null
                      ? "Not supplied by account provider"
                      : money(a.min_payment)}
                  </dd>
                </div>
                <div>
                  <dt>APR</dt>
                  <dd>{a.apr == null ? "Not supplied" : `${(a.apr * 100).toFixed(2)}%`}</dd>
                </div>
                {a.account_type === "credit_card" && (
                  <div>
                    <dt>Credit limit</dt>
                    <dd>{a.credit_limit == null ? "Not supplied" : money(a.credit_limit)}</dd>
                  </div>
                )}
              </dl>
            )}
          </article>
        ))
      ) : (
        <p>
          No imported {title.toLowerCase()} to display. Connect or import these accounts through
          your banking data provider.
        </p>
      )}
      <p className="fine-print">
        Names and balances come from imported records. No bank name, mortgage type, interest rate or
        repayment term is inferred. Confirmed payment dates are listed under upcoming bills.
      </p>
    </dialog>
  );
}
