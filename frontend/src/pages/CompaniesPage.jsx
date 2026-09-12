import { useEffect, useState } from 'react'
import { Badge, Button, Card, ErrorBanner, Field, PageTitle } from '../components/ui.jsx'
import { api, errorMessage } from '../lib/api.js'

export default function CompaniesPage() {
  const [companies, setCompanies] = useState([])
  const [form, setForm] = useState({ name: '', legal_name: '', website: '', industry: '', headquarters: '', company_size: '', description: '' })
  const [error, setError] = useState(null)
  const [notice, setNotice] = useState(null)

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

  return (
    <div className="mx-auto max-w-4xl">
      <PageTitle>Companies</PageTitle>
      <p className="mb-4 text-sm text-slate-600">Reusable across drives. Each drive links to one company; TNPC can reuse TCS across 2027/2028 drives.</p>
      <ErrorBanner message={error} />
      {notice && <div className="mb-4 rounded-md border border-green-200 bg-green-50 px-4 py-2 text-sm text-green-700">{notice}</div>}

      <Card className="mb-6">
        <h2 className="mb-3 font-semibold">Create Company</h2>
        <form onSubmit={onCreate} className="grid gap-3 sm:grid-cols-2">
          <Field label="Name *" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
          <Field label="Legal name" value={form.legal_name} onChange={(e) => setForm({ ...form, legal_name: e.target.value })} />
          <Field label="Website" value={form.website} onChange={(e) => setForm({ ...form, website: e.target.value })} placeholder="https://" />
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

      <div className="grid gap-4 sm:grid-cols-2">
        {companies.map((c) => (
          <Card key={c.id} className="flex flex-col">
            <div className="flex items-start justify-between gap-2">
              <h3 className="font-semibold text-slate-900">{c.name}</h3>
              {c.industry && <Badge tone="indigo">{c.industry}</Badge>}
            </div>
            {c.legal_name && c.legal_name !== c.name && <p className="text-xs text-slate-500">{c.legal_name}</p>}
            <div className="mt-3 space-y-1.5 text-sm text-slate-600">
              {c.website && <a href={c.website} target="_blank" rel="noreferrer" className="block truncate font-medium text-indigo-600 hover:underline">{c.website}</a>}
              {c.headquarters && <p className="flex items-center gap-1.5"><span>📍</span> {c.headquarters}</p>}
              {c.company_size && <p className="flex items-center gap-1.5"><span>👥</span> {c.company_size}</p>}
            </div>
            {c.description && <p className="mt-3 line-clamp-3 text-sm text-slate-700">{c.description}</p>}
            {!c.website && !c.headquarters && !c.company_size && !c.description && !c.legal_name && (
              <p className="mt-3 text-xs text-slate-400">No additional details — edit to add website, HQ, size.</p>
            )}
          </Card>
        ))}
        {companies.length === 0 && <p className="text-sm text-slate-500">No companies yet. Create one above to reuse across drives.</p>}
      </div>
    </div>
  )
}
