import { Modal } from './ui'

export function PageIntro({ eyebrow, title, children, actions }) {
  return <div className="page-intro">
    <div>
      {eyebrow && <div className="eyebrow">{eyebrow}</div>}
      <h2>{title}</h2>
      {children && <p>{children}</p>}
    </div>
    {actions && <div className="page-actions">{actions}</div>}
  </div>
}

export function ErrorNote({ children }) {
  if (!children) return null
  return <div className="error-note"><span>!</span>{children}</div>
}

export function Loading({ label = 'Loading secure telemetry…' }) {
  return <div className="loading"><span className="spinner" />{label}</div>
}

export function Field({ label, children, hint }) {
  return <label className="field">
    <span>{label}</span>
    {children}
    {hint && <small>{hint}</small>}
  </label>
}

export function DataTable({ columns, rows, empty = 'No records match the current filters.' }) {
  if (!rows?.length) return <div className="empty"><span>◌</span>{empty}</div>
  return <div className="table-wrap"><table>
    <thead><tr>{columns.map((column) => <th key={column.key}>{column.label}</th>)}</tr></thead>
    <tbody>{rows.map((row, index) => <tr key={row.id || `${index}-${row.created_at}`} onClick={row.onClick}>
      {columns.map((column) => <td key={column.key} className={column.className || ''}>{column.render ? column.render(row) : row[column.key] ?? '—'}</td>)}
    </tr>)}</tbody>
  </table></div>
}

export function Details({ label, value }) {
  return <div className="kv-item"><span className="k">{label}</span><span className="v mono">{value || '—'}</span></div>
}

export function Confirmation({ title, children, onClose, onConfirm, busy, confirmText = 'Confirm' }) {
  return <Modal title={title} onClose={onClose}>
    <p className="confirm-copy">{children}</p>
    <div className="modal-actions">
      <button className="btn" onClick={onClose} disabled={busy}>Cancel</button>
      <button className="btn primary" onClick={onConfirm} disabled={busy}>{busy ? 'Working…' : confirmText}</button>
    </div>
  </Modal>
}

