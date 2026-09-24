import { useState } from 'react'
import { api } from '../api'
import { DataTable, ErrorNote, Field, Loading, PageIntro } from '../components/data'
import { useApi } from '../components/hooks'
import { Modal } from '../components/ui'
import { SeverityBadge } from '../components/badges'
import { toast } from '../components/toast'

const EMPTY = { name: '', code: '', description: '', category: 'SIM_SWAP', weight: 20, severity: 'MEDIUM', is_active: true, config: '{}' }

export function RulesPage() {
  const [form, setForm] = useState(null)
  const [busy, setBusy] = useState(false)
  const { data, error, loading, reload } = useApi('/rules')
  const rules = data?.items || []
  const columns = [
    { key: 'name', label: 'Rule', render: (row) => <div><b className="cell-title">{row.name}</b><small className="cell-sub mono">{row.code}</small></div> },
    { key: 'category', label: 'Category', render: (row) => <span className="chip">{row.category}</span> },
    { key: 'severity', label: 'Severity', render: (row) => <SeverityBadge severity={row.severity} /> },
    { key: 'weight', label: 'Weight', render: (row) => <span className="mono">+{row.weight} pts</span> },
    { key: 'is_active', label: 'State', render: (row) => <span className={`badge ${row.is_active ? 'bg-active' : 'bg-resolved'}`}>{row.is_active ? 'Enabled' : 'Disabled'}</span> },
    { key: 'action', label: '', render: (row) => <button className="btn small" onClick={() => setForm({ ...row, config: JSON.stringify(row.config || {}, null, 2) })}>Edit</button> },
  ]
  const save = async (e) => {
    e.preventDefault(); setBusy(true)
    const payload = { ...form, weight: Number(form.weight), config: form.config ? JSON.parse(form.config) : {} }
    try { await (form.rule_id ? api.put(`/rules/${form.rule_id}`, payload) : api.post('/rules', payload)); toast(form.rule_id ? 'Detection rule updated' : 'Detection rule created', 'ok'); setForm(null); reload() } catch (err) { toast(err.message, 'err') } finally { setBusy(false) }
  }
  return <>
    <PageIntro eyebrow="Risk engine / configuration" title="Detection rules" actions={<><button className="btn" onClick={reload}>↻ Refresh</button><button className="btn primary" onClick={() => setForm({ ...EMPTY })}>+ Add rule</button></>}>Tune the live scoring engine. Active rules contribute their configured weight when their signal is present.</PageIntro>
    <section className="card"><div className="card-head"><h2>Rule catalog</h2><span className="hint">{rules.filter((rule) => rule.is_active).length} active signals</span></div>{error && <div className="filter-pad"><ErrorNote>{error}</ErrorNote></div>}{loading && !data ? <Loading /> : <DataTable columns={columns} rows={rules} empty="No detection rules configured." />}</section>
    {form && <Modal title={form.rule_id ? 'Edit detection rule' : 'Add detection rule'} onClose={() => setForm(null)}><form className="form-grid" onSubmit={save}><Field label="Rule name"><input required className="input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></Field><Field label="Unique code"><input required className="input" value={form.code} disabled={!!form.rule_id} onChange={(e) => setForm({ ...form, code: e.target.value.toUpperCase() })} /></Field><Field label="Category"><select className="select" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}><option>SIM_SWAP</option><option>AIRTIME</option><option>ACCOUNT</option><option>GLOBAL</option></select></Field><Field label="Weight"><input className="input" type="number" min="0" max="100" value={form.weight} onChange={(e) => setForm({ ...form, weight: e.target.value })} /></Field><Field label="Severity"><select className="select" value={form.severity} onChange={(e) => setForm({ ...form, severity: e.target.value })}><option>LOW</option><option>MEDIUM</option><option>HIGH</option><option>CRITICAL</option></select></Field><Field label="Description"><textarea className="input textarea" value={form.description || ''} onChange={(e) => setForm({ ...form, description: e.target.value })} /></Field><Field label="Config JSON"><textarea className="input textarea mono" value={form.config} onChange={(e) => setForm({ ...form, config: e.target.value })} /></Field><label className="check-field"><input type="checkbox" checked={form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} /> Rule is active</label><div className="modal-actions"><button type="button" className="btn" onClick={() => setForm(null)}>Cancel</button><button type="submit" className="btn primary" disabled={busy}>{busy ? 'Saving…' : 'Save rule'}</button></div></form></Modal>}
  </>
}
