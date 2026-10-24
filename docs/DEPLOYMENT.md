# Deployment (prototype only)

## Backend: Render
Use Render -> New -> Blueprint -> connect ESTROC/osintalpha, then apply `render.yaml`.
The Dockerfile serves FastAPI on port 8000 and exposes `/api/health`.
The Blueprint generates `OSINTALPHA_ADMIN_PASSWORD`; get it privately from your Render environment settings. Do not put it in GitHub, ChatGPT, or frontend environment variables.

IMPORTANT: The Free service has **ephemeral SQLite storage**. Restarts or redeployments can delete investigations and evidence. Do not put personal or customer investigations into this configuration. For persistence, move to a durable managed database and complete a production security review.

## Frontend: Vercel
Import the same repo, set Root Directory to `static`, Framework Preset = Other.
Set `OSINTALPHA_BACKEND_URL` in Vercel Production & Preview to the exact Render HTTPS origin, e.g. `https://<actual-render-host>.onrender.com` (do not include /api).
The Vercel Node API function at `static/api/[...path].js` is a same-origin proxy. It forwards cookies, requests and reports.

Site assets under /assets/* are rewritten to the static project root. Direct backend URL is not used by the browser; login and reports work via the Vercel domain.

## Validation
- GET Render /api/health -> 200 JSON
- GET Vercel / -> 200 HTML
- GET Vercel /assets/app.js -> 200 JavaScript
- GET Vercel /api/health -> 200 JSON (proves proxy)
- POST /api/auth/login, followed by GET /api/auth/me on Vercel (checks session cookie)
- Create a synthetic authorized case; export PDF; verify no errors.
- Confirm all report and evidence endpoints require login.

## Security
This is a single-admin prototype, not a multi-tenant commercial deployment. Use only synthetic demo inputs. Before handling real person data, implement durable storage, authentication hardening, retention, secure audits and independent security review.
