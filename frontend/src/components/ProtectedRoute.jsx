import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'

export default function ProtectedRoute({ roles, children } = {}) {
  const { user, loading } = useAuth()

  if (loading) {
    return <div className="p-10 text-center text-slate-500">Loading…</div>
  }
  if (!user) {
    return <Navigate to="/login" replace />
  }
  if (roles && roles.length > 0 && !roles.includes(user.role)) {
    return (
      <div className="mx-auto max-w-2xl p-10 text-center">
        <h1 className="text-xl font-semibold text-slate-900">Access denied</h1>
        <p className="mt-2 text-sm text-slate-600">
          This page is only for <b>{roles.join(' / ')}</b> — your role is <b>{user.role}</b>.
        </p>
        <button
          type="button"
          onClick={() => window.history.back()}
          className="mt-4 rounded-md border border-slate-300 px-4 py-1.5 text-sm font-medium"
        >
          Go back
        </button>
      </div>
    )
  }
  if (children) return children
  return <Outlet />
}
