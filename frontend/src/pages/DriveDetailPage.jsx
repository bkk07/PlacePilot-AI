import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { Badge, Button, Card, ErrorBanner, PageTitle } from '../components/ui.jsx'
import { api, ApiError, errorMessage } from '../lib/api.js'

function compLabel(c) {
  if (!c) return '—'
  if (c.is_unpaid) return 'Unpaid'
  const parts = []
  if (c.ctc_min != null || c.ctc_max != null) {
    if (c.ctc_min != null && c.ctc_max != null && c.ctc_min !== c.ctc_max) parts.push(`${c.ctc_min}-${c.ctc_max} LPA`)
    else parts.push(`${c.ctc_min ?? c.ctc_max ?? c.annual_ctc} LPA`)
  } else if (c.annual_ctc) parts.push(`${c.annual_ctc} LPA`)
  if (c.stipend_min != null || c.stipend_max != null) {
    if (c.stipend_min != null && c.stipend_max != null && c.stipend_min !== c.stipend_max) parts.push(`₹${Number(c.stipend_min).toLocaleString()}-₹${Number(c.stipend_max).toLocaleString()}/mo`)
    else parts.push(`₹${Number(c.stipend_min ?? c.stipend_max ?? c.monthly_stipend).toLocaleString()}/mo`)
  } else if (c.monthly_stipend) parts.push(`₹${Number(c.monthly_stipend).toLocaleString()}/mo`)
  return parts.join(' · ') || '—'
}

