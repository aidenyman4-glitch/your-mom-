# 67 Jumpscare

A Chrome extension. Type `67` anywhere — any input, any textarea, any page — and
the 67 kid comes screaming out of the screen at you.

Runs entirely offline. No network requests, no analytics, no remote assets: the
face is inline SVG and the scream is synthesized with the Web Audio API at the
moment it fires.

## Install

1. Clone or download this repo.
2. Open `chrome://extensions` and switch on **Developer mode** (top right).
3. Click **Load unpacked** and pick the **`extension/`** folder (not the repo root).
4. Go to any website, click in a text box, and type `67`.

Works in any Chromium browser with Manifest V3 — Chrome, Edge, Brave, Opera.

## What sets it off

The extension watches your keystrokes and fires the moment the last two
characters you typed are `6` then `7`. So `67` does it, and so does `route 67`
or `level 67`.

With **loose match** on (the default), separators between the digits are
ignored, so `6-7` and `6 7` count too. Worth knowing: this makes it eager on
purpose — `666 777` ends in `6`, space, `7`, so it fires. Turn loose match off
in the popup if you want only a literal `67`.

Things that never set it off:

- Password fields, while **spare password fields** is on (the default).
- Any hostname in your blocklist.
- Anything typed while the extension is switched off.
- Shortcuts — keys held with Ctrl, Cmd, or Alt are ignored.

Keystrokes are only ever observed, never swallowed: whatever you typed still
lands in the page as normal.

## Settings

Click the toolbar icon:

| Setting | What it does | Default |
| --- | --- | --- |
| Master switch | Arms or disarms the whole thing | on |
| Volume | How loud the scream is (0 mutes it) | 70% |
| Duration | How long the overlay stays up | 2.2s |
| Cooldown | Minimum gap between scares, so it can't spam you | 1.5s |
| Scream | Sound on or off, independent of volume | on |
| Loose match | Count `6-7` and `6 7` as well | on |
| Spare password fields | Never fire while typing a password | on |
| Never scare me on | One hostname per line; subdomains included | empty |

Changes apply immediately to tabs that are already open — no reload needed.
**Test it on this tab** fires a scare on demand without touching your counter.

Dismiss a scare early by clicking it or pressing <kbd>Esc</kbd>; otherwise it
clears itself when the duration runs out.

## Where things live

```
extension/
  manifest.json          Manifest V3
  content/scare.js       keystroke detection, overlay, synthesized scream
  popup/                 settings UI (popup.html / .css / .js)
  assets/icon.svg        icon source; the PNGs are generated from it
tests/e2e.js             end-to-end suite, drives a real Chromium
tools/make-icons.sh      regenerates the PNG icons from icon.svg
```

The overlay lives in a **closed shadow root** on a `position: fixed` host at the
maximum z-index, so page CSS can't restyle or hide it and page scripts can't
reach into it. Settings live in `chrome.storage.sync`, which is also how the
popup and the content scripts stay in step.

The extension declares `<all_urls>` because "type 67 anywhere" means it has to
watch every page; the `host_permissions` entry is what lets the popup's test
button reach the current tab.

## Working on it

Edit the artwork in the `FACE_SVG` string in `extension/content/scare.js`, or
the scream in the `scream()` function just above it. Reload the extension from
`chrome://extensions` to pick up changes.

Icons, after editing `extension/assets/icon.svg`:

```bash
./tools/make-icons.sh      # needs ImageMagick, plus rsvg-convert or Chromium
```

Tests — loads the real unpacked extension, types at it, and checks what happens
(trigger cases, the ones that must stay silent, cooldown, overlay geometry, and
the popup's settings taking effect live):

```bash
node tests/e2e.js          # needs Playwright on NODE_PATH
```
