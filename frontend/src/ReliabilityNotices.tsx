import type { Meta, Notice } from "./api";

export function uniqueNotices(groups: Notice[][]): Notice[] {
  const result = new Map<string, Notice>();
  for (const notice of groups.flat()) {
    const key = `${notice.code}:${notice.context}`;
    const old = result.get(key);
    result.set(
      key,
      old
        ? { ...old, technical_detail: [...new Set([old.technical_detail, notice.technical_detail])].join("\n") }
        : notice,
    );
  }
  return [...result.values()];
}

export default function ReliabilityNotices({ groups, metas: _metas = [] }: { groups: Notice[][]; metas?: Meta[] }) {
  const notices = uniqueNotices(groups);
  const critical = notices.filter((notice) => notice.category === "critical");
  const limits = notices.filter((notice) => notice.category === "data_limitation");
  if (!critical.length && !limits.length) return null;
  return (
    <section className="estimate-notices" aria-label="Data and forecast reliability">
      {critical.map((notice) => (
        <p className="live-warning" role="alert" key={`${notice.code}:${notice.context}`} data-notice-code={notice.code}>
          {notice.message}
        </p>
      ))}
      {limits.length > 0 && (
        <details>
          <summary>About this estimate</summary>
          <div className="estimate-details">
            {limits.map((notice) => (
              <p key={`${notice.code}:${notice.context}`} data-notice-code={notice.code}>{notice.message}</p>
            ))}
          </div>
        </details>
      )}
    </section>
  );
}
