import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Button, Card, ErrorBanner, Field } from '../components/ui.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import { errorMessage } from '../lib/api.js'

export default function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('asha@college.edu')
  const [password, setPassword] = useState('student-pass')
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  async function onSubmit(e) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await login(email, password)
      navigate('/')
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-100 px-4">
      <Card className="w-full max-w-md">
        <h1 className="mb-1 text-2xl font-semibold text-slate-900">Sign in</h1>
        <p className="mb-1 text-sm text-slate-500">PlacePilot AI — Student & TNPC Admin</p>
        <div className="mb-4 rounded-md bg-slate-50 px-3 py-2 text-xs text-slate-600">
          <p className="font-medium">Demo accounts:</p>
          <p>Student: <code>asha@college.edu</code> / <code>student-pass</code></p>
          <p>TNPC Admin: <code>placement@college.edu</code> / <code>admin-pass</code></p>
        </div>
        <ErrorBanner message={error} />
        <form onSubmit={onSubmit} className="space-y-4">
          <Field
            label="Email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <Field
            label="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          <Button type="submit" disabled={busy} className="w-full">
            {busy ? 'Signing in…' : 'Sign in'}
          </Button>
        </form>
        <p className="mt-4 text-sm text-slate-600">
          No account?{' '}
          <Link to="/signup" className="font-medium text-indigo-600 hover:underline">
            Create one
          </Link>
        </p>
      </Card>
    </div>
  )
}