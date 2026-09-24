import { useState } from 'react'
import { api, fmtDate } from '../api'
import { DataTable, ErrorNote, Field, Loading, PageIntro } from '../components/data'
import { useApi } from '../components/hooks'
import { Pager } from '../components/ui'
import { ChannelBadge } from '../components/badges'
import { toast } from '../components/toast'

export function NotificationsPage() {
  const [page, setPage] = useState(1)
  const [channel, setChannel] = useState('')
  const [success, setSuccess] = useState('')
  const [test, setTest] = useState({ msisdn: '254712345678', channel: 'sms' })
  const [busy, setBusy] = useState(false)
  const path = `/notifications/logs?page=${page}&per_page=20${channel ? `&channel=${channel}` : ''}${success ? `&success=${success}` : ''}`
  const { data, error, loading, reload } = useApi(path)
  const rows = data?.items || []
  const columns = [
    { key: 'log_id', label: 'Attempt', render: (row) => <span className="mono">#{row.log_id}</span> },
    { key: 'channel', label: 'Channel', render: (row) => <ChannelBadge channel={row.channel} /> },
    { key: 'msisdn', label: 'Subscriber', render: (row) => <span className="mono">{row.msisdn}</span> },
    { key: 'provider', label: 'Provider', render: (row) => <span className="chip">{row.provider}</span> },
    { key: 'success', label: 'Result', render: (row) => <span className={`badge ${row.success ? 'bg-active' : 'bg-flagged'}`}>{row.success ? 'DELIVERED' : 'FAILED'}</span> },
    { key: 'created_at', label: 'Attempted', render: (row) => <span className="mono">{fmtDate(row.created_at)}</span> },
  ]
  const sendTest = async (e) => {
    e.preventDefault(); setBusy(true)
    try { const result = await api.post('/notifications/test', test); toast(result.simulated ? 'Test notification queued in sandbox' : 'Test notification sent', result.success ? 'ok' : 'err'); reload() } catch (err) { toast(err.message, 'err') } finally { setBusy(false) }
  }
  return <>
    <PageIntro eyebrow="Africa\'s Talking / delivery operations" title="Notification audit" actions={<button className="btn primary" onClick={reload}>↻ Refresh log</button>}>Verify subscriber SMS and voice delivery, inspect provider responses and run a safe sandbox connectivity test.</PageIntro>
    <div className="grid cols-3 mb"><div className="card stat"><div className="label">Attempts indexed</div><div className="value">{data?.pagination?.total || 0}</div><div className="foot">All channels and statuses</div></div><div className="card stat"><div className="label">Current page</div><div className="value">{page}</div><div className="foot">of {data?.pagination?.pages || 1}</div></div><div className="card stat"><div className="label">Provider</div><div className="value" style={{ fontSize: 22 }}>AT Sandbox</div><div className="foot">SMS + voice adapters</div></div></div>
    <div className="grid cols-2"><section className="card"><div className="card-head"><h2>Send test notification</h2><span className="hint">Operator tool</span></div><form className="form-pad" onSubmit={sendTest}><Field label="Test MSISDN" hint="Use a sandbox-safe number for demo delivery."><input required className="input" value={test.msisdn} onChange={(e) => setTest({ ...test, msisdn: e.target.value })} /></Field><Field label="Channel"><select className="select" value={test.channel} onChange={(e) => setTest({ ...test, channel: e.target.value })}><option value="sms">SMS</option><option value="voice">Voice</option></select></Field><button className="btn primary" disabled={busy} style={{ marginTop: 16 }}>{busy ? 'Dispatching…' : 'Dispatch test alert'}</button></form><div className="sandbox-note"><b>Sandbox note</b><p>Voice calls fall back to a labelled simulation when the sandbox voice host is unavailable. Every attempt is still persisted for audit.</p></div></section><section className="card"><div className="card-head"><h2>Delivery filters</h2><span className="hint">Live audit query</span></div><div className="filter-row filter-pad"><Field label="Channel"><select className="select" value={channel} onChange={(e) => { setPage(1); setChannel(e.target.value) }}><option value="">All channels</option><option value="sms">SMS</option><option value="voice">Voice</option></select></Field><Field label="Result"><select className="select" value={success} onChange={(e) => { setPage(1); setSuccess(e.target.value) }}><option value="">All results</option><option value="true">Delivered</option><option value="false">Failed</option></select></Field><button className="btn small" style={{ marginTop: 19 }} onClick={reload}>Apply</button></div>{error && <div className="filter-pad"><ErrorNote>{error}</ErrorNote></div>}{loading && !data ? <Loading /> : <DataTable columns={columns} rows={rows} empty="No notification attempts found." />}<Pager pagination={data?.pagination} onPage={setPage} /></section></div>
  </>
}
