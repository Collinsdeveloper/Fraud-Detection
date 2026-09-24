import { useState } from 'react'
import { api } from '../api'
import { DataTable, ErrorNote, Field, Loading, PageIntro } from '../components/data'
import { useApi } from '../components/hooks'
import { Pager } from '../components/ui'
import { ChannelBadge, StatusBadge } from '../components/badges'
import { Modal } from '../components/ui'
import { toast } from '../components/toast'

const EMPTY = { msisdn: '', first_name: '', last_name: '', network: 'SAFARICOM', is_vip: false, alert_channel: 'sms', status: 'active' }

export function SubscribersPage() {
  const [page, setPage] = useState(1)
  const [status, setStatus] = useState('')
  const [network, setNetwork] = useState('')
  const [search, setSearch] = useState('')
  const [form, setForm] = useState(null)
  const path = `/subscribers?page=${page}&per_page=20${status ? `&status=${status}` : ''}${network ? `&network=${network}` : ''}${search ? `&q=${encodeURIComponent(search)}` : ''}`
  const { data, error, loading, reload } = useApi(path)
  const columns = [
    { key: 'full_name', label: 'Subscriber', render: (row) => <div><b className="cell-title">{row.full_name || 'Unnamed line'}</b><small className="cell-sub mono">{row.msisdn}</small></div> },
    { key: 'network', label: 'Network', render: (row) => <span className="chip">{row.network}</span> },
    { key: 'status', label: 'Standing', render: (row) => <StatusBadge status={row.status} /> },
    { key: 'alert_channel', label: 'Alerts via', render: (row) => <ChannelBadge channel={(row.alert_channel || 'sms').toUpperCase()} /> },
    { key: 'is_vip', label: 'Tier', render: (row) => row.is_vip ? <span className="badge bg-VIP">VIP</span> : <span className="text-dim">Standard</span> },
  ]
  const rows = (data?.items || []).map((row) => ({ ...row, onClick: () => setForm({ ...row }) }))
  return <>
    <PageIntro eyebrow="Directory / subscriber controls" title="Subscribers" actions={<><button className="btn" onClick={reload}>↻ Refresh</button><button className="btn primary" onClick={() => setForm({ ...EMPTY })}>+ Add subscriber</button></>}>Manage the lines included in monitoring and choose how each subscriber receives urgent alerts.</PageIntro>
    <section className="card"><div className="card-head"><h2>Subscriber directory</h2><span className="hint">{data?.pagination?.total || 0} lines</span></div><div className="filter-row filter-pad"><Field label="Search"><input className="input" value={search} onChange={(e) => { setPage(1); setSearch(e.target.value) }} placeholder="Name or MSISDN" /></Field><Field label="Standing"><select className="select" value={status} onChange={(e) => { setPage(1); setStatus(e.target.value) }}><option value="">All</option><option value="active">Active</option><option value="flagged">Flagged</option><option value="blocked">Blocked</option></select></Field><Field label="Network"><select className="select" value={network} onChange={(e) => { setPage(1); setNetwork(e.target.value) }}><option value="">All</option><option value="SAFARICOM">Safaricom</option><option value="AIRTEL">Airtel</option><option value="TELKOM">Telkom</option><option value="EQUITEL">Equitel</option></select></Field></div>{error && <div className="filter-pad"><ErrorNote>{error}</ErrorNote></div>}{loading && !data ? <Loading /> : <DataTable columns={columns} rows={rows} />}<Pager pagination={data?.pagination} onPage={setPage} /></section>
    {form && <SubscriberModal subscriber={form} onChange={setForm} onClose={() => setForm(null)} onSaved={() => { setForm(null); reload() }} />}
  </>
}

function SubscriberModal({ subscriber, onChange, onClose, onSaved }) {
  const [busy, setBusy] = useState(false)
  const edit = !!subscriber.subscriber_id
  const update = (key, value) => onChange({ ...subscriber, [key]: value })
  const save = async (e) => {
    e.preventDefault(); setBusy(true)
    try { await (edit ? api.put(`/subscribers/${subscriber.subscriber_id}`, subscriber) : api.post('/subscribers', subscriber)); toast(edit ? 'Subscriber updated' : 'Subscriber added', 'ok'); onSaved() } catch (err) { toast(err.message, 'err') } finally { setBusy(false) }
  }
  return <Modal title={edit ? 'Edit subscriber' : 'Add subscriber'} onClose={onClose}><form onSubmit={save} className="form-grid"><Field label="MSISDN"><input className="input" required value={subscriber.msisdn || ''} onChange={(e) => update('msisdn', e.target.value)} placeholder="2547..." /></Field><Field label="First name"><input className="input" value={subscriber.first_name || ''} onChange={(e) => update('first_name', e.target.value)} /></Field><Field label="Last name"><input className="input" value={subscriber.last_name || ''} onChange={(e) => update('last_name', e.target.value)} /></Field><Field label="Network"><select className="select" value={subscriber.network || 'SAFARICOM'} onChange={(e) => update('network', e.target.value)}><option>SAFARICOM</option><option>AIRTEL</option><option>TELKOM</option><option>EQUITEL</option></select></Field><Field label="Alert channel"><select className="select" value={subscriber.alert_channel || 'sms'} onChange={(e) => update('alert_channel', e.target.value)}><option value="sms">SMS</option><option value="voice">Voice</option><option value="both">SMS + voice</option><option value="none">No alerts</option></select></Field><Field label="Standing"><select className="select" value={subscriber.status || 'active'} onChange={(e) => update('status', e.target.value)}><option value="active">Active</option><option value="flagged">Flagged</option><option value="blocked">Blocked</option></select></Field><label className="check-field"><input type="checkbox" checked={!!subscriber.is_vip} onChange={(e) => update('is_vip', e.target.checked)} /> VIP priority subscriber</label><div className="modal-actions"><button type="button" className="btn" onClick={onClose}>Cancel</button><button type="submit" className="btn primary" disabled={busy}>{busy ? 'Saving…' : 'Save subscriber'}</button></div></form></Modal>
}
