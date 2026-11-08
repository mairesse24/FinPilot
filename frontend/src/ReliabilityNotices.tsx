import type { Meta, Notice } from './api';

export function uniqueNotices(groups: Notice[][]): Notice[] {
  const result = new Map<string, Notice>();
  for (const notice of groups.flat()) {
    const key = `${notice.code}:${notice.context}`;
    const old = result.get(key);
    result.set(key, old ? { ...old, technical_detail: [...new Set([old.technical_detail, notice.technical_detail])].join('\n') } : notice);
  }
  return [...result.values()];
}

export default function ReliabilityNotices({ groups, metas = [] }: { groups: Notice[][]; metas?: Meta[] }) {
  const notices = uniqueNotices(groups);
  const critical = notices.filter(n => n.category === 'critical');
  const limits = notices.filter(n => n.category === 'data_limitation');
  const technical = [...new Set(notices.map(n => n.technical_detail))];
  const raw = notices.length ? [] : [...new Set(metas.map(m => m.warning).filter(Boolean))];
  return <section className="live-panel" aria-label="Data and forecast reliability">
    {critical.map(n => <p className="live-warning" role="alert" key={`${n.code}:${n.context}`} data-notice-code={n.code}>{n.message}</p>)}
    {limits.length > 0 && <details><summary>Data limitations · {limits.length}</summary>
      {limits.map(n => <p key={`${n.code}:${n.context}`} data-notice-code={n.code}>{n.message}</p>)}
    </details>}
    {(notices.length > 0 || raw.length > 0) && <details><summary>Engineering diagnostics</summary>
      {notices.map(n => <p key={`${n.code}:${n.context}`}>{n.code} ? {n.context}</p>)}
      {technical.map(detail => <pre key={detail} style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{detail}</pre>)}
      {raw.length > 0 && <details><summary>Legacy diagnostic payloads</summary>{raw.map(w => <pre key={w} style={{ whiteSpace: 'pre-wrap' }}>{w}</pre>)}</details>}
    </details>}
    {!notices.length && !raw.length && <p>No reported data limitations.</p>}
  </section>;
}
