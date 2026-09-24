import { useEffect, useState } from 'react'
import { api, fmtDate, severityColor } from '../api'
import { Donut, StackedBars, Sparkline } from '../components/ui'
import { ErrorNote, Loading, PageIntro } from '../components/data'
import { RiskBadge, SeverityBadge, StatusBadge } from '../components/badges'

const COLORS = { INFO: '#38bdf8', LOW: '#a3e635', MEDIUM: '#f59e0b', HIGH: '#fb7185', CRITICAL: '#ef4444' }

export function Dashboard() {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  useEffect(() => {
    let active = true
    const load = () => api.get('/dashboard/summary').then((value) => { if (active) setData(value) }).catch((err) => { if (active) setError(err.message) })
    load()
    const timer = window.setInterval(load, 30000)
    return () => { active = false; window.clearInterval(timer) }
  }, [])
  if (!data) return error ? <ErrorNote>{error}</ErrorNote> : <Loading />
  const stats = [
    ['Open alerts', data.open_alerts, '🚨', '#ef4444', `${data.high_critical} high/critical`, '#/alerts'],
    ['Lines watched', data.total_subscribers, '👥', '#22d3ee', `${data.flagged_subscribers} under watch`, '#/subscribers'],
    ['SIM swaps today', data.events_today.sim_swaps, '📱', '#818cf8', 'real-time signal', '#/sim-swaps'],
    ['Delivery success', `${data.notifications.successful}/${data.notifications.total}`, '📨', '#22c55e', `${data.notifications.failed} failed`, '#/notifications'],
  ]
  const series = [
    { name: 'SIM swaps', values: data.sim_swap_trend.map((p) => p.count) },
    { name: 'Airtime', values: data.airtime_trend.map((p) => p.count) },
    { name: 'ATO events', values: data.account_trend.map((p) => p.count) },
  ]
  return <>
    {error && <ErrorNote>Live refresh: {error}</ErrorNote>}
    <PageIntro eyebrow="FraudShield / command center" title="Real-time fraud posture" actions={<span className="live-pill"><span className="pulse" /> AUTO-REFRESH 30s</span>}>
      Monitor SIM re-issuance, transfer velocity and account takeover signals across your subscriber base. Scores are calculated by the live rule engine as events arrive.
    </PageIntro>
    <div className="grid stats">{stats.map(([label, value, icon, color, note, route]) => <div className="card stat" key={label}><div className="label">{label}</div><div className="value">{value}</div><div className="foot">{icon} {note}</div><span className="glow" style={{ background: color }} /><div className="stat-actions"><a className="stat-link" href={route}>Open monitor →</a></div></div>)}</div>
    <div className="grid cols-2 mt">
      <section className="card"><div className="card-head"><h2>Alert severity</h2><span className="hint">All recorded alerts</span></div><div className="donut-wrap"><Donut data={data.severity_distribution} colors={COLORS} /><div className="donut-legend">{Object.entries(data.severity_distribution).map(([key, value]) => <div className="legend-item" key={key}><span className="sw" style={{ background: COLORS[key] }} />{key}<span className="n">{value}</span></div>)}</div></div></section>
      <section className="card"><div className="card-head"><h2>Event volume</h2><span className="hint">Last 7 days</span></div><StackedBars series={series} days={data.sim_swap_trend.map((p) => ({ date: p.date }))} colors={['#22d3ee', '#818cf8', '#f59e0b']} /></section>
    </div>
    <div className="grid cols-2 mt">
      <section className="card"><div className="card-head"><h2>Latest fraud alerts</h2><a className="btn small" href="#/alerts">View all</a></div><div className="feed">{data.recent_alerts.length ? data.recent_alerts.map((alert) => <div className="feed-item" key={alert.alert_id}><div className="ic" style={{ background: `${severityColor(alert.severity)}18`, color: severityColor(alert.severity) }}>{alert.alert_type === 'SIM_SWAP' ? '📱' : alert.alert_type === 'AIRTIME_TRANSFER' ? '💸' : '🔓'}</div><div className="body"><div className="t">{alert.title}</div><div className="m">{alert.msisdn} · {alert.alert_type.replaceAll('_', ' ').toLowerCase()}</div><div className="meta"><SeverityBadge severity={alert.severity} /><StatusBadge status={alert.status} /><span>{fmtDate(alert.created_at)}</span></div></div></div>) : <div className="empty">No alerts recorded.</div>}</div></section>
      <section className="card"><div className="card-head"><h2>Active watchlist</h2><span className="hint">Suspicious + flagged SIM events</span></div><div>{data.active_watchlist.length ? data.active_watchlist.map((item) => <div className="watch-item" key={item.event_id}><div className="inline-actions" style={{ justifyContent: 'space-between' }}><div><span className="mono">{item.msisdn}</span><div className="chips" style={{ marginTop: 6 }}><RiskBadge level={item.risk_level} score={item.risk_score} />{item.channel && <span className="chip">{item.channel}</span>}</div></div><span className="mono" style={{ color: 'var(--text-dim)' }}>{fmtDate(item.swap_datetime)}</span></div>{item.reasons?.length > 0 && <div className="reason-box">{item.reasons[0]}</div>}</div>) : <div className="empty">No active watchlist events.</div>}</div></section>
    </div>
    <div className="grid cols-3 mt">{[['SIM swap trend', data.sim_swap_trend.map((p) => p.count), '#22d3ee'], ['Airtime trend', data.airtime_trend.map((p) => p.count), '#818cf8'], ['ATO trend', data.account_trend.map((p) => p.count), '#f59e0b']].map(([label, values, color]) => <div className="card" key={label}><div className="card-head"><h2>{label}</h2><span className="hint">7d</span></div><div className="spark-box"><Sparkline values={values} color={color} height={48} /></div></div>)}</div>
  </>
}
