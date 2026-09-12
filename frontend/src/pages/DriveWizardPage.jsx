import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Badge, Button, Card, ErrorBanner, Field, PageTitle } from '../components/ui.jsx'
import { api, errorMessage } from '../lib/api.js'

const EMPTY_DRIVE = {
  title: '', description: '', drive_type: 'ON_CAMPUS', mode: 'OFFLINE',
  registration_start: '', registration_end: '', drive_start_date: '', drive_end_date: '',
  application_limit: '', instructions: '',
}
const EMPTY_POSITION = {
  title: '', role: '', department: '', employment_type: 'FULL_TIME', openings: '', work_mode: 'ONSITE', job_description: '',
  // compensation
  currency: 'INR', ctc_min: '', ctc_max: '', stipend_min: '', stipend_max: '', is_unpaid: false,
  // bond
  bond_required: false, bond_duration_months: '', bond_amount: '', bond_description: '',
}

export default function DriveWizardPage() {
  const navigate = useNavigate()
  const [step, setStep] = useState(1)
  const [companies, setCompanies] = useState([])
  const [showAddCompany, setShowAddCompany] = useState(false)
  const [newCompany, setNewCompany] = useState({ name: '', industry: '', website: '' })
  const [drive, setDrive] = useState({ ...EMPTY_DRIVE, company_id: '' })
  const [createdDrive, setCreatedDrive] = useState(null)
  const [position, setPosition] = useState({ ...EMPTY_POSITION })
  const [positions, setPositions] = useState([])
  const [error, setError] = useState(null)
  const [notice, setNotice] = useState(null)
  // enrichments for role
  const [allSkills, setAllSkills] = useState([])
  const [skillQuery, setSkillQuery] = useState('')
  const [selectedSkills, setSelectedSkills] = useState([]) // [{skill_id, name, mandatory:true, skill_level:''}]
  const [locations, setLocations] = useState([{ city: '', state: '', country: 'India', work_mode: 'ONSITE' }])
  const [intern, setIntern] = useState({ duration_months: '', ppo_available: false, ppo_criteria: '' })

  // Step 3 state
  const [branches, setBranches] = useState([])
  const [selectedBranches, setSelectedBranches] = useState([])
  const [batchYears, setBatchYears] = useState('2027, 2028')
  const [eligibility, setEligibility] = useState({ minimum_cgpa: '', maximum_backlogs: '', passing_year_from: '', passing_year_to: '' })
  // Step 4 state
  const [rounds, setRounds] = useState([])
  const [roundForm, setRoundForm] = useState({ name: '', type: 'APTITUDE', sequence: 1 })

  useEffect(() => { api.listCompanies().then(setCompanies).catch(() => {}) }, [])
  useEffect(() => {
    let cancelled = false
    // initial empty query loads immediately, otherwise debounce 300ms for backend search
    if (skillQuery.trim() === '') {
      api.listSkills('').then((res) => { if (!cancelled) setAllSkills(res) }).catch(() => {})
      return () => { cancelled = true }
    }
    const t = setTimeout(() => {
      api.listSkills(skillQuery).then((res) => { if (!cancelled) setAllSkills(res) }).catch(() => {})
    }, 300)
    return () => { cancelled = true; clearTimeout(t) }
  }, [skillQuery])
  useEffect(() => {
    if (step === 3 && createdDrive) {
      api.listBranches().then(setBranches).catch(() => {})
      api.getDriveBranches(createdDrive.id).then((r) => setSelectedBranches(r.map((x) => x.branch_id))).catch(() => {})
      api.getDriveBatches(createdDrive.id).then((r) => setBatchYears(r.map((x) => x.graduation_year).join(', '))).catch(() => {})
    }
    if (step === 4 && createdDrive) {
      api.listRounds(createdDrive.id).then(setRounds).catch(() => {})
    }
  }, [step, createdDrive])

  async function createCompanyInline(e) {
    e.preventDefault(); setError(null)
    try {
      const res = await api.createCompany(newCompany)
      setCompanies((c) => [...c, { id: res.id, name: res.name }])
      setDrive({ ...drive, company_id: res.id })
      setNewCompany({ name: '', industry: '', website: '' })
      setShowAddCompany(false)
      setNotice(`Company "${res.name}" added.`)
    } catch (err) { setError(errorMessage(err)) }
  }

  async function createDrive(e) {
    e.preventDefault(); setError(null)
    // Validate required fields; defer actual POST until at least one job is added (transactional creation)
    if (!drive.company_id) { setError('Company is required'); return }
    if (!drive.title?.trim()) { setError('Drive Title is required'); return }
    // Keep payload for deferred creation
    setNotice(`Drive "${drive.title}" ready — add at least one job role to create it.`)
    setStep(2)
  }

  async function ensureDriveCreated() {
    if (createdDrive) return createdDrive
    // first time: create drive for real now that we have at least one role
    const payload = {
      ...drive,
      application_limit: drive.application_limit ? Number(drive.application_limit) : null,
      registration_start: drive.registration_start || null,
      registration_end: drive.registration_end || null,
      drive_start_date: drive.drive_start_date || null,
      drive_end_date: drive.drive_end_date || null,
    }
    const created = await api.createDrive(payload)
    setCreatedDrive(created)
    return created
  }

  function toggleSkill(skill) {
    const exists = selectedSkills.find((s) => s.skill_id === skill.id)
    if (exists) setSelectedSkills((prev) => prev.filter((s) => s.skill_id !== skill.id))
    else setSelectedSkills((prev) => [...prev, { skill_id: skill.id, name: skill.name, mandatory: true, skill_level: 'INTERMEDIATE' }])
  }

  async function addPosition(e) {
    e.preventDefault(); setError(null)
    try {
      const payload = {
        title: position.title,
        role: position.role || position.title,
        department: position.department || null,
        employment_type: position.employment_type,
        openings: position.openings === '' ? null : Number(position.openings),
        work_mode: position.work_mode,
        job_description: position.job_description || null,
        bond_required: !!position.bond_required,
        bond_duration_months: position.bond_duration_months ? Number(position.bond_duration_months) : null,
        bond_amount: position.bond_amount ? Number(position.bond_amount) : null,
        bond_description: position.bond_description || null,
        compensation: {
          currency: position.currency || 'INR',
          ctc_min: position.ctc_min ? Number(position.ctc_min) : null,
          ctc_max: position.ctc_max ? Number(position.ctc_max) : null,
          stipend_min: position.stipend_min ? Number(position.stipend_min) : null,
          stipend_max: position.stipend_max ? Number(position.stipend_max) : null,
          is_unpaid: !!position.is_unpaid,
        },
        skills: selectedSkills.map((s) => ({ skill_id: s.skill_id, mandatory: s.mandatory, skill_level: s.skill_level })),
        locations: locations.filter((l) => l.city.trim()).map((l) => ({ city: l.city.trim(), state: l.state || null, country: l.country || 'India', work_mode: l.work_mode || position.work_mode })),
        internship: position.employment_type === 'INTERNSHIP' || position.employment_type === 'INTERNSHIP_TO_FULL_TIME' ? {
          duration_months: intern.duration_months ? Number(intern.duration_months) : null,
          paid: !position.is_unpaid,
          stipend_min: position.stipend_min ? Number(position.stipend_min) : null,
          stipend_max: position.stipend_max ? Number(position.stipend_max) : null,
          ppo_available: !!intern.ppo_available,
          ppo_criteria: intern.ppo_criteria || null,
        } : undefined,
      }
      if (!payload.title) throw new Error('Position Title required')
      if (payload.compensation.is_unpaid) {
        payload.compensation.stipend_min = null
        payload.compensation.stipend_max = null
      }
      const isFirstRole = !createdDrive
      const driveObj = await ensureDriveCreated()
      if (isFirstRole) setNotice(`Drive "${driveObj.title}" created with first role — add more roles or continue.`)
      const created = await api.createJobPosition(driveObj.id, payload)
      setPositions((p) => [...p, created]); setNotice(`Role "${created.title}" added (${created.employment_type}).`)
      // reset
      setPosition({ ...EMPTY_POSITION })
      setSelectedSkills([])
      setLocations([{ city: '', state: '', country: 'India', work_mode: 'ONSITE' }])
      setIntern({ duration_months: '', ppo_available: false, ppo_criteria: '' })
    } catch (err) { setError(errorMessage(err)) }
  }

  async function saveEligibility(e) {
    e.preventDefault(); setError(null)
    const payload = {}
    if (eligibility.minimum_cgpa) payload.minimum_cgpa = Number(eligibility.minimum_cgpa)
    if (eligibility.maximum_backlogs) payload.maximum_backlogs = Number(eligibility.maximum_backlogs)
    if (eligibility.passing_year_from) payload.passing_year_from = Number(eligibility.passing_year_from)
    if (eligibility.passing_year_to) payload.passing_year_to = Number(eligibility.passing_year_to)
    try { await api.saveEligibility(createdDrive.id, payload); setNotice('Eligibility saved.') } catch (err) { setError(errorMessage(err)) }
  }
  async function saveBranches() {
    setError(null)
    try { await api.saveDriveBranches(createdDrive.id, selectedBranches); setNotice('Branches saved.') } catch (err) { setError(errorMessage(err)) }
  }
  async function saveBatches() {
    setError(null)
    const years = batchYears.split(',').map((s) => s.trim()).filter(Boolean).map(Number).filter((n) => !isNaN(n))
    try { await api.saveDriveBatches(createdDrive.id, years); setNotice('Batches saved.') } catch (err) { setError(errorMessage(err)) }
  }
  async function addRound(e) {
    e.preventDefault(); setError(null)
    try {
      const created = await api.createRound(createdDrive.id, roundForm)
      setRounds((r) => [...r, created]); setNotice(`Round "${created.name}" added.`)
    } catch (err) { setError(errorMessage(err)) }
  }
  async function publish() {
    setError(null)
    try { await api.publishDrive(createdDrive.id); setNotice('Drive published — students can now apply.'); } catch (err) { setError(errorMessage(err)) }
  }

  return (
    <div className="mx-auto max-w-4xl">
      <PageTitle>New Placement Drive — TNPC Wizard</PageTitle>
      <div className="mb-4 flex gap-2 text-sm">
        {[1, 2, 3, 4].map((s) => (
          <span key={s} className={`rounded-full px-3 py-1 ${step === s ? 'bg-indigo-600 text-white' : step > s ? 'bg-green-100 text-green-700' : 'bg-slate-200'}`}>Step {s}</span>
        ))}
      </div>
      <ErrorBanner message={error} />
      {notice && <div className="mb-4 rounded-md border border-green-200 bg-green-50 px-4 py-2 text-sm text-green-700">{notice}</div>}

      {step === 1 && (
        <Card>
          <h2 className="mb-3 font-semibold">1 — Company & Drive Basics</h2>
          <form onSubmit={createDrive} className="space-y-3">
            <div className="flex items-end gap-2">
              <label className="block flex-1"><span className="mb-1 block text-sm font-medium">Company *</span>
                <select value={drive.company_id} onChange={(e) => setDrive({ ...drive, company_id: e.target.value })} className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" required>
                  <option value="">Select company</option>{companies.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                </select>
              </label>
              <Button type="button" onClick={() => setShowAddCompany(!showAddCompany)} className="bg-slate-700 hover:bg-slate-800 whitespace-nowrap">{showAddCompany ? 'Cancel' : '+ Add Company'}</Button>
            </div>
            {showAddCompany && (
              <div className="rounded-md border border-dashed border-slate-300 bg-slate-50 p-3 space-y-2">
                <p className="text-sm font-medium">New Company</p>
                <div className="grid grid-cols-2 gap-2">
                  <Field label="Name *" value={newCompany.name} onChange={(e) => setNewCompany({ ...newCompany, name: e.target.value })} required />
                  <Field label="Industry" value={newCompany.industry} onChange={(e) => setNewCompany({ ...newCompany, industry: e.target.value })} placeholder="Cloud Analytics" />
                </div>
                <Field label="Website" value={newCompany.website} onChange={(e) => setNewCompany({ ...newCompany, website: e.target.value })} placeholder="https://..." />
                <Button onClick={createCompanyInline} className="mt-2">Save Company</Button>
              </div>
            )}
            <Field label="Drive Title *" value={drive.title} onChange={(e) => setDrive({ ...drive, title: e.target.value })} required placeholder="Nimbus 2026 Batch Hiring" />
            <Field label="Description" value={drive.description} onChange={(e) => setDrive({ ...drive, description: e.target.value })} placeholder="Brief about drive..." />
            <div className="grid grid-cols-2 gap-3">
              <label className="block"><span className="mb-1 block text-sm font-medium">Drive Type</span>
                <select value={drive.drive_type} onChange={(e) => setDrive({ ...drive, drive_type: e.target.value })} className="w-full rounded-md border px-3 py-2 text-sm">
                  <option>ON_CAMPUS</option><option>OFF_CAMPUS</option><option>POOL_CAMPUS</option><option>VIRTUAL</option>
                </select>
              </label>
              <label className="block"><span className="mb-1 block text-sm font-medium">Mode</span>
                <select value={drive.mode} onChange={(e) => setDrive({ ...drive, mode: e.target.value })} className="w-full rounded-md border px-3 py-2 text-sm">
                  <option>OFFLINE</option><option>ONLINE</option><option>HYBRID</option>
                </select>
              </label>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Registration Start" type="datetime-local" value={drive.registration_start} onChange={(e) => setDrive({ ...drive, registration_start: e.target.value })} />
              <Field label="Registration End" type="datetime-local" value={drive.registration_end} onChange={(e) => setDrive({ ...drive, registration_end: e.target.value })} />
            </div>
            <Button type="submit">Continue to Roles →</Button>
            <p className="text-xs text-slate-500">Drive will be created when you add the first job role. At least one role is required.</p>
          </form>
        </Card>
      )}

      {step === 2 && (
        <div className="space-y-4">
          <Card>
            <h2 className="mb-1 font-semibold">2 — Job Roles (multiple per Drive) *</h2>
            <p className="mb-3 text-sm text-slate-600">Drive: <b>{createdDrive?.title || drive.title || '—'}</b> {createdDrive ? '' : '(not yet created)'} — each role has independent skills, stipend/bond & location. <span className="font-medium text-amber-700">At least one role required to create drive.</span></p>
            <form onSubmit={addPosition} className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <Field label="Role Title *" value={position.title} onChange={(e) => setPosition({ ...position, title: e.target.value })} required placeholder="Software Engineer" />
                <Field label="Role / Designation" value={position.role} onChange={(e) => setPosition({ ...position, role: e.target.value })} placeholder="SDE-1" />
              </div>
              <div className="grid grid-cols-3 gap-3">
                <label className="block"><span className="mb-1 block text-sm font-medium">Employment Type *</span>
                  <select value={position.employment_type} onChange={(e) => setPosition({ ...position, employment_type: e.target.value })} className="w-full rounded-md border px-3 py-2 text-sm">
                    <option>FULL_TIME</option><option>INTERNSHIP</option><option>INTERNSHIP_TO_FULL_TIME</option><option>CONTRACT</option>
                  </select>
                </label>
                <Field label="Openings" type="number" min="1" value={position.openings} onChange={(e) => setPosition({ ...position, openings: e.target.value })} placeholder="10" />
                <Field label="Work Mode" value={position.work_mode} onChange={(e) => setPosition({ ...position, work_mode: e.target.value })} placeholder="ONSITE / REMOTE / HYBRID" />
              </div>
              <Field label="Department" value={position.department} onChange={(e) => setPosition({ ...position, department: e.target.value })} placeholder="Engineering" />
              <label className="block"><span className="mb-1 block text-sm font-medium">Job Description</span>
                <textarea value={position.job_description} onChange={(e) => setPosition({ ...position, job_description: e.target.value })} rows={3} className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="Responsibilities, tech stack..." />
              </label>

              {/* Compensation */}
              <div className="rounded-md border border-slate-200 bg-slate-50 p-3 space-y-3">
                <h3 className="text-sm font-semibold">Compensation</h3>
                <div className="grid grid-cols-3 gap-3">
                  <Field label="Currency" value={position.currency} onChange={(e) => setPosition({ ...position, currency: e.target.value })} />
                  <label className="flex items-center gap-2 text-sm pt-6"><input type="checkbox" checked={!!position.is_unpaid} onChange={(e) => setPosition({ ...position, is_unpaid: e.target.checked })} /> Unpaid</label>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <Field label="CTC Min (LPA) — annual" type="number" step="0.1" value={position.ctc_min} onChange={(e) => setPosition({ ...position, ctc_min: e.target.value })} placeholder="8" disabled={position.employment_type === 'INTERNSHIP'} />
                  <Field label="CTC Max (LPA)" type="number" step="0.1" value={position.ctc_max} onChange={(e) => setPosition({ ...position, ctc_max: e.target.value })} placeholder="12" disabled={position.employment_type === 'INTERNSHIP'} />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <Field label="Stipend Min (₹/mo)" type="number" value={position.stipend_min} onChange={(e) => setPosition({ ...position, stipend_min: e.target.value })} placeholder="25000" disabled={!!position.is_unpaid} />
                  <Field label="Stipend Max (₹/mo)" type="number" value={position.stipend_max} onChange={(e) => setPosition({ ...position, stipend_max: e.target.value })} placeholder="40000" disabled={!!position.is_unpaid} />
                </div>
                {position.is_unpaid && <p className="text-xs text-amber-700">Marked as Unpaid — stipend will show as “Unpaid” to students.</p>}
                {position.employment_type === 'INTERNSHIP' || position.employment_type === 'INTERNSHIP_TO_FULL_TIME' ? (
                  <div className="grid grid-cols-2 gap-3 border-t pt-3">
                    <Field label="Intern Duration (months)" type="number" value={intern.duration_months} onChange={(e) => setIntern({ ...intern, duration_months: e.target.value })} placeholder="3" />
                    <label className="flex items-center gap-2 text-sm pt-6"><input type="checkbox" checked={!!intern.ppo_available} onChange={(e) => setIntern({ ...intern, ppo_available: e.target.checked })} /> PPO Available</label>
                    {intern.ppo_available && <Field label="PPO Criteria" value={intern.ppo_criteria} onChange={(e) => setIntern({ ...intern, ppo_criteria: e.target.value })} placeholder="Performance > 8 CGPA" />}
                  </div>
                ) : null}
              </div>

              {/* Bond */}
              <div className="rounded-md border border-slate-200 bg-slate-50 p-3 space-y-3">
                <label className="flex items-center gap-2 text-sm font-semibold"><input type="checkbox" checked={!!position.bond_required} onChange={(e) => setPosition({ ...position, bond_required: e.target.checked })} /> Service Bond / Agreement</label>
                {position.bond_required && (
                  <div className="grid grid-cols-2 gap-3">
                    <Field label="Bond Duration (months)" type="number" value={position.bond_duration_months} onChange={(e) => setPosition({ ...position, bond_duration_months: e.target.value })} placeholder="12" />
                    <Field label="Bond Amount (₹)" type="number" value={position.bond_amount} onChange={(e) => setPosition({ ...position, bond_amount: e.target.value })} placeholder="100000" />
                    <label className="block col-span-2"><span className="mb-1 block text-sm font-medium">Bond Description</span>
                      <input value={position.bond_description} onChange={(e) => setPosition({ ...position, bond_description: e.target.value })} className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="2-year service agreement, exit penalty..." />
                    </label>
                  </div>
                )}
              </div>

              {/* Skills */}
              <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
                <h3 className="text-sm font-semibold mb-2">Required Skills (per role) — search from backend</h3>
                <Field label="Search skills" value={skillQuery} onChange={(e) => setSkillQuery(e.target.value)} placeholder="Type to search: python, java, sql..." />
                <div className="mt-2 max-h-40 overflow-y-auto grid grid-cols-2 gap-1 text-sm">
                  {allSkills.map((sk) => (
                    <label key={sk.id} className="flex items-center gap-2"><input type="checkbox" checked={!!selectedSkills.find((s) => s.skill_id === sk.id)} onChange={() => toggleSkill(sk)} /> {sk.name} <span className="text-xs text-slate500">({sk.category})</span></label>
                  ))}
                  {allSkills.length === 0 && <p className="col-span-2 py-2 text-center text-xs text-slate-500">No skills found for “{skillQuery}”</p>}
                </div>
                {selectedSkills.length > 0 && (
                  <div className="mt-3 space-y-1">
                    {selectedSkills.map((s) => (
                      <div key={s.skill_id} className="flex items-center gap-2 text-xs">
                        <Badge>{s.name}</Badge>
                        <label className="flex items-center gap-1"><input type="checkbox" checked={s.mandatory} onChange={(e) => setSelectedSkills((prev) => prev.map((x) => x.skill_id === s.skill_id ? { ...x, mandatory: e.target.checked } : x))} /> Mandatory</label>
                        <select value={s.skill_level} onChange={(e) => setSelectedSkills((prev) => prev.map((x) => x.skill_id === s.skill_id ? { ...x, skill_level: e.target.value } : x))} className="rounded border px-1 py-0.5 text-xs">
                          <option>BEGINNER</option><option>INTERMEDIATE</option><option>ADVANCED</option><option>EXPERT</option>
                        </select>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Locations */}
              <div className="rounded-md border border-slate-200 bg-slate-50 p-3 space-y-2">
                <h3 className="text-sm font-semibold">Job Locations</h3>
                {locations.map((loc, idx) => (
                  <div key={idx} className="grid grid-cols-4 gap-2">
                    <Field label={idx === 0 ? 'City *' : ''} value={loc.city} onChange={(e) => setLocations((prev) => prev.map((x, i) => i === idx ? { ...x, city: e.target.value } : x))} placeholder="Bangalore" />
                    <Field label={idx === 0 ? 'State' : ''} value={loc.state} onChange={(e) => setLocations((prev) => prev.map((x, i) => i === idx ? { ...x, state: e.target.value } : x))} placeholder="Karnataka" />
                    <Field label={idx === 0 ? 'Country' : ''} value={loc.country} onChange={(e) => setLocations((prev) => prev.map((x, i) => i === idx ? { ...x, country: e.target.value } : x))} />
                    <div className="flex items-end gap-1">
                      <Button type="button" onClick={() => setLocations((prev) => prev.filter((_, i) => i !== idx))} className="bg-red-600 hover:bg-red-700 px-2 py-1 text-xs" disabled={locations.length === 1}>Remove</Button>
                    </div>
                  </div>
                ))}
                <Button type="button" onClick={() => setLocations((prev) => [...prev, { city: '', state: '', country: 'India', work_mode: 'ONSITE' }])} className="bg-slate-600 hover:bg-slate-700 text-xs">+ Add Location</Button>
              </div>

              <Button type="submit">Add Role</Button>
            </form>
            {positions.length > 0 && (
              <div className="mt-4 space-y-2">
                <h3 className="text-sm font-semibold">Added Roles ({positions.length})</h3>
                {positions.map((p) => (
                  <div key={p.id} className="rounded-md border border-green-200 bg-green-50 px-3 py-2 text-sm flex justify-between">
                    <span><b>{p.title}</b> — {p.role} · {p.employment_type} · {p.work_mode} {p.bond_required ? '· 🔒 Bond' : ''}</span>
                    <span className="text-xs text-slate-600">{p.compensation?.is_unpaid ? 'Unpaid' : p.compensation?.stipend_min ? `₹${p.compensation.stipend_min}-${p.compensation.stipend_max}` : p.compensation?.ctc_min ? `${p.compensation.ctc_min}-${p.compensation.ctc_max} LPA` : ''} · {p.locations?.map((l) => l.city).join(', ')}</span>
                  </div>
                ))}
              </div>
            )}
            <div className="mt-4 flex gap-2">
              <Button onClick={() => setStep(3)} disabled={positions.length === 0} className={positions.length === 0 ? 'opacity-50' : ''}>Next — Eligibility & Batches →</Button>
              <Button onClick={() => { if (createdDrive) navigate(`/drives/${createdDrive.id}`)}} disabled={!createdDrive || positions.length === 0} className={`bg-slate-600 hover:bg-slate-700 ${(!createdDrive || positions.length === 0) ? 'opacity-50 cursor-not-allowed' : ''}`}>Finish & View Drive</Button>
            </div>
            {positions.length === 0 && <p className="mt-2 text-xs font-medium text-red-600">Add at least one role — drive will not be created otherwise.</p>}
          </Card>
        </div>
      )}

      {step === 3 && (
        <div className="space-y-4">
          <Card>
            <h2 className="mb-3 font-semibold">3a — Eligibility Criteria</h2>
            <form onSubmit={saveEligibility} className="grid grid-cols-2 gap-3">
              <Field label="Min CGPA" type="number" step="0.01" value={eligibility.minimum_cgpa} onChange={(e) => setEligibility({ ...eligibility, minimum_cgpa: e.target.value })} />
              <Field label="Max Backlogs" type="number" value={eligibility.maximum_backlogs} onChange={(e) => setEligibility({ ...eligibility, maximum_backlogs: e.target.value })} />
              <Field label="Passing Year From" type="number" value={eligibility.passing_year_from} onChange={(e) => setEligibility({ ...eligibility, passing_year_from: e.target.value })} />
              <Field label="Passing Year To" type="number" value={eligibility.passing_year_to} onChange={(e) => setEligibility({ ...eligibility, passing_year_to: e.target.value })} />
              <div className="col-span-2"><Button type="submit">Save Eligibility</Button></div>
            </form>
          </Card>
          <Card>
            <h2 className="mb-3 font-semibold">3b — Eligible Branches</h2>
            <div className="grid grid-cols-3 gap-2">
              {branches.map((b) => (
                <label key={b.id} className="flex items-center gap-2 text-sm"><input type="checkbox" checked={selectedBranches.includes(b.id)} onChange={(e) => setSelectedBranches(e.target.checked ? [...selectedBranches, b.id] : selectedBranches.filter((x) => x !== b.id))} /> {b.code} — {b.name}</label>
              ))}
            </div>
            <Button onClick={saveBranches} className="mt-3">Save Branches</Button>
          </Card>
          <Card>
            <h2 className="mb-3 font-semibold">3c — Eligible Batches</h2>
            <Field label="Graduation Years (comma separated)" value={batchYears} onChange={(e) => setBatchYears(e.target.value)} placeholder="2027, 2028" />
            <Button onClick={saveBatches} className="mt-3">Save Batches</Button>
          </Card>
          <Button onClick={() => setStep(4)}>Next — Rounds & Publish →</Button>
        </div>
      )}

      {step === 4 && (
        <div className="space-y-4">
          <Card>
            <h2 className="mb-3 font-semibold">4 — Recruitment Rounds</h2>
            <form onSubmit={addRound} className="grid grid-cols-2 gap-3">
              <Field label="Round Name *" value={roundForm.name} onChange={(e) => setRoundForm({ ...roundForm, name: e.target.value })} required />
              <label className="block"><span className="mb-1 block text-sm font-medium">Type</span>
                <select value={roundForm.type} onChange={(e) => setRoundForm({ ...roundForm, type: e.target.value })} className="w-full rounded-md border px-3 py-2 text-sm">
                  <option>APTITUDE</option><option>CODING</option><option>GROUP_DISCUSSION</option><option>TECHNICAL_INTERVIEW</option><option>HR_INTERVIEW</option><option>ASSESSMENT</option><option>OTHER</option>
                </select>
              </label>
              <Button type="submit" className="col-span-2">Add Round</Button>
            </form>
            {rounds.length > 0 && <ul className="mt-3 list-disc pl-5 text-sm">{rounds.map((r) => <li key={r.id}>{r.sequence}. {r.name} — {r.type}</li>)}</ul>}
          </Card>
          <Card>
            <h2 className="mb-2 font-semibold">Publish Drive</h2>
            <p className="mb-3 text-sm text-slate-600">Once published, eligible students can apply per role.</p>
            <Button onClick={publish}>Publish Drive</Button>
            <Button onClick={() => navigate(`/drives/${createdDrive.id}`)} className="ml-2 bg-slate-600 hover:bg-slate-700">View Drive</Button>
          </Card>
        </div>
      )}
    </div>
  )
}
