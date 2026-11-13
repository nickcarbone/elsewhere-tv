#!/usr/bin/env python3
"""Re-verify channels.json against YouTube. No API key, standard library only.

Usage:  python3 scripts/check_channels.py [--write]

For every YouTube channel it looks up the current live broadcast, then updates
status, liveNowAtCheck, embedding and lastVerified. The saved videoId is
replaced only for channels Breaking Wall does not manage (no breakingWallKey).
Without --write it only prints a report.

Safety: if more than 40% of lookups fail, or more than 60% of channels come
back off air, YouTube is probably refusing or walling this network (common on
cloud runners), so nothing is written.
"""
import datetime, json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import yt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "channels.json")

def main():
    write = "--write" in sys.argv
    data = json.load(open(PATH, encoding="utf-8"))
    today = datetime.date.today().isoformat()
    checked = failed = changed = offair = 0
    pending = []
    for ch in data["channels"]:
        if not ch.get("channelId"):
            continue
        checked += 1
        res = yt.lookup(ch["channelId"])
        if res.get("error") == "HTTP 429":
            time.sleep(30); res = yt.lookup(ch["channelId"])
        time.sleep(1.3)
        if not res.get("ok"):
            failed += 1; print(f"LOOKUP FAILED  {ch['id']}: {res.get('error')}"); continue
        new = dict(ch)
        live = bool(res.get("isLive"))
        new["liveNowAtCheck"] = live
        new["status"] = "verified-live" if live else "off-air-at-check"
        new["lastVerified"] = today
        if live and res.get("videoId"):
            emb = yt.embeddable(res["videoId"])
            if ch.get("embed") != "external":
                new["embedding"] = "confirmed" if emb else "blocked" if emb is False else "unknown"
            if not ch.get("breakingWallKey") and (ch.get("embed") == "channel" or not ch.get("videoId") or yt.embeddable(ch["videoId"]) is not True):
                new["videoId"] = res["videoId"]
        if res.get("channel"): new["youtubeChannelName"] = res["channel"]
        if not live:
            offair += 1; print(f"OFF AIR        {ch['id']}")
        elif new.get("videoId") != ch.get("videoId"): print(f"NEW LINK       {ch['id']}: {ch.get('videoId')} -> {new['videoId']}")
        if {k: v for k, v in new.items() if k != "lastVerified"} != {k: v for k, v in ch.items() if k != "lastVerified"}: changed += 1
        pending.append((ch, new))
    print(f"\n{checked} checked, {failed} lookups failed, {changed} records changed")
    if checked and failed / checked > 0.4:
        print("Too many failures: YouTube is likely blocking this network. Nothing written."); return 2
    if checked and offair / checked > 0.6:
        print("Most channels look off air: YouTube is likely walling this network. Nothing written."); return 2
    if write:
        for ch, new in pending: ch.update(new)
        data["generated"] = today
        json.dump(data, open(PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("channels.json updated")
    return 0

if __name__ == "__main__":
    sys.exit(main())
