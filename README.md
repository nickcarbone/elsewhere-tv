# ELSEWHERE TV

A hotel-room window onto everyday television around the world. Pick a country, switch on, and watch what people there are watching, in their own language.

## Files

| File | What it does |
|---|---|
| `index.html` | The whole interface: player, guide, discovery dial. No build step, no framework. |
| `channels.json` | The channel catalogue. Edit this to add, remove or fix channels. |
| `scripts/yt.py` | Keyless YouTube lookup used by the checker (standard library only). |
| `scripts/check_channels.py` | Re-verifies every channel and rewrites `channels.json`. |
| `.github/workflows/check-channels.yml` | Optional: runs the checker weekly and on demand. |

## Publishing on GitHub Pages

1. Create a repository (for example `elsewhere-tv`) and upload every file, keeping the folders.
2. Settings → Pages → Source: *Deploy from a branch*, branch `main`, folder `/ (root)`.
3. The site appears at `https://<your-user>.github.io/elsewhere-tv/`.

`index.html` and `channels.json` must sit side by side. Opening `index.html` directly from your computer will not load the guide; it needs to be served over http(s).

## How streams stay current

YouTube live streams change their video ID whenever a broadcaster restarts a stream. The page handles this in three layers:

1. **Breaking Wall feed.** At load, the page reads `https://nickcarbone.github.io/breaking-wall/news_sources.json`. Channels with a `breakingWallKey` take their current link from it, matched on the feed's stable `key` (never on name or channel ID alone). If the feed is unreachable the page uses the links saved in `channels.json` and says so in the footer.
2. **Channel embeds.** Channels marked `"embed": "channel"` ask YouTube for the channel's current live broadcast, so a rotated video ID does not matter.
3. **Fallback chain.** If an embed errors, the page tries the other embed method, then shows a card with links to YouTube and the broadcaster's site. It never leaves an empty player.

## The checker

```
python3 scripts/check_channels.py          # report only
python3 scripts/check_channels.py --write  # update channels.json
```

It needs no API key. YouTube sometimes refuses or walls cloud networks (including GitHub's runners). If more than 40% of lookups fail, or more than 60% of channels come back off air, the script assumes it is being blocked and writes nothing. Running it from your own computer is the most reliable option.

To run the workflow by hand: Actions → *Check channels* → *Run workflow*.

## Channel record fields

| Field | Meaning |
|---|---|
| `id` | Stable identifier, also used in the page URL (`#telefe`). |
| `name`, `country`, `countryCode`, `city`, `region`, `timezone` | Where and what. `timezone` is an IANA name and drives the local clock. |
| `language` | Broadcast language as heard on screen. |
| `genre` | One of `news`, `business`, `general`, `entertainment`, `breakfast`, `talk`, `culture`, `local`, `weather`, `shopping`. Anything other than news and business appears under *Beyond the headlines*. |
| `category` | Short human description shown in the guide. |
| `service` | `domestic` or `international`. Domestic channels list first; *Own-language only* hides international ones. |
| `broadcaster`, `broadcasterType`, `commercial` | Ownership. `commercial` drives the *Commercial television* dial. |
| `channelId`, `videoId`, `embed` | YouTube channel ID, last known live video ID, and embed mode: `video`, `channel` or `external`. |
| `breakingWallKey` | Key of the matching entry in the Breaking Wall feed, or `null`. |
| `youtubeUrl`, `officialUrl` | Fallback links. |
| `status` | `verified-live` (live and playable when checked), `off-air-at-check` (genuine source, not broadcasting at that moment), `external-unconfirmed` (broadcaster's own player; page responded, stream not tested). |
| `embedding` | `confirmed`, `blocked`, `unknown` or `not applicable`. |
| `geoRestriction` | `unknown` throughout: checks ran from one location only. |
| `ads` | `unconfirmed` for commercial channels: many broadcasters replace ad breaks with a holding slate on YouTube. |
| `availabilityNote` | Shown in the channel panel when a channel only streams at certain times. |
| `lastVerified` | Date of the last check. |
| `description`, `notice` | Editorial context: what the channel is, and what to look out for. |

### Adding a channel

Copy an existing record, give it a new `id`, and fill in the fields. To find a channel ID, open the channel on YouTube, view the page source and search for `"externalId"`. If you are unsure whether a stream is permanent, use `"embed": "channel"`.

## What the page does not do

- It does not autoplay. Nothing loads until you press *Switch on* or change channel, and streams start muted unless *Sound* is on.
- It does not bypass geoblocking, sign-ins or embedding restrictions. Blocked channels open on the broadcaster's own page.
- "Likely on now" is a guess from the local hour and channel type, not a programme listing.
