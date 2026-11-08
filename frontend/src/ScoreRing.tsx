export default function ScoreRing({
  score,
  pending = false,
  estimated = false,
}: {
  score: number | null;
  pending?: boolean;
  estimated?: boolean;
}) {
  const tone =
    score == null
      ? "unknown"
      : score < 25
        ? "red"
        : score < 50
          ? "orange"
          : score < 75
            ? "yellow"
            : "green";
  return (
    <div className="score-overview">
      <div className={`score-ring tone-${tone}`}>
        <svg
          viewBox="0 0 140 140"
          role="img"
          aria-label={
            score == null
              ? "Financial health score unavailable"
              : `Financial health score: ${score} out of 100`
          }
        >
          <circle cx="70" cy="70" r="60" fill="none" stroke="#293343" strokeWidth="8" />
          <circle
            cx="70"
            cy="70"
            r="60"
            fill="none"
            stroke="currentColor"
            strokeWidth="8"
            pathLength="100"
            strokeDasharray={`${score ?? 0} 100`}
            strokeLinecap="round"
            transform="rotate(-90 70 70)"
          />
        </svg>
        <div>
          <strong>{score == null ? "—" : `${score.toFixed(2)} / 100`}</strong>
          <small>Financial health</small>
        </div>
      </div>
      <div>
        <span className="eyebrow">Your financial health</span>
        <h2>
          {estimated
            ? "Automatic financial health estimate"
            : pending
              ? "Inputs changed — recalculate"
            : score == null
              ? "Score withheld — confirmation needed"
              : "A closer look at your financial health"}
        </h2>
        <p>
          {estimated
            ? "Based on imported balances, transaction history, bills and scheduled income."
            : "Based on confirmed cash flow, emergency reserves, debt payments and upcoming bills."}
        </p>
        <small>
          Prototype wellness index, not a credit score. Display colors use equal 25-point bands;
          these are not validated risk categories.
        </small>
      </div>
    </div>
  );
}