export default function DriveDetailPage() {
  const { driveId = '' } = useParams()
  const [drive, setDrive] = useState(null)
  const [positions, setPositions] = useState([])
  const [eligibility, setEligibility] = useState(null)
  const [error, setError] = useState(null)
  const [notice, setNotice] = useState(null)
  const [appliedMap, setAppliedMap] = useState({}) // positionId -> true
  const [loading, setLoading] = useState(true)
  const [applyingId, setApplyingId] = useState(null)
  const [expanded, setExpanded] = useState({})

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
        const pos = await api.listJobPositions(driveId).catch(() => [])
        if (!cancelled) setPositions(Array.isArray(pos) ? pos : [])
        await checkEligibility()
        // fetch my applications to mark applied
        try {
          const apps = await api.listApplications()
          const map = {}
          for (const a of apps) {
            if (a.drive_id === driveId) {
              // if app has job_position_id, mark that, else mark drive-level
              // fallback: if no position_id, mark all as applied? we mark drive-level flag
              // Our backend now includes job_position_id in Application but ApplicationOut doesn't expose it; handle both
              if (a.job_position_id) map[a.job_position_id] = true
              else map['__drive__'] = true
            }
          }
          if (!cancelled) setAppliedMap(map)
        } catch {}
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

  async function onApply(positionId) {
    setApplyingId(positionId || '__drive__')
    setError(null)
    setNotice(null)
    try {
      await api.apply(driveId, positionId || null)
      setAppliedMap((m) => ({ ...m, [positionId || '__drive__']: true }))
      setNotice(positionId ? 'Application submitted for this role.' : 'Application submitted.')
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setApplyingId(null)
    }
  }

  if (loading) return <p className="text-slate-500">Loading…</p>
  if (!drive) return <ErrorBanner message={error ?? 'Drive not found'} />

  const driveApplied = !!appliedMap['__drive__']

  return (
    <div className="mx-auto max-w-4xl">
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
            <dt className="text-sm text-slate-500">Drive Type / Mode</dt>
            <dd className="font-medium text-slate-900">{drive.drive_type} · {drive.mode}</dd>
          </div>
          <div>
            <dt className="text-sm text-slate-500">Location(s)</dt>
            <dd className="font-medium text-slate-900">{drive.locations_union?.length ? drive.locations_union.join(', ') : drive.location}</dd>
          </div>
          <div>
            <dt className="text-sm text-slate-500">Deadline</dt>
            <dd className="font-medium text-slate-900">{drive.application_deadline}</dd>
          </div>
          <div>
            <dt className="text-sm text-slate-500">Status</dt>
            <dd>
              <Badge tone="green">{drive.status}</Badge> {drive.roles_count ? <Badge tone="indigo" className="ml-2">{drive.roles_count} Roles</Badge> : null}
            </dd>
          </div>
          <div>
            <dt className="text-sm text-slate-500">Registration</dt>
            <dd className="font-medium text-slate-900 text-xs">{drive.registration_start ? new Date(drive.registration_start).toLocaleString() : '—'} → {drive.registration_end ? new Date(drive.registration_end).toLocaleString() : '—'}</dd>
          </div>
        </dl>
        {drive.description && <p className="mt-4 text-sm text-slate-700">{drive.description}</p>}
        {drive.venue && <p className="mt-2 text-sm text-slate-600">Venue: {drive.venue} {drive.meeting_link && <a href={drive.meeting_link} className="text-indigo-600 hover:underline">· Meeting Link</a>}</p>}
        {drive.skills_union?.length > 0 && (
          <div className="mt-4 flex flex-wrap gap-1.5">
            {drive.skills_union.map((skill) => (
              <Badge key={skill}>{skill}</Badge>
            ))}
          </div>
        )}
        {!drive.skills_union?.length && drive.skills.length > 0 && (
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

      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-900">Roles ({positions.length})</h2>
        {positions.length > 1 && <p className="text-xs text-slate-500">Compare roles — each has separate compensation, bond & skills</p>}
      </div>

      {positions.length === 0 ? (
        <Card>
          <p className="text-sm text-slate-600">No roles added yet. {drive.status === 'open' && !drive.roles_count ? <span>TNPC will add roles soon.</span> : null}</p>
          {!driveApplied && eligibility?.eligible && drive.status === 'open' && positions.length === 0 && (
            <Button onClick={() => onApply(null)} disabled={!!applyingId} className="mt-3">{applyingId ? 'Submitting…' : 'Apply to Drive'}</Button>
          )}
          {driveApplied && <Badge tone="green" className="mt-3">Applied</Badge>}
        </Card>
      ) : (
        <div className="grid gap-4">
          {positions.map((p) => {
            const isApplied = !!appliedMap[p.id]
            const isExpanded = !!expanded[p.id]
            return (
              <Card key={p.id} className="relative">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h3 className="text-base font-semibold text-slate-900">{p.title} <span className="text-sm font-normal text-slate-500">· {p.role}</span></h3>
                    <p className="text-xs text-slate-600">{p.department ? `${p.department} · ` : ''}{p.employment_type} · {p.work_mode} {p.openings ? `· ${p.openings} openings` : ''}</p>
                  </div>
                  <div className="flex flex-col items-end gap-1">
                    <Badge tone={p.employment_type === 'INTERNSHIP' ? 'amber' : p.employment_type === 'FULL_TIME' ? 'green' : 'indigo'}>{p.employment_type}</Badge>
                    {p.bond_required && <Badge tone="red">🔒 Bond {p.bond_duration_months ? `${p.bond_duration_months}mo` : ''}</Badge>}
                  </div>
                </div>

                <dl className="mt-3 grid grid-cols-2 gap-2 text-sm">
                  <div>
                    <dt className="text-slate-500">Compensation</dt>
                    <dd className="font-medium text-slate-900">{compLabel(p.compensation)}</dd>
                    {p.compensation?.is_unpaid && <span className="text-xs text-amber-700">Unpaid</span>}
                    {p.compensation?.currency && <span className="text-xs text-slate-500"> · {p.compensation.currency}</span>}
                  </div>
                  <div>
                    <dt className="text-slate-500">Location(s)</dt>
                    <dd className="font-medium text-slate-900">{p.locations?.length ? p.locations.map((l) => l.city).join(', ') : '—'}</dd>
                  </div>
                </dl>

                {/* Skills */}
                {p.skills?.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-1.5">
                    {p.skills.map((s) => (
                      <span key={s.skill_id} className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ${s.mandatory ? 'bg-indigo-100 text-indigo-700' : 'bg-slate-100 text-slate-600 border border-dashed'}`}>
                        {s.name} {s.mandatory ? '●' : '○'} <span className="text-[10px]">{s.skill_level}</span>
                      </span>
                    ))}
                  </div>
                )}

                {/* Expand details */}
                <button onClick={() => setExpanded((e) => ({ ...e, [p.id]: !e[p.id] }))} className="mt-3 text-xs font-medium text-indigo-600 hover:underline">{isExpanded ? 'Hide details ▲' : 'View details ▼'}</button>
                {isExpanded && (
                  <div className="mt-3 space-y-2 border-t pt-3 text-sm">
                    {p.job_description && <p className="text-slate-700">{p.job_description}</p>}
                    {p.bond_required && (
                      <div className="rounded-md bg-amber-50 border border-amber-200 p-2 text-xs text-amber-800">
                        <b>Bond:</b> {p.bond_duration_months ? `${p.bond_duration_months} months` : 'Required'} {p.bond_amount ? `· ₹${Number(p.bond_amount).toLocaleString()}` : ''} {p.bond_description ? `· ${p.bond_description}` : ''}
                      </div>
                    )}
                    {p.internship && (
                      <p className="text-xs text-slate-600">Internship: {p.internship.duration_months ? `${p.internship.duration_months} months` : ''} {p.internship.ppo_available ? '· PPO available' : ''} {p.internship.ppo_criteria ? `· ${p.internship.ppo_criteria}` : ''}</p>
                    )}
                    {p.locations?.length > 0 && <p className="text-xs text-slate-600">Work locations: {p.locations.map((l) => [l.city, l.state].filter(Boolean).join(', ')).join(' | ')}</p>}
                  </div>
                )}

                <div className="mt-4">
                  <Button
                    onClick={() => onApply(p.id)}
                    disabled={!!applyingId || isApplied || !eligibility?.eligible || drive.status !== 'open'}
                    className={isApplied ? 'bg-green-600 hover:bg-green-700' : ''}
                  >
                    {isApplied ? 'Applied ✓' : applyingId === p.id ? 'Submitting…' : 'Apply to this Role'}
                  </Button>
                  {!eligibility?.eligible && <span className="ml-2 text-xs text-red-600">Not eligible</span>}
                </div>
              </Card>
            )
          })}
        </div>
      )}
    </div>
  )
}
