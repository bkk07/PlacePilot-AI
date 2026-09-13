import { useEffect, useState } from 'react'
import { Badge, Button, Card, ErrorBanner, Field, PageTitle } from '../components/ui.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import { api, errorMessage } from '../lib/api.js'

function initials(name) {
  return (name || '?').trim().charAt(0).toUpperCase()
}

function CompanyCard({ c, isAdmin, onEdit, editing, editForm, setEditForm, onSave, onCancel, saving }) {
  if (editing) {
    return (
      <Card className="flex flex-col border-indigo-200 ring-1 ring-indigo-100">
        <h3 className="mb-3 font-semibold text-slate-900">Edit Company</h3>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Name *" value={editForm.name} onChange={(e) => setEditForm({ ...editForm, name: e.target.value })} required />
          <Field label="Legal name" value={editForm.legal_name} onChange={(e) => setEditForm({ ...editForm, legal_name: e.target.value })} />
          <Field label="Website" value={editForm.website} onChange={(e) => setEditForm({ ...editForm, website: e.target.value })} placeholder="https://" />
          <Field label="Industry" value={editForm.industry} onChange={(e) => setEditForm({ ...editForm, industry: e.target.value })} placeholder="IT Services" />
          <Field label="Headquarters" value={editForm.headquarters} onChange={(e) => setEditForm({ ...editForm, headquarters: e.target.value })} placeholder="Bangalore" />
          <label className="block"><span className="mb-1 block text-sm font-medium text-slate-700">Company size</span>
            <select value={editForm.company_size} onChange={(e) => setEditForm({ ...editForm, company_size: e.target.value })} className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm">
              <option value="">Select size</option>
              <option value="1-10">1-10</option>
              <option value="11-50">11-50</option>
              <option value="51-200">51-200</option>
              <option value="201-500">201-500</option>
              <option value="501-1000">501-1000</option>
              <option value="1000+">1000+</option>
            </select>
          </label>
          <label className="block sm:col-span-2"><span className="mb-1 block text-sm font-medium text-slate-700">Description</span>
            <textarea value={editForm.description} onChange={(e) => setEditForm({ ...editForm, description: e.target.value })} rows={2} className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
          </label>
        </div>
        <div className="mt-4 flex gap-2">
          <Button onClick={onSave} disabled={saving}>{saving ? 'Saving…' : 'Save'}</Button>
          <Button onClick={onCancel} className="bg-slate-600 hover:bg-slate-700">Cancel</Button>
        </div>
      </Card>
    )
  }

  return (
    <Card className="group relative flex flex-col overflow-hidden p-0 shadow-sm transition hover:shadow-md">
      <div className="h-1.5 w-full bg-gradient-to-r from-indigo-500 via-purple-500 to-indigo-500" />
      <div className="flex flex-1 flex-col p-5">
        <div className="flex items-start gap-3">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-600 to-purple-600 text-base font-bold text-white shadow-sm">{initials(c.name)}</div>
          <div className="min-w-0 flex-1">
            <div className="flex items-start justify-between gap-2">
              <h3 className="truncate pr-2 text-[15px] font-semibold leading-tight text-slate-900">{c.name}</h3>
              {c.industry && <Badge tone="indigo" className="shrink-0">{c.industry}</Badge>}
            </div>
            {c.legal_name && c.legal_name !== c.name && <p className="mt-0.5 truncate text-xs text-slate-500">{c.legal_name}</p>}
          </div>
        </div>

        <div className="mt-4 grid gap-2.5 text-sm">
          {/* Website */}
          {c.website ? (
            <a href={c.website} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1.5 truncate font-medium text-indigo-600 hover:underline">
              <span className="text-slate-400">🔗</span> <span className="truncate">{c.website}</span>
            </a>
          ) : (
            <span className="text-xs text-slate-400">No website</span>
          )}

          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="flex items-center gap-1.5 rounded-md bg-slate-50 px-2.5 py-2">
              <span>📍</span>
              <div className="min-w-0">
                <p className="text-[11px] font-medium uppercase tracking-wide text-slate-400">Headquarters</p>
                <p className="truncate font-medium text-slate-700">{c.headquarters || '—'}</p>
              </div>
            </div>
            <div className="flex items-center gap-1.5 rounded-md bg-slate-50 px-2.5 py-2">
              <span>👥</span>
              <div className="min-w-0">
                <p className="text-[11px] font-medium uppercase tracking-wide text-slate-400">Company size</p>
                <p className="truncate font-medium text-slate-700">{c.company_size || '—'}</p>
              </div>
            </div>
          </div>

          <div className="rounded-md bg-slate-50 px-2.5 py-2">
            <p className="text-[11px] font-medium uppercase tracking-wide text-slate-400">Industry</p>
            <p className="font-medium text-slate-700">{c.industry || '—'}</p>
          </div>

          {c.description ? (
            <div className="rounded-md border border-slate-100 bg-white px-2.5 py-2">
              <p className="text-[11px] font-medium uppercase tracking-wide text-slate-400">About</p>
              <p className="mt-1 line-clamp-3 text-sm leading-relaxed text-slate-700">{c.description}</p>
            </div>
          ) : (
            <p className="text-xs italic text-slate-400">No description added.</p>
          )}
        </div>

        <div className="mt-4 flex items-center justify-between border-t border-slate-100 pt-3">
          <span className="text-xs text-slate-400">All fields shown</span>
          {isAdmin && (
            <button onClick={() => onEdit(c)} className="rounded-md border border-indigo-200 bg-white px-3 py-1.5 text-xs font-medium text-indigo-600 transition hover:bg-indigo-50">Edit</button>
          )}
        </div>
      </div>
    </Card>
  )
}

