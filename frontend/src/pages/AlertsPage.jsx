import { useState } from 'react'
import { api, fmtDate } from '../api'
import { DataTable, ErrorNote, Field, Loading, PageIntro } from '../components/data'
import { useApi } from '../components/hooks'
import { Modal, Pager } from '../components/ui'
import { ChannelBadge, SeverityBadge, StatusBadge } from '../components/badges'
import { toast } from '../components/toast'

export function AlertsPage() {
  const [page, setPage] = useState(1)
  const [status, setStatus] = useState('')
  const [severity, setSeverity] = useState('')
  const [type, setType] = useState('')
  const [selected, setSelected] = useState(null)
  const path = `/alerts?page=${page}&per_page=20${status ? `&status=${status}` : ''}${severity ? `&severity=${severity}` : ''}${type ? `&alert_type=${type}` : ''}`
  const { data, error, loading, reload } = useApi(path)
  const columns = [
    { key: 'title', label: 'Alert', render: (row) => <div><b className="cell-title">{row.title}</b><small className="cell-sub">{row.msisdn} · {row.alert_type.replaceAll('_', ' ')}</small></div> },
    { key: 'severity', label: 'Severity', render: (row) => <SeverityBadge severity={row.severity} /> },
    { key: 'status', label: 'Status', render: (row) => <StatusBadge status={row.status} /> },
    { key: 'channel_sent', label: 'Delivered', render: (row) => <ChannelBadge channel={row.channel_sent} /> },
    { key: 'created_at', label: 'Created', render: (row) => <span className="mono">{fmtDate(row.created_at)}</span> },
  ]
  const rows = (data?.items || []).map((row) => ({ ...row, onClick: () => setSelected(row) }))
  return <>
    <PageIntro eyebrow="Investigation / alert lifecycle" title="Alert console" actions={<button className="btn primary" onClick={reload}>↻ Refresh</button>}>Triage, acknowledge and resolve generated fraud alerts. Delivery state is recorded for every subscriber notification attempt.</PageIntro>
    <section className="card"><div className="card-head"><h2>Fraud alert stream</h2><span className="hint">{data?.pagination?.total || 0} alerts</span></div><div className="filter-row filter-pad"><Field label="Status"><select className="select" value={status} onChange={(e) => { setPage(1); setStatus(e.target.value) }}><option value="">All statuses</option><option value="open">Open</option><option value="acknowledged">Acknowledged</option><option value="resolved">Resolved</option></select></Field><Field label="Severity"><select className="select" value={severity} onChange={(e) => { setPage(1); setSeverity(e.target.value) }}><option value="">All severities</option><option value="INFO">Info</option><option value="LOW">Low</option><option value="MEDIUM">Medium</option><option value="HIGH">High</option><option value="CRITICAL">Critical</option></select></Field><Field label="Signal"><select className="select" value={type} onChange={(e) => { setPage(1); setType(e.target.value) }}><option value="">All signals</option><option value="SIM_SWAP">SIM swap</option><option value="AIRTIME_TRANSFER">Airtime</option><option value="ACCOUNT_TAKEOVER">ATO</option></select></Field></div>{error && <div className="filter-pad"><ErrorNote>{error}</ErrorNote></div>}{loading && !data ? <Loading /> : <DataTable columns={columns} rows={rows} empty="No alerts match the current filters." />}<Pager pagination={data?.pagination} onPage={setPage} /></section>
    {selected && <AlertModal alert={selected} onClose={() => setSelected(null)} onChanged={reload} />}
  </>
}

function AlertModal({ alert, onClose, onChanged }) {
  const [busy, setBusy] = useState('')
  const update = async (next) => {
    setBusy(next)
    try { await api.put(`/alerts/${alert.alert_id}/status`, { status: next }); toast(`Alert ${next}`, 'ok'); onChanged(); onClose() } catch (err) { toast(err.message, 'err') } finally { setBusy('') }
  }
  return <Modal title="Alert investigation" onClose={onClose} width={620}><div className="investigation-head"><div><span className={`badge bg-${alert.severity}`}>{alert.severity}</span><h4>{alert.title}</h4><span className="mono">{alert.msisdn} · {alert.alert_type.replaceAll('_', ' ')}</span></div><div className="risk-number"><strong>{alert.risk_score}</strong><small>risk / 100</small></div></div><p className="investigation-copy">{alert.message}</p><div className="kv"><span className="k">Status</span><span className="v"><StatusBadge status={alert.status} /></span><span className="k">Delivery</span><span className="v"><ChannelBadge channel={alert.channel_sent} /></span><span className="k">Created</span><span className="v mono">{fmtDate(alert.created_at)}</span></div><div className="modal-actions">{alert.status !== 'acknowledged' && alert.status !== 'resolved' && <button className="btn" onClick={() => update('acknowledged')} disabled={!!busy}>Acknowledge</button>}{alert.status !== 'resolved' && <button className="btn primary" onClick={() => update('resolved')} disabled={!!busy}>{busy ? 'Working…' : 'Resolve alert'}</button>}<button className="btn" onClick={onClose}>Close</button></div></Modal>
}
