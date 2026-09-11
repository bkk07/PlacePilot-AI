import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Badge, Button, Card, ErrorBanner, PageTitle } from '../components/ui.jsx'
import { api, errorMessage } from '../lib/api.js'

const TONES = {
  applied: 'indigo',
  shortlisted: 'amber',
  interview: 'amber',
  offer: 'green',
  selected: 'green',
  rejected: 'red',
  withdrawn: 'slate',
}

export default function ApplicationsPage() {
  const [applications, setApplications] = useState([])
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)
  const [busyId, setBusyId] = useState(null)

  async function load() {
    setLoading(true)
    try {
      setApplications(await api.listApplications())
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [])

  async function onWithdraw(id) {
    setBusyId(id)
    setError(null)
    try {
      await api.withdraw(id)
      await load()
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusyId(null)
    }
  }

  return (
    <div>
      <PageTitle>My applications</PageTitle>
      <ErrorBanner message={error} />
      {loading ? (
        <p className="text-slate-500">Loading…</p>
      ) : applications.length === 0 ? (
        <Card>
          <p className="text-sm text-slate-600">
            No applications yet.{' '}
            <Link to="/drives" className="font-medium text-indigo-600 hover:underline">
              Browse drives
            </Link>
          </p>
        </Card>
      ) : (
        <div className="space-y-3">
          {applications.map((app) => {
            const canWithdraw = !['withdrawn', 'rejected', 'selected'].includes(app.status)
            return (
              <Card key={app.id} className="flex items-center justify-between gap-4">
                <div>
                  <Link
                    to={`/drives/${app.drive_id}`}
                    className="font-medium text-slate-900 hover:text-indigo-600"
                  >
                    {app.drive_title}
                  </Link>
                  <p className="text-xs text-slate-500">
                    Applied {new Date(app.created_at).toLocaleDateString()}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <Badge tone={TONES[app.status] ?? 'slate'}>{app.status}</Badge>
                  {canWithdraw && (
                    <Button
                      onClick={() => onWithdraw(app.id)}
                      disabled={busyId === app.id}
                      className="bg-slate-600 hover:bg-slate-700"
                    >
                      {busyId === app.id ? 'Withdrawing…' : 'Withdraw'}
                    </Button>
                  )}
                </div>
              </Card>
            )
          })}
        </div>
      )}
    </div>
  )
}