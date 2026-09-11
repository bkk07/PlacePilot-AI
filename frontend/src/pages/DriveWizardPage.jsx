import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button, Card, ErrorBanner, Field, PageTitle } from '../components/ui.jsx'
import { api, errorMessage } from '../lib/api.js'

const EMPTY_DRIVE = {
  title: '', description: '', drive_type: 'ON_CAMPUS', mode: 'OFFLINE',
  registration_start: '', registration_end: '', drive_start_date: '', drive_end_date: '',
  venue: '', meeting_link: '', application_limit: '', instructions: '',
}
const EMPTY_POSITION = { title: '', role: '', employment_type: 'FULL_TIME', openings: '', work_mode: 'ONSITE', job_description: '' }

export default function DriveWizardPage() {
  const navigate = useNavigate()
  const [step, setStep] = useState(1)
  const [companies, setCompanies] = useState([])
  const [drive, setDrive] = useState({ ...EMPTY_DRIVE, company_id: '' })
  const [createdDrive, setCreatedDrive] = useState(null)
  const [position, setPosition] = useState({ ...EMPTY_POSITION })
  const [positions, setPositions] = useState([])
  const [error, setError] = useState(null)
  const [notice, setNotice] = useState(null)
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
    if (step === 3 && createdDrive) {
      api.listBranches().then(setBranches).catch(() => {})
      api.getDriveBranches(createdDrive.id).then((r) => setSelectedBranches(r.map((x) => x.branch_id))).catch(() => {})
      api.getDriveBatches(createdDrive.id).then((r) => setBatchYears(r.map((x) => x.graduation_year).join(', '))).catch(() => {})
    }
    if (step === 4 && createdDrive) {
      api.listRounds(createdDrive.id).then(setRounds).catch(() => {})
    }
  }, [step, createdDrive])

  async function createDrive(e) {
    e.preventDefault(); setError(null)
    try {
      const payload = {
        ...drive,
        application_limit: drive.application_limit ? Number(drive.application_limit) : null,
        registration_start: drive.registration_start || null,
        registration_end: drive.registration_end || null,
        drive_start_date: drive.drive_start_date || null,
        drive_end_date: drive.drive_end_date || null,
      }
      const created = await api.createDrive(payload)
      setCreatedDrive(created); setNotice(`Drive "${created.title}" created — now add job positions.`); setStep(2)
    } catch (err) { setError(errorMessage(err)) }
  }
  async function addPosition(e) {
    e.preventDefault(); setError(null)
    try {
      const payload = { ...position, openings: position.openings === '' || position.openings === null ? null : Number(position.openings) }
      if (payload.openings === null) delete payload.openings
      const created = await api.createJobPosition(createdDrive.id, payload)
      setPositions((p) => [...p, created]); setPosition({ ...EMPTY_POSITION }); setNotice('Position added.')
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
    <div className="mx-auto max-w-3xl">
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
          <h2 className="mb-3 font-semibold">1 — Drive Basics</h2>
          <form onSubmit={createDrive} className="space-y-3">
            <label className="block"><span className="mb-1 block text-sm font-medium">Company *</span>
              <select value={drive.company_id} onChange={(e) => setDrive({ ...drive, company_id: e.target.value })} className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" required>
                <option value="">Select company</option>{companies.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </label>
            <Field label="Title *" value={drive.title} onChange={(e) => setDrive({ ...drive, title: e.target.value })} required />
            <Field label="Description" value={drive.description} onChange={(e) => setDrive({ ...drive, description: e.target.value })} />
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
            <Field label="Venue" value={drive.venue} onChange={(e) => setDrive({ ...drive, venue: e.target.value })} />
            <Field label="Meeting Link" value={drive.meeting_link} onChange={(e) => setDrive({ ...drive, meeting_link: e.target.value })} />
            <Button type="submit">Create Drive & Continue</Button>
          </form>
        </Card>
      )}

      {step === 2 && (
        <Card>
          <h2 className="mb-3 font-semibold">2 — Job Positions</h2>
          <p className="mb-3 text-sm text-slate-600">Drive: <b>{createdDrive?.title}</b> — add one or multiple positions.</p>
          <form onSubmit={addPosition} className="space-y-3">
            <Field label="Position Title *" value={position.title} onChange={(e) => setPosition({ ...position, title: e.target.value })} required />
            <div className="grid grid-cols-2 gap-3">
              <Field label="Role" value={position.role} onChange={(e) => setPosition({ ...position, role: e.target.value })} />
              <Field label="Openings (optional)" type="number" min="1" placeholder="Leave blank if not fixed" value={position.openings} onChange={(e) => setPosition({ ...position, openings: e.target.value === '' ? '' : Number(e.target.value) })} />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <label className="block"><span className="mb-1 block text-sm font-medium">Employment Type</span>
                <select value={position.employment_type} onChange={(e) => setPosition({ ...position, employment_type: e.target.value })} className="w-full rounded-md border px-3 py-2 text-sm">
                  <option>FULL_TIME</option><option>INTERNSHIP</option><option>INTERNSHIP_TO_FULL_TIME</option><option>CONTRACT</option>
                </select>
              </label>
              <Field label="Work Mode" value={position.work_mode} onChange={(e) => setPosition({ ...position, work_mode: e.target.value })} />
            </div>
            <Button type="submit">Add Position</Button>
          </form>
          {positions.length > 0 && <ul className="mt-4 list-disc pl-5 text-sm">{positions.map((p) => <li key={p.id}>{p.title} — {p.role}</li>)}</ul>}
          <div className="mt-4 flex gap-2">
            <Button onClick={() => setStep(3)}>Next — Eligibility & Batches →</Button>
            <Button onClick={() => navigate(`/drives/${createdDrive.id}`)} className="bg-slate-600 hover:bg-slate-700">Finish & View Drive</Button>
          </div>
        </Card>
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
            <p className="mb-3 text-sm text-slate-600">Once published, eligible students can apply and the pipeline (Application → Shortlist → RoundResult → Selection → Offer → PlacementOutcome) begins.</p>
            <Button onClick={publish}>Publish Drive</Button>
            <Button onClick={() => navigate(`/drives/${createdDrive.id}`)} className="ml-2 bg-slate-600 hover:bg-slate-700">View Drive</Button>
          </Card>
        </div>
      )}
    </div>
  )
}
