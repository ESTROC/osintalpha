/*
 * OSINT Alpha same-origin API reverse proxy.
 * Routes /api/* on Vercel to the separately deployed Render FastAPI service.
 * A single same-origin URL preserves HttpOnly session cookies and avoids
 * insecure cross-site credential handling.
 */
export default async function handler(req, res) {
  const backend = process.env.OSINTALPHA_BACKEND_URL;
  if (!backend) return res.status(503).json({
    detail: 'Backend not configured. Set OSINTALPHA_BACKEND_URL to the Render HTTPS origin.'
  });
  let origin;
  try {
    origin = new URL(backend);
    if (origin.protocol !== 'https:' || origin.username || origin.password || origin.pathname !== '/' || origin.search || origin.hash)
      throw new Error('Invalid backend origin');
  } catch {
    return res.status(503).json({detail: 'Backend origin is invalid.'});
  }
  const incoming = new URL(req.url, 'https://frontend.invalid');
  if (!incoming.pathname.startsWith('/api/'))
    return res.status(404).json({detail:'Not found'});
  const dest = new URL(incoming.pathname + incoming.search, origin);
  const blocked = new Set(['host','connection','content-length','transfer-encoding','accept-encoding']);
  const headers = new Headers();
  for (const [key,value] of Object.entries(req.headers || {})) {
    if (!blocked.has(key.toLowerCase()) && value != null)
      headers.set(key, Array.isArray(value) ? value.join(', ') : String(value));
  }
  let body;
  if (req.method !== 'GET' && req.method !== 'HEAD') {
    const v = req.body;
    if (Buffer.isBuffer(v)) body = v;
    else if (typeof v === 'string') body = v;
    else if (v != null) {
      body = JSON.stringify(v);
      if (!headers.has('content-type')) headers.set('content-type','application/json');
    }
  }
  try {
    const upstream = await fetch(dest, {
      method: req.method, headers, body, redirect: 'manual',
      signal: AbortSignal.timeout(55000)
    });
    res.status(upstream.status);
    for (const [k,v] of upstream.headers.entries()) {
      if (!['content-length','content-encoding','transfer-encoding','connection','set-cookie'].includes(k.toLowerCase()))
        res.setHeader(k, v);
    }
    const cookies = upstream.headers.getSetCookie?.() || [];
    if (cookies.length) res.setHeader('Set-Cookie', cookies);
    else if (upstream.headers.get('set-cookie')) res.setHeader('Set-Cookie', upstream.headers.get('set-cookie'));
    res.setHeader('Cache-Control', 'no-store');
    res.end(Buffer.from(await upstream.arrayBuffer()));
  } catch {
    res.status(502).json({detail:'Backend unavailable. Check Render service health and proxy configuration.'});
  }
}
