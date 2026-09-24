import { useState } from 'react'
import { api, fmtDate, money } from '../api'
import { DataTable, ErrorNote, Field, Loading, PageIntro } from '../components/data'
import { useApi } from '../components/hooks'
import { Modal, Pager } from '../components/ui'
import { RiskBadge, StatusBadge } from '../components/badges'
import { toast } from '../components/toast'

const CONFIG = {
  'sim-swap': { endpoint: '/sim-swaps', title: 'SIM swap monitor', eyebrow: 'Subscriber identity / SIM re-issuance', description: 'Inspect new SIM identities, network changes, channels and repeat-swap behavior in real time.', columns: [['msisdn', 'MSISDN'], ['channel', 'Channel'], ['network_change', 'Network change'], ['risk', 'Risk'], ['status', 'Status'], ['time', 'Observed']] },
  airtime: { endpoint: '/airtime/transfers', title: 'Airtime transfer monitor', eyebrow: 'Value movement / velocity', description: 'Watch new beneficiaries, transfer bursts, large values and transfers from watched lines.', columns: [['sender_msisdn', 'Sender'], ['recipient_msisdn', 'Recipient'], ['amount', 'Amount'], ['risk', 'Risk'], ['status', 'Status'], ['time', 'Observed']] },
  account: { endpoint: '/account/events', title: 'Account takeover monitor', eyebrow: 'Identity and access / ATO signals', description: 'Correlate sensitive account changes with device, IP and location signals from the access layer.', columns: [['msisdn', 'MSISDN'], ['event_type', 'Event'], ['location', 'Location'], ['risk', 'Risk'], ['status', 'Status'], ['time', 'Observed']] },
}

export function MonitorPage({ kind }) {
  const config = CONFIG[kind]
  const [page, setPage] = useState(1)
  const [risk, setRisk] = useState('')
  const [search, setSearch] = useState('')
  const [selected, setSelected] = useState(null)
  const searchKey = kind === 'airtime' ? 'sender_msisdn' : 'msisdn'
  const path = `${config.endpoint}?page=${page}&per_page=20${risk ? `&risk_level=${risk}` : ''}${search ? `&${searchKey}=${encodeURIComponent(search)}` : ''}`
  const { data, error, loading, reload } = useApi(path)
  const rows = (data?.items || []).map((row) => ({ ...row, onClick: () => setSelected(row) }))
  const value = (row, key) => {
    if (key === 'risk') return <RiskBadge level={row.risk_level} score={row.risk_score} />
    if (key === 'status') return <StatusBadge status={row.status} />
    if (key === 'time') return <span className="mono">{fmtDate(row.swap_datetime || row.transfer_datetime || row.event_datetime)}</span>
    if (key === 'amount') return <span className="mono">{money(row.amount)}</span>
    if (key === 'network_change') return <span className={row.network_change ? 'code' : ''}>{row.network_change ? 'YES · NETWORK CHANGED' : 'No change'}</span>
    if (key === 'event_type') return <span className="code">{String(row.event_type || '').replaceAll('_', ' ')}</span>
    return <span className="mono">{row[key] || '—'}</span>
  }
  const columns = config.columns.map(([key, label]) => ({ key, label, render: (row) => value(row, key) }))
  return <>
    <PageIntro eyebrow={config.eyebrow} title={config.title} actions={<><a className="btn" href="#/simulator">Open simulator</a><button className="btn primary" onClick={reload}>↻ Refresh</button></>}>{config.description}</PageIntro>
    <section className="card"><div className="card-head"><h2>Live event stream</h2><span className="hint">{data?.pagination?.total || 0} events indexed</span></div><div className="filter-row" style={{ padding: '0 18px 16px' }}><Field label="Risk level"><select className="select" value={risk} onChange={(e) => { setPage(1); setRisk(e.target.value) }}><option value="">All levels</option><option value="safe">Safe</option><option value="suspicious">Suspicious</option><option value="flagged">Flagged</option></select></Field><Field label={kind === 'airtime' ? 'Sender MSISDN' : 'MSISDN'}><input className="input" value={search} onChange={(e) => { setPage(1); setSearch(e.target.value) }} placeholder="Search number" /></Field><button className="btn small" style={{ marginTop: 19 }} onClick={reload}>Apply filters</button></div>{error && <div style={{ padding: '0 18px 16px' }}><ErrorNote>{error}</ErrorNote></div>}{loading && !data ? <Loading /> : <DataTable columns={columns} rows={rows} />}<Pager pagination={data?.pagination} onPage={setPage} /></section>
    {selected && <EventModal kind={kind} event={selected} onClose={() => setSelected(null)} onRefresh={reload} />}
  </>
}

function EventModal({ kind, event, onClose, onRefresh }) {
  const [busy, setBusy] = useState(false)
  const title = kind === 'sim-swap' ? 'SIM swap forensic view' : kind === 'airtime' ? 'Airtime transfer forensic view' : 'Account event forensic view'
  const refreshEvent = async () => {
    setBusy(true)
    try {
      const path = kind === 'sim-swap' ? `/sim-swaps/${event.event_id}/detail` : kind === 'airtime' ? `/airtime/transfers/${event.event_id}/detail` : `/account/events/${event.event_id}/detail`
      await api.get(path)
      toast('Event record refreshed from the audit stream', 'ok')
      onRefresh()
    } catch (err) { toast(err.message, 'err') } finally { setBusy(false) }
  }
  const details = kind === 'sim-swap'
    ? [['MSISDN', event.msisdn], ['Old IMSI', event.old_imsi], ['New IMSI', event.new_imsi], ['Channel', event.channel], ['Agent', event.agent_name], ['Device', event.device_model], ['Network change', event.network_change ? 'Yes' : 'No'], ['Observed', fmtDate(event.swap_datetime)]]
    : kind === 'airtime'
      ? [['Sender', event.sender_msisdn], ['Recipient', event.recipient_msisdn], ['Amount', money(event.amount)], ['Method', event.method], ['New beneficiary', event.is_new_recipient ? 'Yes' : 'No'], ['Transfers in 60m', event.transfers_window_60m], ['Observed', fmtDate(event.transfer_datetime)]]
      : [['MSISDN', event.msisdn], ['Event type', event.event_type], ['IP address', event.ip_address], ['Device hash', event.device_hash], ['Location', event.location], ['Observed', fmtDate(event.event_datetime)]]
  return <Modal title={title} onClose={onClose} width={620}>
    <div className="detail-grid"><div className="wide"><div className="inline-actions"><RiskBadge level={event.risk_level} score={event.risk_score} /><StatusBadge status={event.status} /></div></div>{details.map(([label, value]) => <div className="kv-item" key={label}><span className="k">{label}</span><span className="v mono">{value || '—'}</span></div>)}</div>
    {event.reasons?.length > 0 && <><div className="eyebrow" style={{ marginTop: 20 }}>Engine explanation</div><ul className="reasons">{event.reasons.map((reason) => <li key={reason}>▸ {reason}</li>)}</ul></>}
    <div className="modal-actions"><button className="btn" onClick={onClose}>Close</button><button className="btn primary" onClick={refreshEvent} disabled={busy}>{busy ? 'Refreshing…' : 'Refresh event'}</button></div>
  </Modal>
}

