const BASE = import.meta.env.VITE_API_URL ?? '/api'

export const TOKEN_KEY = 'placepilot_token'

export class ApiError extends Error {
  constructor(status, detail) {
    super(typeof detail === 'string' ? detail : `Request failed (${status})`)
    this.status = status
    this.detail = detail
  }
}

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY)
}

function parseBody(text) {
  if (!text) return null
  try {
    return JSON.parse(text)
  } catch {
    return text
  }
}

async function request(path, options = {}) {
  const headers = { ...(options.headers ?? {}) }
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`
  if (options.body && !(options.body instanceof FormData)) headers['Content-Type'] = 'application/json'

  const res = await fetch(`${BASE}${path}`, { ...options, headers })
  const data = parseBody(await res.text())
  if (!res.ok) {
    if (res.status === 401) {
      clearToken()
    }
    const detail =
      data && typeof data === 'object' && 'detail' in data ? data.detail : data
    throw new ApiError(res.status, detail)
  }
  return data
}

export const api = {
  signup: (body) => request('/auth/signup', { method: 'POST', body: JSON.stringify(body) }),

  login: (body) => request('/auth/login', { method: 'POST', body: JSON.stringify(body) }),

  me: () => request('/auth/me'),

  getProfile: () => request('/students/me/profile'),

  saveProfile: (body) =>
    request('/students/me/profile', { method: 'PUT', body: JSON.stringify(body) }),

  uploadProfilePhoto: (file) => {
    const fd = new FormData()
    fd.append('file', file)
    return request('/students/me/profile/photo', { method: 'POST', body: fd })
  },

  getProfilePhotoUrl: () => `${BASE}/students/me/profile/photo`,

  getProfilePhotoBlob: async () => {
    const token = getToken()
    const headers = {}
    if (token) headers.Authorization = `Bearer ${token}`
    const res = await fetch(`${BASE}/students/me/profile/photo`, { headers })
    if (!res.ok) {
      const data = parseBody(await res.text())
      throw new ApiError(res.status, data?.detail ?? data)
    }
    return res.blob()
  },

  checkEligibility: (driveId) => request(`/students/me/eligibility/${driveId}`),

  listDrives: (filters = {}) => {
    const params = new URLSearchParams()
    if (filters.query) params.set('query', filters.query)
    if (filters.company) params.set('company', filters.company)
    if (filters.role) params.set('role', filters.role)
    if (filters.status) params.set('status', filters.status)
    if (filters.skip != null) params.set('skip', String(filters.skip))
    if (filters.limit != null) params.set('limit', String(filters.limit))
    const qs = params.toString()
    return request(`/drives${qs ? `?${qs}` : ''}`)
  },

  getDrive: (driveId) => request(`/drives/${driveId}`),

  createDrive: (body) => request('/drives', { method: 'POST', body: JSON.stringify(body) }),

  updateDrive: (driveId, body) => request(`/drives/${driveId}`, { method: 'PUT', body: JSON.stringify(body) }),

  apply: (driveId, jobPositionId = null) =>
    request('/applications', {
      method: 'POST',
      body: JSON.stringify({ drive_id: driveId, job_position_id: jobPositionId }),
    }),

  listApplications: () => request('/applications'),

  withdraw: (applicationId) =>
    request(`/applications/${applicationId}`, {
      method: 'PATCH',
      body: JSON.stringify({ status: 'withdrawn' }),
    }),

  chat: (message, threadId) =>
    request('/ai/chat', {
      method: 'POST',
      body: JSON.stringify({ message, thread_id: threadId }),
    }),

  // SSE chat stream: onEvent(stage, data) receives intent/tools/reply/citations/done/error.
  chatStream: async (message, threadId, onEvent, token = getToken()) => {
    const res = await fetch(`${BASE}/ai/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ message, thread_id: threadId }),
    })
    if (!res.ok) {
      const data = parseBody(await res.text())
      throw new ApiError(res.status, data?.detail ?? data)
    }
    if (!res.body) throw new Error('no stream body')

    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      let sep
      while ((sep = buffer.indexOf('\n\n')) !== -1) {
        const frame = buffer.slice(0, sep)
        buffer = buffer.slice(sep + 2)
        let stage = null
        let data = {}
        for (const line of frame.split('\n')) {
          if (line.startsWith('event: ')) stage = line.slice(7).trim()
          else if (line.startsWith('data: ')) {
            try {
              data = JSON.parse(line.slice(6))
            } catch {
              /* ignore malformed frame */
            }
          }
        }
        if (stage && stage !== 'ping') onEvent(stage, data)
      }
    }
  },

  // — TNPC domain (new) —
  listCompanies: () => request('/companies'),
  createCompany: (body) => request('/companies', { method: 'POST', body: JSON.stringify(body) }),
  getCompany: (id) => request(`/companies/${id}`),
  updateCompany: (id, body) => request(`/companies/${id}`, { method: 'PUT', body: JSON.stringify(body) }),

  listJobPositions: (driveId) => request(`/drives/${driveId}/positions`),
  createJobPosition: (driveId, body) =>
    request(`/drives/${driveId}/positions`, { method: 'POST', body: JSON.stringify(body) }),

  listSkills: (q = '') => {
    const params = new URLSearchParams()
    if (q) params.set('q', q)
    const qs = params.toString()
    return request(`/skills${qs ? `?${qs}` : ''}`)
  },
  createSkill: (body) => request('/skills', { method: 'POST', body: JSON.stringify(body) }),

  getEligibility: (driveId) => request(`/drives/${driveId}/eligibility-criteria`),
  saveEligibility: (driveId, body) =>
    request(`/drives/${driveId}/eligibility-criteria`, { method: 'PUT', body: JSON.stringify(body) }),

  listBranches: () => request('/branches'),
  getDriveBranches: (driveId) => request(`/drives/${driveId}/branches`),
  saveDriveBranches: (driveId, branchIds) =>
    request(`/drives/${driveId}/branches`, { method: 'PUT', body: JSON.stringify({ branch_ids: branchIds }) }),

  getDriveBatches: (driveId) => request(`/drives/${driveId}/batches`),
  saveDriveBatches: (driveId, years) =>
    request(`/drives/${driveId}/batches`, { method: 'PUT', body: JSON.stringify({ years }) }),

  listRounds: (driveId) => request(`/drives/${driveId}/rounds`),
  createRound: (driveId, body) =>
    request(`/drives/${driveId}/rounds`, { method: 'POST', body: JSON.stringify(body) }),

  listSchedules: (driveId) => request(`/drives/${driveId}/schedules`),
  createSchedule: (driveId, body) =>
    request(`/drives/${driveId}/schedules`, { method: 'POST', body: JSON.stringify(body) }),

  listAnnouncements: (driveId) => request(`/drives/${driveId}/announcements`),
  createAnnouncement: (driveId, body) =>
    request(`/drives/${driveId}/announcements`, { method: 'POST', body: JSON.stringify(body) }),

  publishDrive: (driveId) => request(`/drives/${driveId}/publish`, { method: 'POST' }),
  getDrivePipeline: (driveId) => request(`/drives/${driveId}/pipeline`),

  listDriveApplications: (driveId) => request(`/drives/${driveId}/applications`),
  updateApplicationStatus: (appId, status, reason) =>
    request(`/applications/${appId}`, { method: 'PATCH', body: JSON.stringify({ status, reason }) }),
}

export function errorMessage(err) {
  if (err instanceof ApiError) {
    const detail = err.detail
    if (typeof detail === 'string') return detail
    if (detail && typeof detail === 'object') {
      if ('message' in detail && typeof detail.message === 'string') return detail.message
      if ('reasons' in detail && Array.isArray(detail.reasons)) return detail.reasons.join('; ')
      if (Array.isArray(detail) && detail.length > 0) {
        const first = detail[0]
        if (first?.msg) return detail.map((d) => d.msg).join('; ')
      }
      try {
        return JSON.stringify(detail)
      } catch {
        return `Request failed (${err.status})`
      }
    }
    return `Request failed (${err.status})`
  }
  if (err instanceof Error) return err.message
  return 'Something went wrong'
}