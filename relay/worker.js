// Elsewhere TV relay — a Cloudflare Worker.
//
// Some broadcasters hand out their live stream only as a short-lived, signed
// address, from a service that a page on another site cannot call. This Worker
// calls that service and returns the address as JSON:
//
//   GET /resolve/rai-news-24  ->  {"url": "https://...m3u8?token...", "ttl": 60}
//   GET /resolve/ct24         ->  {"url": "https://...", "ttl": 600}
//   GET /health               ->  {"ok": true, "sources": [...]}
//
// The video itself never passes through the Worker: the viewer's browser plays
// it straight from the broadcaster's CDN. Each answer is remembered for a
// little less than the token's life, so the Worker makes few upstream calls.

const ALLOWED_ORIGINS = [
  'https://nickcarbone.github.io',
];

const UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36';

const SOURCES = {
  // RAI's "relinker" answers with an Akamai address carrying an hdnea token
  // that lasts about 150 seconds. Rai News 24 is cont=1.
  'rai-news-24': {
    ttl: 60,
    async resolve() {
      const res = await fetch('https://mediapolis.rai.it/relinker/relinkerServlet.htm?cont=1&output=64', {
        headers: { 'User-Agent': UA, 'Referer': 'https://www.rainews.it/' },
      });
      if (!res.ok) throw new Error(`relinker HTTP ${res.status}`);
      const xml = await res.text();
      const m = xml.match(/<url type="content">\s*<!\[CDATA\[(https:[^\]]+)\]\]>/);
      if (!m) throw new Error('relinker gave no stream address');
      return m[1].trim();
    },
  },
  // Česká televize's live API returns a CDN address valid for about an hour.
  'ct24': {
    ttl: 600,
    async resolve() {
      const api = 'https://api.ceskatelevize.cz/video/v1/playlist-live/v1/stream-data/channel/CH_24'
        + '?canPlayDrm=false&streamType=hls&quality=web&maxQualityCount=5';
      const res = await fetch(api, {
        headers: { 'User-Agent': UA, 'Referer': 'https://ct24.ceskatelevize.cz/', 'Accept': 'application/json' },
      });
      if (!res.ok) throw new Error(`ČT API HTTP ${res.status}`);
      const body = await res.json();
      if (body.isBlocked) throw new Error('ČT reports the stream blocked');
      const url = body.streamUrls && body.streamUrls.main;
      if (!url) throw new Error('ČT API gave no stream address');
      return url;
    },
  },
};

function corsHeaders(origin) {
  const h = { 'Vary': 'Origin' };
  if (origin && ALLOWED_ORIGINS.includes(origin)) {
    h['Access-Control-Allow-Origin'] = origin;
    h['Access-Control-Allow-Methods'] = 'GET, OPTIONS';
    h['Access-Control-Max-Age'] = '86400';
  }
  return h;
}

function json(body, status, origin, maxAge) {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
      'Cache-Control': maxAge ? `public, max-age=${maxAge}` : 'no-store',
      ...corsHeaders(origin),
    },
  });
}

const memo = new Map();

export default {
  async fetch(request, env, ctx) {
    const origin = request.headers.get('Origin');
    // Other sites may not use this relay. Requests with no Origin (you,
    // typing the address into a browser to test) are allowed.
    if (origin && !ALLOWED_ORIGINS.includes(origin)) return json({ error: 'origin not allowed' }, 403, null);
    if (request.method === 'OPTIONS') return new Response(null, { status: 204, headers: corsHeaders(origin) });
    if (request.method !== 'GET') return json({ error: 'method not allowed' }, 405, origin);

    const path = new URL(request.url).pathname.replace(/\/+$/, '');
    if (path === '/health' || path === '') return json({ ok: true, sources: Object.keys(SOURCES) }, 200, origin);

    const m = path.match(/^\/resolve\/([a-z0-9-]+)$/);
    const source = m && SOURCES[m[1]];
    if (!source) return json({ error: 'unknown channel' }, 404, origin);

    // Remember each answer for a little less than its token's life. The memory
    // lives in the Worker instance, which Cloudflare keeps warm between calls
    // (the Cache API would do nothing on a workers.dev address).
    const now = Date.now();
    let hit = memo.get(m[1]);
    if (!hit || hit.expires <= now) {
      let url;
      try { url = await source.resolve(); }
      catch (e) { return json({ error: String(e.message || e) }, 502, origin); }
      hit = { body: { url, ttl: source.ttl }, expires: now + source.ttl * 1000 };
      memo.set(m[1], hit);
    }
    return json(hit.body, 200, origin, 0);
  },
};