export default function CompaniesPage() {
  const { user } = useAuth()
  const isAdmin = user?.role === 'admin'
  const [companies, setCompanies] = useState([])
  const [form, setForm] = useState({ name: '', legal_name: '', website: '', industry: '', headquarters: '', company_size: '', description: '' })
  const [error, setError] = useState(null)
  const [notice, setNotice] = useState(null)
  const [editingId, setEditingId] = useState(null)
  const [editForm, setEditForm] = useState({ name: '', legal_name: '', website: '', industry: '', headquarters: '', company_size: '', description: '' })
  const [saving, setSaving] = useState(false)

  async function load() {
    try { setCompanies(await api.listCompanies()) } catch (err) { setError(errorMessage(err)) }
  }
  useEffect(() => { void load() }, [])

  async function onCreate(e) {
    e.preventDefault()
    setError(null); setNotice(null)
    try {
      await api.createCompany(form)
      setNotice(`Company "${form.name}" created.`)
      setForm({ name: '', legal_name: '', website: '', industry: '', headquarters: '', company_size: '', description: '' })
      await load()
    } catch (err) { setError(errorMessage(err)) }
  }

  function startEdit(c) {
    setError(null); setNotice(null)
    setEditingId(c.id)
    setEditForm({
      name: c.name || '',
      legal_name: c.legal_name || '',
      website: c.website || '',
      industry: c.industry || '',
      headquarters: c.headquarters || '',
      company_size: c.company_size || '',
      description: c.description || '',
    })
  }

  async function onSaveEdit() {
    if (!editingId) return
    setSaving(true); setError(null)
    try {
      await api.updateCompany(editingId, editForm)
      setNotice('Company updated.')
      setEditingId(null)
      await load()
    } catch (err) { setError(errorMessage(err)) }
    finally { setSaving(false) }
  }

  return (
    <div className="mx-auto max-w-5xl">
      <PageTitle>Companies</PageTitle>
      <p className="mb-4 text-sm text-slate-600">Reusable across drives. Each drive links to one company; TNPC can reuse TCS across 2027/2028 drives.</p>
      <ErrorBanner message={error} />
      {notice && <div className="mb-4 rounded-md border border-green-200 bg-green-50 px-4 py-2 text-sm text-green-700">{notice}</div>}

      {isAdmin ? (
        <Card className="mb-8">
          <h2 className="mb-3 font-semibold">Create Company</h2>
          <form onSubmit={onCreate} className="grid gap-3 sm:grid-cols-2">
            <Field label="Name *" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
            <Field label="Legal name" value={form.legal_name} onChange={(e) => setForm({ ...form, legal_name: e.target.value })} />
            <Field label="Website" type="url" value={form.website} onChange={(e) => setForm({ ...form, website: e.target.value })} placeholder="https://" />
            <Field label="Industry" value={form.industry} onChange={(e) => setForm({ ...form, industry: e.target.value })} placeholder="IT Services" />
            <Field label="Headquarters" value={form.headquarters} onChange={(e) => setForm({ ...form, headquarters: e.target.value })} placeholder="Bangalore" />
            <label className="block"><span className="mb-1 block text-sm font-medium text-slate-700">Company size</span>
              <select value={form.company_size} onChange={(e) => setForm({ ...form, company_size: e.target.value })} className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500">
                <option value="">Select size</option>
                <option value="1-10">1-10</option>
                <option value="11-50">11-50</option>
                <option value="51-200">51-200</option>
                <option value="201-500">201-500</option>
                <option value="501-1000">501-1000</option>
                <option value="1000+">1000+</option>
              </select>
            </label>
            <label className="block sm:col-span-2"><span className="mb-1 block text-sm font-medium text-slate-700">Description</span>
              <textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} rows={2} placeholder="Short company overview" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500" />
            </label>
            <div className="flex items-end sm:col-span-2"><Button type="submit">Create</Button></div>
          </form>
        </Card>
      ) : (
        <Card className="mb-8 border-dashed bg-slate-50">
          <p className="text-sm text-slate-600">Only TNPC Admin can create companies. Student view is read-only.</p>
        </Card>
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        {companies.map((c) => (
          <CompanyCard
            key={c.id}
            c={c}
            isAdmin={isAdmin}
            onEdit={startEdit}
            editing={editingId === c.id}
            editForm={editForm}
            setEditForm={setEditForm}
            onSave={onSaveEdit}
            onCancel={() => setEditingId(null)}
            saving={saving}
          />
        ))}
        {companies.length === 0 && <p className="text-sm text-slate-500">No companies yet. Create one above to reuse across drives.</p>}
      </div>
    </div>
  )
}
