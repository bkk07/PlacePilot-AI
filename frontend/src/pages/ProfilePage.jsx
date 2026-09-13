import { useEffect, useMemo, useState } from 'react'
import { Button, Card, ErrorBanner, Field, PageTitle } from '../components/ui.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import { api, errorMessage } from '../lib/api.js'

const EMPTY = {
  roll_number: '',
  branch: 'CSE',
  graduation_year: 2027,
  cgpa: null,
  active_backlogs: 0,
  skills: [],
  personal_email: '',
  phone_number: '',
  degree: 'B.Tech',
  specialization: '',
  admission_year: null,
  current_year: null,
  current_semester: null,
  tenth_percentage: null,
  tenth_board: '',
  twelfth_percentage: null,
  twelfth_board: '',
  diploma_percentage: null,
  history_of_backlogs: 0,
  year_gaps: 0,
}

const BRANCH_FALLBACK = ['CSE','ECE','EEE','ME','CIVIL','IT','CSE-AIML','CSE-DS','CHEM','AERO']

function Section({ title, children }) {
  return (
    <Card>
      <h3 className="mb-4 text-sm font-semibold tracking-wide text-slate-900 uppercase">{title}</h3>
      {children}
    </Card>
  )
}

export default function ProfilePage() {
  const { user } = useAuth()
  const [form, setForm] = useState(EMPTY)
  const [skillsCatalog, setSkillsCatalog] = useState([])
  const [branches, setBranches] = useState([])
  const [skillQuery, setSkillQuery] = useState('')
  const [error, setError] = useState(null)
  const [notice, setNotice] = useState(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [photoBusy, setPhotoBusy] = useState(false)
  const [photoUrl, setPhotoUrl] = useState(null)

  // load profile + catalogs
  useEffect(() => {
    let cancelled = false
    let objectUrl = null
    async function load() {
      try {
        const [profile, skills, brs] = await Promise.all([
          api.getProfile().catch(() => null),
          api.listSkills().catch(() => []),
          api.listBranches().catch(() => []),
        ])
        if (cancelled) return
        if (profile) {
          setForm({
            roll_number: profile.roll_number ?? '',
            branch: profile.branch ?? 'CSE',
            graduation_year: profile.graduation_year ?? 2027,
            cgpa: profile.cgpa,
            active_backlogs: profile.active_backlogs ?? 0,
            skills: profile.skills ?? [],
            personal_email: profile.personal_email ?? '',
            phone_number: profile.phone_number ?? '',
            degree: profile.degree ?? 'B.Tech',
            specialization: profile.specialization ?? '',
            admission_year: profile.admission_year ?? null,
            current_year: profile.current_year ?? null,
            current_semester: profile.current_semester ?? null,
            tenth_percentage: profile.tenth_percentage ?? null,
            tenth_board: profile.tenth_board ?? '',
            twelfth_percentage: profile.twelfth_percentage ?? null,
            twelfth_board: profile.twelfth_board ?? '',
            diploma_percentage: profile.diploma_percentage ?? null,
            history_of_backlogs: profile.history_of_backlogs ?? 0,
            year_gaps: profile.year_gaps ?? 0,
          })
          if (profile.profile_photo_id) {
            try {
              const blob = await api.getProfilePhotoBlob()
              if (!cancelled && blob) {
                objectUrl = URL.createObjectURL(blob)
                setPhotoUrl(objectUrl)
              }
            } catch {}
          }
        }
        setSkillsCatalog(skills)
        setBranches(brs.length ? brs : BRANCH_FALLBACK.map(c => ({ code: c, name: c })))
      } catch {
        // keep empty
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    void load()
    return () => {
      cancelled = true
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [])

  const filteredSkills = useMemo(() => {
    if (!skillQuery.trim()) return []
    const q = skillQuery.trim().toLowerCase()
    const selected = new Set(form.skills.map(s => s.toLowerCase()))
    return skillsCatalog.filter(s => !selected.has(s.name.toLowerCase()) && s.name.toLowerCase().includes(q)).slice(0, 8)
  }, [skillQuery, skillsCatalog, form.skills])

  function addSkill(name) {
    const n = name.trim()
    if (!n) return
    if (form.skills.some(s => s.toLowerCase() === n.toLowerCase())) return
    setForm({ ...form, skills: [...form.skills, n] })
    setSkillQuery('')
  }
  function removeSkill(name) {
    setForm({ ...form, skills: form.skills.filter(s => s !== name) })
  }

  async function onPhotoChange(e) {
    const file = e.target.files?.[0]
    if (!file) return
    if (file.size > 2 * 1024 * 1024) {
      setError('File too large (max 2MB)')
      return
    }
    if (!file.type.startsWith('image/')) {
      setError('Only image files allowed')
      return
    }
    setPhotoBusy(true); setError(null)
    try {
      await api.uploadProfilePhoto(file)
      const blob = await api.getProfilePhotoBlob()
      setPhotoUrl(prev => { if (prev) URL.revokeObjectURL(prev); return URL.createObjectURL(blob) })
      setNotice('Photo updated.')
    } catch (err) { setError(errorMessage(err)) }
    finally { setPhotoBusy(false); e.target.value = '' }
  }

  function numOrNull(v) { return v === '' || v === null ? null : Number(v) }

  async function onSubmit(e) {
    e.preventDefault()
    setBusy(true); setError(null); setNotice(null)
    const payload = {
      roll_number: form.roll_number.trim(),
      branch: form.branch.trim(),
      graduation_year: Number(form.graduation_year),
      cgpa: numOrNull(form.cgpa),
      active_backlogs: Number(form.active_backlogs) || 0,
      skills: form.skills.map(s => s.trim().toLowerCase()).filter(Boolean),
      personal_email: form.personal_email.trim() || null,
      phone_number: form.phone_number.trim() || null,
      degree: form.degree.trim() || 'B.Tech',
      specialization: form.specialization.trim() || null,
      admission_year: numOrNull(form.admission_year),
      current_year: numOrNull(form.current_year),
      current_semester: numOrNull(form.current_semester),
      tenth_percentage: numOrNull(form.tenth_percentage),
      tenth_board: form.tenth_board.trim() || null,
      twelfth_percentage: numOrNull(form.twelfth_percentage),
      twelfth_board: form.twelfth_board.trim() || null,
      diploma_percentage: numOrNull(form.diploma_percentage),
      history_of_backlogs: Number(form.history_of_backlogs) || 0,
      year_gaps: Number(form.year_gaps) || 0,
    }
    try {
      await api.saveProfile(payload)
      setNotice('Profile saved.')
    } catch (err) { setError(errorMessage(err)) }
    finally { setBusy(false) }
  }

  if (loading) return <p className="text-slate-500">Loading…</p>

  return (
    <div className="mx-auto max-w-4xl">
      <PageTitle>Student Profile</PageTitle>
      <ErrorBanner message={error} />
      {notice && <div className="mb-4 rounded-md border border-green-200 bg-green-50 px-4 py-2 text-sm text-green-700">{notice}</div>}

      <form onSubmit={onSubmit} className="space-y-6">
        {/* 1. Student Information */}
        <Section title="1 · Student Information">
          <div className="flex gap-4 mb-4">
            <div className="h-20 w-20 overflow-hidden rounded-full border border-slate-200 bg-slate-100 flex items-center justify-center shrink-0">
              {photoUrl ? <img src={photoUrl} alt="photo" className="h-full w-full object-cover" /> : <span className="text-xl font-semibold text-slate-500">{(user?.full_name || 'S').slice(0,1).toUpperCase()}</span>}
            </div>
            <div className="flex-1">
              <p className="text-sm font-medium text-slate-900">{user?.full_name} <span className="font-normal text-slate-500">· {user?.email}</span></p>
              <p className="text-xs text-slate-500">College email is your login email. Add a personal email below if different.</p>
              <label className="mt-2 inline-block rounded-md border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 cursor-pointer">
                {photoBusy ? 'Uploading…' : 'Upload photo'}
                <input type="file" accept="image/*" className="hidden" onChange={onPhotoChange} disabled={photoBusy} />
              </label>
            </div>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Student ID / Roll Number *" value={form.roll_number} onChange={e=>setForm({...form, roll_number: e.target.value})} required />
            <Field label="Full Name (from account)" value={user?.full_name ?? ''} disabled className="bg-slate-50" />
            <Field label="College Email (login)" value={user?.email ?? ''} disabled className="bg-slate-50" />
            <Field label="Personal Email" type="email" placeholder="you@gmail.com" value={form.personal_email} onChange={e=>setForm({...form, personal_email: e.target.value})} />
            <Field label="Phone Number" placeholder="10-digit mobile" value={form.phone_number} onChange={e=>setForm({...form, phone_number: e.target.value})} />
          </div>
        </Section>

        {/* 2. B.Tech Academic Information */}
        <Section title="2 · B.Tech Academic Information">
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block">
              <span className="mb-1 block text-sm font-medium text-slate-700">Degree</span>
              <select value={form.degree} onChange={e=>setForm({...form, degree: e.target.value})} className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm">
                <option>B.Tech</option><option>M.Tech</option><option>B.E.</option><option>MCA</option><option>BCA</option>
              </select>
            </label>
            <label className="block">
              <span className="mb-1 block text-sm font-medium text-slate-700">Branch *</span>
              <select value={form.branch} onChange={e=>setForm({...form, branch: e.target.value})} className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm">
                {branches.map(b => <option key={b.code} value={b.code}>{b.code} — {b.name}</option>)}
              </select>
            </label>
            <Field label="Specialization" placeholder="AI & ML / Data Science / etc." value={form.specialization} onChange={e=>setForm({...form, specialization: e.target.value})} />
            <Field label="Admission Year" type="number" value={form.admission_year ?? ''} onChange={e=>setForm({...form, admission_year: e.target.value === '' ? null : Number(e.target.value)})} placeholder="2023" />
            <Field label="Graduation Year *" type="number" value={form.graduation_year} onChange={e=>setForm({...form, graduation_year: Number(e.target.value)})} required />
            <Field label="Current Year" type="number" min="1" max="6" value={form.current_year ?? ''} onChange={e=>setForm({...form, current_year: e.target.value === '' ? null : Number(e.target.value)})} placeholder="4" />
            <Field label="Current Semester" type="number" min="1" max="12" value={form.current_semester ?? ''} onChange={e=>setForm({...form, current_semester: e.target.value === '' ? null : Number(e.target.value)})} placeholder="7" />
            <Field label="CGPA" type="number" step="0.01" min="0" max="10" value={form.cgpa ?? ''} onChange={e=>setForm({...form, cgpa: e.target.value === '' ? null : Number(e.target.value)})} placeholder="8.72" />
          </div>
        </Section>

        {/* 3. School Academic Details */}
        <Section title="3 · School Academic Details">
          <p className="mb-3 text-xs text-slate-500">10th/12th percentages are used for eligibility checks — many companies filter on them.</p>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="10th Percentage" type="number" step="0.01" min="0" max="100" value={form.tenth_percentage ?? ''} onChange={e=>setForm({...form, tenth_percentage: e.target.value === '' ? null : Number(e.target.value)})} />
            <Field label="10th Board" placeholder="CBSE / ICSE / State" value={form.tenth_board} onChange={e=>setForm({...form, tenth_board: e.target.value})} />
            <Field label="12th / Intermediate Percentage" type="number" step="0.01" min="0" max="100" value={form.twelfth_percentage ?? ''} onChange={e=>setForm({...form, twelfth_percentage: e.target.value === '' ? null : Number(e.target.value)})} />
            <Field label="12th Board" placeholder="CBSE / State / etc." value={form.twelfth_board} onChange={e=>setForm({...form, twelfth_board: e.target.value})} />
            <Field label="Diploma Percentage (optional)" type="number" step="0.01" min="0" max="100" value={form.diploma_percentage ?? ''} onChange={e=>setForm({...form, diploma_percentage: e.target.value === '' ? null : Number(e.target.value)})} />
          </div>
        </Section>

        {/* 4. Backlog / Academic Eligibility */}
        <Section title="4 · Backlog / Academic Eligibility">
          <div className="grid gap-4 sm:grid-cols-3">
            <Field label="Current Backlogs" type="number" min="0" value={form.active_backlogs} onChange={e=>setForm({...form, active_backlogs: Number(e.target.value)})} />
            <Field label="History of Backlogs" type="number" min="0" value={form.history_of_backlogs} onChange={e=>setForm({...form, history_of_backlogs: Number(e.target.value)})} />
            <Field label="Year Gaps" type="number" min="0" value={form.year_gaps} onChange={e=>setForm({...form, year_gaps: Number(e.target.value)})} />
          </div>
        </Section>

        {/* Skills */}
        <Section title="Skills">
          <div className="mb-2 flex flex-wrap gap-1.5">
            {form.skills.length === 0 && <span className="text-xs text-slate-400">No skills selected — search below.</span>}
            {form.skills.map(s => (
              <span key={s} className="inline-flex items-center gap-1 rounded-full bg-indigo-50 px-2.5 py-1 text-xs font-medium text-indigo-700 border border-indigo-200">
                {s} <button type="button" onClick={()=>removeSkill(s)} className="ml-1 text-indigo-500 hover:text-indigo-800">×</button>
              </span>
            ))}
          </div>
          <div className="relative">
            <input value={skillQuery} onChange={e=>setSkillQuery(e.target.value)} onKeyDown={e=>{ if(e.key==='Enter'){ e.preventDefault(); if(filteredSkills[0]) addSkill(filteredSkills[0].name); else if(skillQuery.trim()) addSkill(skillQuery) } }} placeholder="Search skills (e.g. python, react, docker) — Enter to add" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500" />
            {filteredSkills.length>0 && (
              <div className="absolute z-10 mt-1 max-h-48 w-full overflow-auto rounded-md border border-slate-200 bg-white shadow">
                {filteredSkills.map(s => (
                  <button key={s.id} type="button" onClick={()=>addSkill(s.name)} className="flex w-full items-center justify-between px-3 py-1.5 text-left text-sm hover:bg-slate-50">
                    <span>{s.name}</span><span className="text-xs text-slate-400">{s.category}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
          <p className="mt-1 text-xs text-slate-500">{skillsCatalog.length} skills available from catalog. Press Enter to add a custom skill if not found.</p>
        </Section>

        <div className="flex justify-end">
          <Button type="submit" disabled={busy}>{busy ? 'Saving…' : 'Save profile'}</Button>
        </div>
      </form>
    </div>
  )
}
