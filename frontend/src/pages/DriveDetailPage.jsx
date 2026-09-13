import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { Badge, Button, Card, ErrorBanner, Field, PageTitle } from '../components/ui.jsx'
import { api, ApiError, errorMessage } from '../lib/api.js'
import { useAuth } from '../context/AuthContext.jsx'

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
  const { user } = useAuth()
  const isAdmin = user?.role === 'admin'
  const [drive, setDrive] = useState(null)
  const [positions, setPositions] = useState([])
  const [eligibility, setEligibility] = useState(null)
  const [error, setError] = useState(null)
  const [notice, setNotice] = useState(null)
  const [appliedMap, setAppliedMap] = useState({}) // positionId -> true
  const [loading, setLoading] = useState(true)
  const [applyingId, setApplyingId] = useState(null)
  const [expanded, setExpanded] = useState({})
  const [isEditing, setIsEditing] = useState(false)
  const [editForm, setEditForm] = useState(null)
  const [companies, setCompanies] = useState([])
  const [savingEdit, setSavingEdit] = useState(false)
  const [publishing, setPublishing] = useState(false)
  const [applicants, setApplicants] = useState([])
  const [appsLoading, setAppsLoading] = useState(false)
  const [updatingId, setUpdatingId] = useState(null)

  const isOpenStatus = useCallback((s) => ['open', 'OPEN', 'PUBLISHED', 'REGISTRATION_OPEN'].includes(String(s)), [])

  const checkEligibility = useCallback(async () => {
    if (isAdmin) { setEligibility(null); return }
    try {
      const res = await api.checkEligibility(driveId)
      setEligibility(res)
    } catch (err) {
      if (err instanceof ApiError && (err.status === 409 || err.status === 403 || err.status === 404)) {
        setEligibility({ eligible: false, reasons: [errorMessage(err)], missing_requirements: [] })
      } else {
        setError(errorMessage(err))
      }
    }
  }, [driveId, isAdmin])

  function toLocalInput(iso) {
    if (!iso) return ''
    const d = new Date(iso)
    if (isNaN(d.getTime())) return ''
    const pad = (n) => String(n).padStart(2, '0')
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
  }

  function startEdit() {
    if (!drive) return
    setEditForm({
      company_id: drive.company_id || '',
      title: drive.title || '',
      description: drive.description || '',
      drive_type: drive.drive_type || 'ON_CAMPUS',
      mode: drive.mode || 'OFFLINE',
      registration_start: toLocalInput(drive.registration_start),
      registration_end: toLocalInput(drive.registration_end),
      application_deadline: drive.application_deadline || '',
      application_limit: drive.application_limit ?? '',
      instructions: drive.instructions || '',
      status: drive.status || 'open',
    })
    setIsEditing(true)
    setError(null)
    if (companies.length === 0) {
      api.listCompanies().then(setCompanies).catch(() => {})
    }
  }

  function cancelEdit() {
    setIsEditing(false)
    setEditForm(null)
  }

  async function saveEdit(e) {
    e?.preventDefault()
    if (!editForm) return
    setSavingEdit(true)
    setError(null)
    try {
      const payload = {
        company_id: editForm.company_id || undefined,
        title: editForm.title?.trim(),
        description: editForm.description || null,
        drive_type: editForm.drive_type,
        mode: editForm.mode,
        registration_start: editForm.registration_start || null,
        registration_end: editForm.registration_end || null,
        application_deadline: editForm.application_deadline || null,
        application_limit: editForm.application_limit === '' || editForm.application_limit == null ? null : Number(editForm.application_limit),
        instructions: editForm.instructions || null,
        status: editForm.status,
      }
      if (!payload.title) throw new Error('Title is required')
      const updated = await api.updateDrive(driveId, payload)
      setDrive(updated)
      setIsEditing(false)
      setNotice('Drive updated.')
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setSavingEdit(false)
    }
  }

  async function handlePublish() {
    setError(null); setNotice(null)
    setPublishing(true)
    try {
      await api.publishDrive(driveId)
      const updated = await api.getDrive(driveId)
      setDrive(updated)
      setNotice('Drive published — now open for students.')
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setPublishing(false)
    }
  }

  const loadApplicants = useCallback(async () => {
    if (!isAdmin) return
    setAppsLoading(true)
    try {
      const data = await api.listDriveApplications(driveId)
      setApplicants(Array.isArray(data) ? data : [])
    } catch (err) {
      // silently ignore 403 etc for non-admin
    } finally {
      setAppsLoading(false)
    }
  }, [driveId, isAdmin])

  async function handleAppAction(appId, newStatus) {
    setUpdatingId(appId); setError(null); setNotice(null)
    try {
      await api.updateApplicationStatus(appId, newStatus)
      setApplicants((prev) => prev.map((a) => a.id === appId ? { ...a, status: newStatus } : a))
      setNotice(`Application ${newStatus}`)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setUpdatingId(null)
    }
  }

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const d = await api.getDrive(driveId)
        if (!cancelled) setDrive(d)
        const pos = await api.listJobPositions(driveId).catch(() => [])
        if (!cancelled) setPositions(Array.isArray(pos) ? pos : [])
        await checkEligibility()
        if (isAdmin) {
          try {
            const data = await api.listDriveApplications(driveId)
            if (!cancelled) setApplicants(Array.isArray(data) ? data : [])
          } catch {}
        }
        // fetch my applications to mark applied (students only)
        if (!isAdmin) {
          try {
            const apps = await api.listApplications()
            const map = {}
            for (const a of apps) {
              if (a.drive_id === driveId) {
                if (a.job_position_id) map[a.job_position_id] = true
                else map['__drive__'] = true
              }
            }
            if (!cancelled) setAppliedMap(map)
          } catch {}
        } else {
          if (!cancelled) setAppliedMap({})
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
  }, [driveId, checkEligibility, isAdmin])

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
  const driveIsOpen = isOpenStatus(drive.status)

  return (
    <div className="mx-auto max-w-4xl">
      <Link to="/drives" className="text-sm font-medium text-indigo-600 hover:underline">
        ← Back to drives
      </Link>
      <div className="flex items-center justify-between gap-3">
        <PageTitle>{drive.title}</PageTitle>
        {isAdmin && !isEditing && (
          <div className="flex gap-2">
            {drive.status === 'DRAFT' && (
              <Button onClick={handlePublish} disabled={publishing || positions.length === 0} className="shrink-0 bg-green-600 hover:bg-green-700 disabled:opacity-50" title={positions.length === 0 ? 'Add at least one role before publishing' : 'Publish drive to make it open'}>
                {publishing ? 'Publishing…' : 'Publish — Make Open'}
              </Button>
            )}
            <Button onClick={startEdit} className="shrink-0 bg-slate-800 hover:bg-slate-900">Edit Drive</Button>
          </div>
        )}
        {isAdmin && isEditing && (
          <div className="flex gap-2">
            <Button onClick={saveEdit} disabled={savingEdit}>{savingEdit ? 'Saving…' : 'Save'}</Button>
            <Button onClick={cancelEdit} className="bg-slate-600 hover:bg-slate-700">Cancel</Button>
          </div>
        )}
      </div>
      <ErrorBanner message={error} />
      {notice && (
        <div className="mb-4 rounded-md border border-green-200 bg-green-50 px-4 py-2 text-sm text-green-700">
          {notice}
        </div>
      )}
      {isEditing ? (
        <Card className="mb-4">
          <h3 className="mb-3 font-semibold text-slate-900">Edit Drive</h3>
          <form onSubmit={saveEdit} className="space-y-3">
            <label className="block"><span className="mb-1 block text-sm font-medium">Company *</span>
              <select value={editForm.company_id} onChange={(e) => setEditForm({ ...editForm, company_id: e.target.value })} className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" required>
                <option value="">Select company</option>
                {companies.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </label>
            <Field label="Title *" value={editForm.title} onChange={(e) => setEditForm({ ...editForm, title: e.target.value })} required />
            <Field label="Description" value={editForm.description} onChange={(e) => setEditForm({ ...editForm, description: e.target.value })} />
            <div className="grid grid-cols-2 gap-3">
              <label className="block"><span className="mb-1 block text-sm font-medium">Drive Type</span>
                <select value={editForm.drive_type} onChange={(e) => setEditForm({ ...editForm, drive_type: e.target.value })} className="w-full rounded-md border px-3 py-2 text-sm">
                  <option>ON_CAMPUS</option><option>OFF_CAMPUS</option><option>POOL_CAMPUS</option><option>VIRTUAL</option>
                </select>
              </label>
              <label className="block"><span className="mb-1 block text-sm font-medium">Mode</span>
                <select value={editForm.mode} onChange={(e) => setEditForm({ ...editForm, mode: e.target.value })} className="w-full rounded-md border px-3 py-2 text-sm">
                  <option>OFFLINE</option><option>ONLINE</option><option>HYBRID</option>
                </select>
              </label>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Registration Start" type="datetime-local" value={editForm.registration_start} onChange={(e) => setEditForm({ ...editForm, registration_start: e.target.value })} />
              <Field label="Registration End — extend deadline here" type="datetime-local" value={editForm.registration_end} onChange={(e) => setEditForm({ ...editForm, registration_end: e.target.value })} />
            </div>
            <Field label="Application Deadline (YYYY-MM-DD) — extend here" type="date" value={editForm.application_deadline} onChange={(e) => setEditForm({ ...editForm, application_deadline: e.target.value })} />
            <div className="grid grid-cols-2 gap-3">
              <Field label="Application Limit" type="number" min="1" value={editForm.application_limit} onChange={(e) => setEditForm({ ...editForm, application_limit: e.target.value })} placeholder="Leave blank for unlimited" />
              <label className="block"><span className="mb-1 block text-sm font-medium">Status — change drive status</span>
                <select value={editForm.status} onChange={(e) => setEditForm({ ...editForm, status: e.target.value })} className="w-full rounded-md border px-3 py-2 text-sm">
                  <option value="open">open</option><option value="DRAFT">DRAFT</option><option value="PUBLISHED">PUBLISHED</option><option value="REGISTRATION_OPEN">REGISTRATION_OPEN</option><option value="REGISTRATION_CLOSED">REGISTRATION_CLOSED</option><option value="IN_PROGRESS">IN_PROGRESS</option><option value="COMPLETED">COMPLETED</option><option value="CANCELLED">CANCELLED</option><option value="ARCHIVED">ARCHIVED</option>
                </select>
              </label>
            </div>
            <label className="block"><span className="mb-1 block text-sm font-medium">Instructions</span>
              <textarea value={editForm.instructions} onChange={(e) => setEditForm({ ...editForm, instructions: e.target.value })} rows={2} className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="Instructions for students" />
            </label>
            <div className="flex gap-2">
              <Button type="submit" disabled={savingEdit}>{savingEdit ? 'Saving…' : 'Save Changes'}</Button>
              <Button type="button" onClick={cancelEdit} className="bg-slate-600 hover:bg-slate-700">Cancel</Button>
            </div>
          </form>
        </Card>
      ) : (
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
        {['DRAFT', 'draft'].includes(String(drive.status)) && isAdmin && (
          <div className="mt-4 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
            This drive is in <b>DRAFT</b> — not visible to students. {positions.length === 0 ? 'Add at least one role first.' : 'Click “Publish — Make Open” above or change Status to “open” via Edit Drive to make it open.'}
          </div>
        )}
        {drive.description && <p className="mt-4 text-sm text-slate-700">{drive.description}</p>}
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
      )}

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
            {eligibility.missing_requirements?.length > 0 && (
              <div className="mt-3 rounded-md bg-amber-50 border border-amber-200 p-2 text-xs text-amber-800">
                <b>Missing:</b> {eligibility.missing_requirements.join('; ')}
              </div>
            )}
          </>
        ) : (
          <p className="text-sm text-slate-600">
            {isAdmin ? 'Eligibility check is student-only.' : 'Complete your profile to see your eligibility for this drive.'}
          </p>
        )}
      </Card>

      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-900">Roles ({positions.length})</h2>
        {positions.length > 1 && <p className="text-xs text-slate-500">Compare roles — each has separate compensation, bond & skills</p>}
      </div>

      {positions.length === 0 ? (
        <Card>
          <p className="text-sm text-slate-600">No roles added yet. {driveIsOpen && !drive.roles_count ? <span>TNPC will add roles soon.</span> : null}</p>
          {!driveApplied && eligibility?.eligible && driveIsOpen && positions.length === 0 && (
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
                    disabled={!!applyingId || isApplied || !eligibility?.eligible || !driveIsOpen}
                    className={isApplied ? 'bg-green-600 hover:bg-green-700' : ''}
                  >
                    {isApplied ? 'Applied ✓' : applyingId === p.id ? 'Submitting…' : 'Apply to this Role'}
                  </Button>
                  {eligibility && !eligibility?.eligible && <span className="ml-2 text-xs text-red-600">Not eligible</span>}
                  {!driveIsOpen && <span className="ml-2 text-xs text-amber-700">Drive not open ({drive.status})</span>}
                </div>
              </Card>
            )
          })}
        </div>
      )}
      {isAdmin && (
        <Card className="mt-6">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-base font-semibold text-slate-900">Applicants for this drive ({applicants.length})</h2>
            <Button onClick={loadApplicants} disabled={appsLoading} className="bg-slate-700 px-3 py-1 text-xs">{appsLoading ? 'Loading…' : 'Refresh'}</Button>
          </div>
          {applicants.length === 0 ? (
            <p className="py-4 text-center text-sm text-slate-500">{appsLoading ? 'Loading…' : 'No students have applied yet.'}</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[640px] text-left text-sm">
                <thead className="border-b bg-slate-50 text-xs uppercase text-slate-500">
                  <tr>
                    <th className="px-3 py-2">Student</th>
                    <th className="px-3 py-2">Branch / CGPA</th>
                    <th className="px-3 py-2">Role Applied</th>
                    <th className="px-3 py-2">Applied On</th>
                    <th className="px-3 py-2">Status</th>
                    <th className="px-3 py-2">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {applicants.map((app) => (
                    <tr key={app.id} className="border-b last:border-0">
                      <td className="px-3 py-2">
                        <p className="font-medium text-slate-900">{app.student_name}</p>
                        <p className="text-xs text-slate-500">{app.student_email}</p>
                      </td>
                      <td className="px-3 py-2 text-slate-700">{app.branch || '—'} {app.cgpa != null ? `· ${app.cgpa} CGPA` : ''} <span className="text-xs text-slate-500">{app.graduation_year ? `· ${app.graduation_year}` : ''}</span></td>
                      <td className="px-3 py-2 text-slate-700">{app.job_title ? `${app.job_title} (${app.job_role})` : '—'}</td>
                      <td className="px-3 py-2 text-xs text-slate-600">{app.created_at ? new Date(app.created_at).toLocaleDateString() : '—'}</td>
                      <td className="px-3 py-2"><Badge tone={app.status === 'applied' ? 'slate' : app.status === 'shortlisted' ? 'green' : app.status === 'rejected' ? 'red' : 'amber'}>{app.status}</Badge></td>
                      <td className="px-3 py-2">
                        <div className="flex gap-1.5">
                          <button onClick={() => handleAppAction(app.id, 'shortlisted')} disabled={updatingId === app.id || app.status !== 'applied'} className="rounded-md bg-green-600 px-2.5 py-1 text-xs font-medium text-white hover:bg-green-700 disabled:opacity-40">{updatingId === app.id ? '…' : 'Shortlist'}</button>
                          <button onClick={() => handleAppAction(app.id, 'rejected')} disabled={updatingId === app.id || app.status !== 'applied'} className="rounded-md bg-red-600 px-2.5 py-1 text-xs font-medium text-white hover:bg-red-700 disabled:opacity-40">{updatingId === app.id ? '…' : 'Reject'}</button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}
    </div>
  )
}
