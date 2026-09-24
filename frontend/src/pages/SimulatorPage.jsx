import { useState } from 'react'
import { api, fmtDate, money } from '../api'
import { ErrorNote, PageIntro } from '../components/data'
import { RiskBadge, SeverityBadge } from '../components/badges'
import { toast } from '../components/toast'

const TYPES = [
  { key: 'sim-swap', label: 'SIM swap', icon: '📱', endpoint: '/simulate/sim-swap', copy: 'Re-issued SIM, new IMSI, suspicious channel or repeat swap.' },
  { key: 'airtime', label: 'Airtime transfer', icon: '💸', endpoint: '/simulate/airtime', copy: 'New beneficiary, high value, velocity or odd-hour transfer.' },
  { key: 'account', label: 'Account takeover', icon: '🔓', endpoint: '/simulate/account', copy: 'New device, OTP abuse, password reset or profile takeover.' },
]
const SCENARIOS = [
  { key: 'normal', label: 'Normal', description: 'Baseline activity expected to pass silently.', tone: 'safe' },
  { key: 'suspicious', label: 'Suspicious', description: 'One or more medium-risk indicators are present.', tone: 'suspicious' },
  { key: 'flagged', label: 'Flagged', description: 'High-confidence fraud pattern; subscriber alert is dispatched.', tone: 'flagged' },
]

export function SimulatorPage() {
  const [type, setType] = useState(TYPES[0])
  const [scenario, setScenario] = useState('suspicious')
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const run = async () => {
    setBusy(true); setError('')
    try {
      const data = await api.post(type.endpoint, { scenario })
      setResult({ type: type.key, data })
      toast(`${type.label} ${scenario} event scored`, scenario === 'flagged' ? 'warn' : 'ok')
    } catch (err) { setError(err.message); toast(err.message, 'err') } finally { setBusy(false) }
  }
  return <>
    <PageIntro eyebrow="Controlled environment / live ingestion" title="Event simulator" actions={<span className="live-pill"><span className="pulse" /> PIPELINE READY</span>}>Generate representative telco events and send them through the exact same scoring, alert and notification pipeline as network integrations.</PageIntro>
    <div className="sim-grid mb">{TYPES.map((item) => <button type="button" className={`card sim-tile ${type.key === item.key ? 'selected' : ''}`} key={item.key} onClick={() => { setType(item); setResult(null) }}><div className="em">{item.icon}</div><h4>{item.label}</h4><p>{item.copy}</p><span className="tile-state">{type.key === item.key ? 'SELECTED' : 'SELECT'}</span></button>)}</div>
    <div className="grid cols-2">
      <section className="card"><div className="card-head"><h2>Run a scenario</h2><span className="hint">POST /simulate/{type.key}</span></div><div className="scenario-list">{SCENARIOS.map((item) => <button type="button" className={`scenario ${item.tone} ${scenario === item.key ? 'selected' : ''}`} key={item.key} onClick={() => setScenario(item.key)}><span className="scenario-dot" /><span><b>{item.label}</b><small>{item.description}</small></span><strong>{scenario === item.key ? '●' : '○'}</strong></button>)}</div>{error && <div className="filter-pad"><ErrorNote>{error}</ErrorNote></div>}<div className="simulator-actions"><button className="btn primary" onClick={run} disabled={busy}>{busy ? 'Scoring event…' : `Run ${scenario} ${type.label}`}</button><span className="hint">Creates a real audit record in the local database.</span></div></section>
      <section className="card"><div className="card-head"><h2>Latest result</h2><span className="hint">{result ? 'JUST NOW' : 'WAITING'}</span></div>{!result ? <div className="empty"><div style={{ fontSize: 32, marginBottom: 8 }}>⌁</div>Select an event and run a scenario to inspect the engine verdict.</div> : <ResultPanel result={result} />}</section>
    </div>
  </>
}

function ResultPanel({ result }) {
  const { type, data } = result
  const title = type === 'sim-swap' ? 'SIM swap event' : type === 'airtime' ? 'Airtime transfer' : 'Account event'
  const rows = type === 'sim-swap' ? [['Subscriber', data.msisdn], ['Channel', data.channel], ['New IMSI', data.new_imsi], ['Observed', fmtDate(data.swap_datetime)]] : type === 'airtime' ? [['Sender', data.sender_msisdn], ['Recipient', data.recipient_msisdn], ['Amount', money(data.amount)], ['Transfers in 60m', data.transfers_window_60m]] : [['Subscriber', data.msisdn], ['Event type', data.event_type], ['Location', data.location], ['IP address', data.ip_address]]
  return <div className="result-panel"><div className="result-hero"><div><span className="eyebrow">{title} · event #{data.event_id}</span><h3>{data.risk_level === 'flagged' ? 'Fraud pattern flagged' : data.risk_level === 'suspicious' ? 'Suspicious activity detected' : 'Activity accepted'}</h3></div><div className="risk-score"><strong>{data.risk_score}</strong><small>/ 100</small></div></div><div className="inline-actions" style={{ margin: '14px 0' }}><RiskBadge level={data.risk_level} score={data.risk_score} />{data.alert && <SeverityBadge severity={data.alert.severity} />}{data.alert && <span className="chip">{data.alert.channel_sent} dispatched</span>}</div><div className="detail-grid">{rows.map(([label, value]) => <div className="kv-item" key={label}><span className="k">{label}</span><span className="v mono">{value || '—'}</span></div>)}</div>{data.reasons?.length > 0 && <div className="reason-box result-reasons"><b>Why the engine decided</b><ul className="reasons">{data.reasons.map((reason) => <li key={reason}>{reason}</li>)}</ul></div>}{data.alert && <div className="alert-delivery"><span>✓</span><div><b>Subscriber notification dispatched</b><p>{data.alert.title} · {data.alert.status}</p></div></div>}</div>
}
