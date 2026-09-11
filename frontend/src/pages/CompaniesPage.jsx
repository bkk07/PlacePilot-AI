import { useEffect, useState } from 'react'
import { Badge, Button, Card, ErrorBanner, Field, PageTitle } from '../components/ui.jsx'
import { api, errorMessage } from '../lib/api.js'

export default function CompaniesPage() {
  const [companies, setCompanies] = useState([])
  const [form, setForm] = useState({ name: '', legal_name: '', website: '', industry: '', headquarters: '' })
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
      setForm({ name: '', legal_name: '', website: '', industry: '', headquarters: '' })
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
          <Field label="Industry" value={form.industry} onChange={(e) => setForm({ ...form, industry: e.target.value })} />
          <Field label="Headquarters" value={form.headquarters} onChange={(e) => setForm({ ...form, headquarters: e.target.value })} />
          <div className="flex items-end"><Button type="submit">Create</Button></div>
        </form>
      </Card>

      <div className="grid gap-3 sm:grid-cols-2">
        {companies.map((c) => (
          <Card key={c.id}>
            <h3 className="font-semibold">{c.name}</h3>
            <p className="text-sm text-slate-600">{c.industry || '—'} {c.headquarters ? `· ${c.headquarters}` : ''}</p>
            {c.description && <p className="mt-2 text-sm text-slate-700 line-clamp-2">{c.description}</p>}
            <div className="mt-2"><Badge>{c.company_size || '—'}</Badge></div>
          </Card>
        ))}
        {companies.length === 0 && <p className="text-sm text-slate-500">No companies yet.</p>}
      </div>
    </div>
  )
}
