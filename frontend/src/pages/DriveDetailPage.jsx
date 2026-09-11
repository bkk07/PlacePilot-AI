import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { Badge, Button, Card, ErrorBanner, PageTitle } from '../components/ui.jsx'
import { api, ApiError, errorMessage } from '../lib/api.js'

export default function DriveDetailPage() {
  const { driveId = '' } = useParams()
  const [drive, setDrive] = useState(null)
  const [eligibility, setEligibility] = useState(null)
  const [error, setError] = useState(null)
  const [notice, setNotice] = useState(null)
  const [applied, setApplied] = useState(false)
  const [loading, setLoading] = useState(true)
  const [applying, setApplying] = useState(false)

  const checkEligibility = useCallback(async () => {
    try {
      setEligibility(await api.checkEligibility(driveId))
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setEligibility(null)
      } else {
        setError(errorMessage(err))
      }
    }
  }, [driveId])

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const d = await api.getDrive(driveId)
        if (!cancelled) setDrive(d)
        await checkEligibility()
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
  }, [driveId, checkEligibility])

  async function onApply() {
    setApplying(true)
    setError(null)
    setNotice(null)
    try {
      await api.apply(driveId)
      setApplied(true)
      setNotice('Application submitted.')
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setApplying(false)
    }
  }

  if (loading) return <p className="text-slate-500">Loading…</p>
  if (!drive) return <ErrorBanner message={error ?? 'Drive not found'} />

  return (
    <div className="mx-auto max-w-3xl">
      <Link to="/drives" className="text-sm font-medium text-indigo-600 hover:underline">
        ← Back to drives
      </Link>
      <PageTitle>{drive.title}</PageTitle>
      <ErrorBanner message={error} />
      {notice && (
        <div className="mb-4 rounded-md border border-green-200 bg-green-50 px-4 py-2 text-sm text-green-700">
          {notice}
        </div>
      )}
      <Card className="mb-4">
        <dl className="grid gap-3 sm:grid-cols-2">
          <div>
            <dt className="text-sm text-slate-500">Company</dt>
            <dd className="font-medium text-slate-900">{drive.company}</dd>
          </div>
          <div>
            <dt className="text-sm text-slate-500">Role</dt>
            <dd className="font-medium text-slate-900">{drive.role}</dd>
          </div>
          <div>
            <dt className="text-sm text-slate-500">Compensation</dt>
            <dd className="font-medium text-slate-900">
              {drive.ctc_lpa ? `${drive.ctc_lpa} LPA` : '—'}
              {drive.stipend_monthly ? ` · ₹${drive.stipend_monthly.toLocaleString()}/mo` : ''}
            </dd>
          </div>
          <div>
            <dt className="text-sm text-slate-500">Location</dt>
            <dd className="font-medium text-slate-900">{drive.location}</dd>
          </div>
          <div>
            <dt className="text-sm text-slate-500">Deadline</dt>
            <dd className="font-medium text-slate-900">{drive.application_deadline}</dd>
          </div>
          <div>
            <dt className="text-sm text-slate-500">Status</dt>
            <dd>
              <Badge tone="green">{drive.status}</Badge>
            </dd>
          </div>
        </dl>
        {drive.skills.length > 0 && (
          <div className="mt-4 flex flex-wrap gap-1.5">
            {drive.skills.map((skill) => (
              <Badge key={skill}>{skill}</Badge>
            ))}
          </div>
        )}
      </Card>

      <Card className="mb-4">
        <h2 className="mb-2 text-base font-semibold text-slate-900">Eligibility</h2>
        {eligibility ? (
          <>
            <Badge tone={eligibility.eligible ? 'green' : 'red'}>
              {eligibility.eligible ? 'Eligible' : 'Not eligible'}
            </Badge>
            <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-slate-700">
              {eligibility.reasons.map((reason) => (
                <li key={reason}>{reason}</li>
              ))}
            </ul>
          </>
        ) : (
          <p className="text-sm text-slate-600">
            Complete your profile to see your eligibility for this drive.
          </p>
        )}
      </Card>

      <Button
        onClick={onApply}
        disabled={applying || applied || !eligibility?.eligible || drive.status !== 'open'}
      >
        {applied ? 'Applied' : applying ? 'Submitting…' : 'Apply'}
      </Button>
    </div>
  )
}