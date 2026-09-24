import { levelColor, severityColor } from '../api'

export function RiskBadge({ level, score }) {
  const cls = `bg-${level || 'safe'}`
  return (
    <span className={`badge ${cls}`}>
      <span className="c" style={{ background: levelColor(level) }} />
      {level || 'safe'}{score != null ? ` · ${score}` : ''}
    </span>
  )
}

export function SeverityBadge({ severity }) {
  const cls = `bg-${severity || 'INFO'}`
  return (
    <span className={`badge ${cls}`}>
      <span className="c" style={{ background: severityColor(severity) }} />
      {severity || 'INFO'}
    </span>
  )
}

export function StatusBadge({ status }) {
  const key = {
    open: 'open',
    acknowledged: 'acknowledged',
    resolved: 'resolved',
    active: 'active',
    flagged: 'flagged-sub',
  }
  return <span className={`badge bg-${key[status] || 'open'}`}>{status}</span>
}

export function ChannelBadge({ channel }) {
  const label = channel || '—'
  return (
    <span className={`badge ${channel === 'NONE' ? 'bg-INFO' : 'bg-active'}`}>
      {label}
    </span>
  )
}
