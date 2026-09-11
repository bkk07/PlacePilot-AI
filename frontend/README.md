# Frontend (React + Vite + Tailwind CSS)

Student-facing UI over the Phase 6 FastAPI backend.

```bash
npm install
npm run dev     # http://localhost:5173 (proxies /api -> http://127.0.0.1:8000)
npm run build   # production build to dist/
npm run lint    # oxlint
```

`VITE_API_URL` (default `/api`) controls the API base; the Vite dev server proxies `/api`
to the backend at `127.0.0.1:8000`.

## Pages

| Route | Page |
|---|---|
| `/login`, `/signup` | Auth (JWT stored in localStorage) |
| `/` | Dashboard (profile summary, applications, quick links) |
| `/drives` | Drive listing with search/company/role filters |
| `/drives/:driveId` | Drive details + eligibility + apply |
| `/profile` | Create/edit student profile |
| `/applications` | Applications list + withdraw |
| `/chat` | AI assistant chat against `POST /ai/chat` |

Demo login: `asha@college.edu` / `student-pass`.