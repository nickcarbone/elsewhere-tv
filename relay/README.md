# Elsewhere relay (Cloudflare Worker)

Rai News 24 and ČT24 only give out short-lived stream addresses, and their services refuse calls from other websites. This Worker fetches a fresh address and hands it to Elsewhere TV. The video still streams straight from the broadcaster to the viewer; only a few hundred bytes of JSON pass through the Worker.

Until the relay is set up, those two channels keep working as "opens site" links. Everything else plays without it.

## Set it up (dashboard only, about five minutes)

1. Sign in at dash.cloudflare.com and open **Workers & Pages** (under Compute in the left-hand menu).
2. Choose **Create application**, then **Create Worker** (or "Start with Hello World").
3. Name it `elsewhere-relay` and press **Deploy**. Cloudflare deploys its Hello World code first; that's expected.
4. On the Worker's page, choose **Edit code**. Delete everything in `worker.js`, paste in the whole of [`worker.js`](worker.js) from this folder, then press **Deploy**.
5. Copy the Worker's address from the top of its page. It looks like `https://elsewhere-relay.YOUR-SUBDOMAIN.workers.dev`. If Cloudflare asks you to choose a workers.dev subdomain first, pick anything.

## Test it

Open these in your browser. Each should show a line of JSON with a `"url"`:

- `https://elsewhere-relay.YOUR-SUBDOMAIN.workers.dev/health`
- `https://elsewhere-relay.YOUR-SUBDOMAIN.workers.dev/resolve/rai-news-24`
- `https://elsewhere-relay.YOUR-SUBDOMAIN.workers.dev/resolve/ct24`

An `"error"` instead means the broadcaster refused the Worker. The usual causes are a changed API or a block on Cloudflare's addresses.

## Switch it on

In GitHub, edit `channels.json` and fill in the empty `relayBase` near the top:

```json
"relayBase": "https://elsewhere-relay.YOUR-SUBDOMAIN.workers.dev",
```

Commit. Once Pages has rebuilt, Rai News 24 and ČT24 play on the dial and on Elsewhere Lite. If a relayed stream fails to start within 20 seconds, the page falls back to the broadcaster's own player link.

## Known risks

- **ČT24** returns an address marked `skipIpAddressCheck=false`, which suggests ČT ties it to the IP that asked for it. Here that would be Cloudflare's, so the stream may refuse your browser. If it does, the page falls back to the link, and you can delete `"hlsResolver": "ct24"` and set `"embed": "external"` for that channel.
- **Rai News 24**'s token lasts about 150 seconds. The Worker reuses each address for 60 seconds at most.
- Only `https://nickcarbone.github.io` may call the relay from a web page. To allow another site, add it to `ALLOWED_ORIGINS` at the top of `worker.js`.
- The free Workers plan allows 100,000 requests a day; each channel change costs one.

## Adding another channel

Add an entry to `SOURCES` in `worker.js` with a `ttl` (seconds) and a `resolve()` that returns an `https://` stream address. In `channels.json`, set `"embed": "hls"` and `"hlsResolver": "<the same key>"` on the channel.
