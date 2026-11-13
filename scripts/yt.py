"""Keyless YouTube live lookup. Stdlib only."""
import json, re, urllib.request, urllib.parse, urllib.error
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
def _get(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.8", "Cookie": "CONSENT=YES+1; SOCS=CAI"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read().decode("utf-8", "replace")
def _initial(html):
    m = re.search(r"var ytInitialData\s*=\s*(\{.+?\});\s*</script>", html, re.S)
    return json.loads(m.group(1)) if m else None
def _find(o, key):
    if isinstance(o, dict):
        if key in o: yield o[key]
        for v in o.values(): yield from _find(v, key)
    elif isinstance(o, list):
        for v in o: yield from _find(v, key)
def _text(x):
    if not isinstance(x, dict): return None
    if "simpleText" in x: return x["simpleText"]
    return "".join(r.get("text", "") for r in x.get("runs", [])) or None
def embeddable(video_id):
    """True/False via oEmbed (401 = embedding disabled), None if unknown."""
    u = "https://www.youtube.com/oembed?format=json&url=" + urllib.parse.quote("https://www.youtube.com/watch?v=" + video_id, safe="")
    try:
        s, _ = _get(u, 15); return s == 200
    except urllib.error.HTTPError as e:
        return False if e.code in (401, 403) else None
    except Exception:
        return None
def lookup(ref):
    """ref: UC… channel id, @handle, or video id (v:ID). Returns dict."""
    out = {"ref": ref, "ok": False}
    if ref.startswith("v:"): url = "https://www.youtube.com/watch?v=" + ref[2:]
    elif ref.startswith("UC") and len(ref) == 24: url = f"https://www.youtube.com/channel/{ref}/live"
    else: url = f"https://www.youtube.com/{ref if ref.startswith('@') else '@'+ref}/live"
    try:
        s, html = _get(url)
    except urllib.error.HTTPError as e:
        out["error"] = f"HTTP {e.code}"; return out
    except Exception as e:
        out["error"] = type(e).__name__; return out
    d = _initial(html)
    if not d: out["error"] = "no data"; return out
    out["ok"] = True
    cve = d.get("currentVideoEndpoint", {}).get("watchEndpoint", {})
    if cve.get("videoId"):
        out["videoId"] = cve["videoId"]
        prim = next(_find(d, "videoPrimaryInfoRenderer"), {})
        out["title"] = _text(prim.get("title"))
        vc = prim.get("viewCount", {}).get("videoViewCountRenderer", {})
        out["watching"] = _text(vc.get("viewCount")) or _text(vc.get("originalViewCount"))
        # A scheduled stream that has not started reports isLive with a
        # "waiting" count; treat it as upcoming, not live.
        out["upcoming"] = "waiting" in (out["watching"] or "")
        out["isLive"] = bool(vc.get("isLive")) and not out["upcoming"]
        own = next(_find(d, "videoOwnerRenderer"), {})
        out["channel"] = _text(own.get("title"))
        out["subs"] = _text(own.get("subscriberCountText"))
        be = next(_find(own, "browseId"), None); out["channelId"] = be
        out["verified"] = any("VERIFIED" in json.dumps(b) for b in own.get("badges", []))
        out["embeddable"] = embeddable(out["videoId"])
    else:
        md = next(_find(d, "channelMetadataRenderer"), {})
        out["channel"] = md.get("title"); out["channelId"] = md.get("externalId"); out["isLive"] = False
        out["note"] = "channel page (no single live broadcast)"
    return out
if __name__ == "__main__":
    import sys
    for r in sys.argv[1:]: print(json.dumps(lookup(r), ensure_ascii=False))

def streams(channel_id):
    """Live broadcasts listed on a channel's Live tab: [(videoId, title, viewers)]."""
    try:
        s, html = _get(f"https://www.youtube.com/channel/{channel_id}/streams")
    except Exception:
        return None
    d = _initial(html)
    if not d: return None
    out = []
    for v in _find(d, "lockupViewModel"):
        j = json.dumps(v, ensure_ascii=False)
        if "THUMBNAIL_OVERLAY_BADGE_STYLE_LIVE" not in j: continue
        try: title = v["metadata"]["lockupMetadataViewModel"]["title"]["content"]
        except Exception: title = None
        m = re.search(r'"content": "([\d.,KM]+ watching)"', j)
        out.append((v.get("contentId"), title, m.group(1) if m else None))
    for v in _find(d, "videoRenderer"):
        if '"style": "LIVE"' in json.dumps(v.get("thumbnailOverlays", [])):
            out.append((v.get("videoId"), _text(v.get("title")), _text(v.get("viewCountText"))))
    return out
