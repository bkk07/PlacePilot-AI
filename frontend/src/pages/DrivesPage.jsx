import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Badge, Button, Card, ErrorBanner, Field, PageTitle } from '../components/ui.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import { api, errorMessage } from '../lib/api.js'

function salaryLabel(drive) {
  if (drive.ctc_lpa) return `${drive.ctc_lpa} LPA`
  if (drive.stipend_monthly) return `₹${drive.stipend_monthly.toLocaleString()}/mo`
  return '—'
}

export default function DrivesPage() {
  const { user } = useAuth()
  const isAdmin = user?.role === 'admin'
  const [drives, setDrives] = useState([])
  const [query, setQuery] = useState('')
  const [company, setCompany] = useState('')
  const [role, setRole] = useState('')
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)

  async function load(filters) {
    setLoading(true)
    setError(null)
    try {
      setDrives(await api.listDrives(filters))
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load({})
  }, [])

  function onSearch(e) {
    e.preventDefault()
    void load({ query, company, role })
  }

  return (
    <div>
      <div className="flex items-center justify-between">
        <PageTitle>Placement drives</PageTitle>
        {isAdmin && (
          <Link to="/drives/new" className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700">
            + Create Drive
          </Link>
        )}
      </div>
      <ErrorBanner message={error} />
      <Card className="mb-4">
        <form onSubmit={onSearch} className="grid gap-3 md:grid-cols-4">
          <Field label="Search" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="python, remote…" />
          <Field label="Company" value={company} onChange={(e) => setCompany(e.target.value)} placeholder="Nimbus" />
          <Field label="Role" value={role} onChange={(e) => setRole(e.target.value)} placeholder="Engineer" />
          <div className="flex items-end">
            <Button type="submit" className="w-full">
              Filter
            </Button>
          </div>
        </form>
      </Card>
      {loading ? (
        <p className="text-slate-500">Loading drives…</p>
      ) : drives.length === 0 ? (
        <Card>
          <p className="text-sm text-slate-600">No drives matched your filters.</p>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {drives.map((drive) => (
            <Card key={drive.id}>
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h2 className="text-base font-semibold text-slate-900">{drive.title}</h2>
                  <p className="text-sm text-slate-600">
                    {drive.company} · {drive.location}
                  </p>
                </div>
                <Badge tone="green">{drive.status}</Badge>
              </div>
              <dl className="mt-3 grid grid-cols-2 gap-2 text-sm">
                <div>
                  <dt className="text-slate-500">Compensation</dt>
                  <dd className="font-medium text-slate-900">{salaryLabel(drive)}</dd>
                </div>
                <div>
                  <dt className="text-slate-500">Deadline</dt>
                  <dd className="font-medium text-slate-900">{drive.application_deadline}</dd>
                </div>
              </dl>
              {drive.skills.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {drive.skills.map((skill) => (
                    <Badge key={skill}>{skill}</Badge>
                  ))}
                </div>
              )}
              <Link
                to={`/drives/${drive.id}`}
                className="mt-4 inline-block text-sm font-medium text-indigo-600 hover:underline"
              >
                View details →
              </Link>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}