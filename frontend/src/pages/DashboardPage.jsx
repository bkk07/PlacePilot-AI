import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Badge, Card, ErrorBanner, PageTitle } from '../components/ui.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import { api, errorMessage } from '../lib/api.js'

export default function DashboardPage() {
  const { user } = useAuth()
  const isAdmin = user?.role === 'admin'
  const [profile, setProfile] = useState(null)
  const [applications, setApplications] = useState([])
  const [companies, setCompanies] = useState([])
  const [drives, setDrives] = useState([])
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        if (isAdmin) {
          const [apps, comps, drs] = await Promise.all([
            api.listApplications(),
            api.listCompanies().catch(() => []),
            api.listDrives().catch(() => []),
          ])
          if (cancelled) return
          setApplications(apps)
          setCompanies(comps)
          setDrives(drs)
        } else {
          const [apps, prof, drs] = await Promise.all([
            api.listApplications(),
            api.getProfile().catch(() => null),
            api.listDrives().catch(() => []),
          ])
          if (cancelled) return
          setApplications(apps)
          setProfile(prof)
          setDrives(drs)
        }
      } catch (err) {
        if (!cancelled) setError(errorMessage(err))
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    void load()
    return () => {
      cancelled = true
    }
  }, [isAdmin])

  const active = applications.filter((a) => !['rejected', 'withdrawn'].includes(a.status))

  if (isAdmin) {
    return (
      <div>
        <PageTitle>TNPC Dashboard — Welcome, {user?.full_name?.split(' ')[0] ?? 'Admin'}</PageTitle>
        <ErrorBanner message={error} />
        {loading ? (
          <p className="text-slate-500">Loading…</p>
        ) : (
          <div className="grid gap-4 md:grid-cols-3">
            <Card>
              <p className="text-sm text-slate-500">Total Applications</p>
              <p className="mt-1 text-3xl font-semibold text-slate-900">{applications.length}</p>
              <Link to="/applications" className="text-sm font-medium text-indigo-600 hover:underline">View all →</Link>
            </Card>
            <Card>
              <p className="text-sm text-slate-500">Companies</p>
              <p className="mt-1 text-3xl font-semibold text-slate-900">{companies.length}</p>
              <Link to="/companies" className="text-sm font-medium text-indigo-600 hover:underline">Manage companies →</Link>
            </Card>
            <Card>
              <p className="text-sm text-slate-500">Open Drives</p>
              <p className="mt-1 text-3xl font-semibold text-slate-900">{drives.length}</p>
              <div className="mt-2 flex flex-col gap-1">
                <Link to="/drives/new" className="text-sm font-medium text-indigo-600 hover:underline">Create Drive →</Link>
                <Link to="/drives" className="text-sm font-medium text-indigo-600 hover:underline">View drives →</Link>
              </div>
            </Card>
            <Card className="md:col-span-3">
              <h2 className="mb-3 text-base font-semibold text-slate-900">TNPC Quick Actions</h2>
              <div className="flex flex-wrap gap-2">
                <Link to="/companies" className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700">Add Company</Link>
                <Link to="/drives/new" className="rounded-md border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100">Create Drive</Link>
                <Link to="/chat" className="rounded-md border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100">Ask AI about drives</Link>
              </div>
              <p className="mt-3 text-xs text-slate-500">As TNPC Admin you can create companies, drives with multiple job positions, set eligibility (CGPA/branches/batches), define rounds & schedules, publish drives, and track the full pipeline: Application → Shortlist → Round Results → Selection → Offer → Placement Outcome.</p>
            </Card>
          </div>
        )}
      </div>
    )
  }

  return (
    <div>
      <PageTitle>Welcome back, {user?.full_name?.split(' ')[0] ?? 'student'}</PageTitle>
      <ErrorBanner message={error} />
      {loading ? (
        <p className="text-slate-500">Loading…</p>
      ) : (
        <div className="grid gap-4 md:grid-cols-3">
          <Card>
            <p className="text-sm text-slate-500">Profile</p>
            {profile ? (
              <>
                <p className="mt-1 text-lg font-semibold text-slate-900">
                  {profile.branch} · {profile.graduation_year}
                </p>
                <p className="text-sm text-slate-600">
                  CGPA {profile.cgpa ?? '—'} · {profile.active_backlogs} backlog(s)
                </p>
              </>
            ) : (
              <>
                <p className="mt-1 text-lg font-semibold text-slate-900">Not completed</p>
                <Link to="/profile" className="text-sm font-medium text-indigo-600 hover:underline">
                  Complete your profile →
                </Link>
              </>
            )}
          </Card>
          <Card>
            <p className="text-sm text-slate-500">Active applications</p>
            <p className="mt-1 text-3xl font-semibold text-slate-900">{active.length}</p>
            <Link to="/applications" className="text-sm font-medium text-indigo-600 hover:underline">
              View applications →
            </Link>
          </Card>
          <Card>
            <p className="text-sm text-slate-500">Open drives</p>
            <Link
              to="/drives"
              className="mt-1 block text-lg font-semibold text-indigo-600 hover:underline"
            >
              Browse drives →
            </Link>
            <Link to="/chat" className="text-sm font-medium text-indigo-600 hover:underline">
              Ask the AI assistant →
            </Link>
          </Card>
          <Card className="md:col-span-3">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-base font-semibold text-slate-900">Recent drives</h2>
              <Link to="/drives" className="text-xs font-medium text-indigo-600 hover:underline">View all →</Link>
            </div>
            {drives.length === 0 ? (
              <p className="text-sm text-slate-500">No open drives right now. Check back soon.</p>
            ) : (
              <ul className="divide-y divide-slate-100">
                {drives.slice(0, 5).map((d) => (
                  <li key={d.id} className="flex items-center justify-between py-2.5">
                    <div>
                      <Link to={`/drives/${d.id}`} className="text-sm font-medium text-slate-800 hover:text-indigo-600">{d.title}</Link>
                      <p className="text-xs text-slate-500">{d.company} · {d.role} · {d.location} {d.ctc_lpa ? `· ${d.ctc_lpa} LPA` : ''}</p>
                    </div>
                    <Badge tone="green">{d.status}</Badge>
                  </li>
                ))}
              </ul>
            )}
          </Card>
          {applications.length > 0 && (
            <Card className="md:col-span-3">
              <h2 className="mb-3 text-base font-semibold text-slate-900">Recent applications</h2>
              <ul className="divide-y divide-slate-100">
                {applications.slice(0, 5).map((app) => (
                  <li key={app.id} className="flex items-center justify-between py-2">
                    <span className="text-sm text-slate-700">{app.drive_title}</span>
                    <Badge tone={app.status === 'rejected' ? 'red' : 'indigo'}>{app.status}</Badge>
                  </li>
                ))}
              </ul>
            </Card>
          )}
        </div>
      )}
    </div>
  )
}