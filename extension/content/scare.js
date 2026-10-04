/* 67 Jumpscare - content script.
 * Watches what you type. The moment "67" lands, the 67 kid lands with it.
 * Everything is local: no network, no page-script injection, no data leaves the browser.
 */
(() => {
  "use strict";

  // Don't double-inject if the extension reloads over a live page.
  if (window.__sixtySevenJumpscareLoaded) return;
  window.__sixtySevenJumpscareLoaded = true;

  const DEFAULTS = {
    enabled: true,
    volume: 0.7,
    sound: true,
    durationMs: 2200,
    cooldownMs: 1500,
    looseMatch: true,     // "6-7" and "6 7" count too
    skipPassword: true,   // never fire while typing in a password field
    blocklist: [],        // hostnames that are left alone
    scareCount: 0
  };

  let cfg = { ...DEFAULTS };
  let scaring = false;
  let lastScare = 0;
  let buffer = "";
  let bufferTouched = 0;

  const BUFFER_IDLE_MS = 4000; // stale keystrokes stop counting toward a match
  const BUFFER_MAX = 12;

  /* ---------------------------------------------------------------- config */

  function loadConfig() {
    try {
      chrome.storage.sync.get(DEFAULTS, (stored) => {
        if (chrome.runtime.lastError) return;
        cfg = { ...DEFAULTS, ...stored };
      });
    } catch (_) {
      /* storage unavailable (e.g. torn-down context) - defaults are fine */
    }
  }

  loadConfig();

  try {
    chrome.storage.onChanged.addListener((changes, area) => {
      if (area !== "sync") return;
      for (const [key, { newValue }] of Object.entries(changes)) {
        if (key in DEFAULTS && newValue !== undefined) cfg[key] = newValue;
      }
    });
  } catch (_) {}

  // The popup's "Test it" button talks to us through here.
  try {
    chrome.runtime.onMessage.addListener((msg, _sender, respond) => {
      if (msg && msg.type === "SIXTY_SEVEN_TEST") {
        trigger(true);
        respond && respond({ ok: true });
      }
      return false;
    });
  } catch (_) {}

  /* --------------------------------------------------------------- helpers */

  function siteBlocked() {
    const host = location.hostname.toLowerCase();
    if (!host) return false;
    return (cfg.blocklist || []).some((raw) => {
      const entry = String(raw).trim().toLowerCase().replace(/^\*\./, "");
      if (!entry) return false;
      return host === entry || host.endsWith("." + entry);
    });
  }

  function inPasswordField(target) {
    return !!(
      target &&
      target.tagName === "INPUT" &&
      String(target.type).toLowerCase() === "password"
    );
  }

  /* -------------------------------------------------------------- detector */

  function onKeyDown(event) {
    if (!cfg.enabled || scaring) return;
    if (event.ctrlKey || event.metaKey || event.altKey) return;
    if (cfg.skipPassword && inPasswordField(event.target)) return;

    const key = event.key;
    if (typeof key !== "string") return;

    const now = Date.now();
    if (now - bufferTouched > BUFFER_IDLE_MS) buffer = "";
    bufferTouched = now;

    if (key.length === 1) {
      buffer = (buffer + key).slice(-BUFFER_MAX);
    } else if (key === "Backspace") {
      buffer = buffer.slice(0, -1);
      return;
    } else {
      // Enter, Tab, arrows... you've moved on; start a fresh count.
      buffer = "";
      return;
    }

    const candidate = cfg.looseMatch ? buffer.replace(/[\s\-_.]/g, "") : buffer;
    if (candidate.endsWith("67")) {
      buffer = "";
      trigger(false);
    }
  }

  // Capture phase so we see the key even if the page stops propagation.
  addEventListener("keydown", onKeyDown, true);

  /* ------------------------------------------------------------------ audio */

  let audioCtx = null;

  function scream() {
    if (!cfg.sound) return;
    const Ctx = window.AudioContext || window.webkitAudioContext;
    if (!Ctx) return;

    try {
      if (!audioCtx || audioCtx.state === "closed") audioCtx = new Ctx();
      if (audioCtx.state === "suspended") audioCtx.resume();
    } catch (_) {
      return;
    }

    const ctx = audioCtx;
    const t0 = ctx.currentTime;
    const dur = Math.max(0.6, Math.min(cfg.durationMs / 1000, 4));
    const vol = Math.max(0, Math.min(Number(cfg.volume), 1));
    if (vol === 0) return;

    const master = ctx.createGain();
    master.gain.setValueAtTime(0.0001, t0);
    master.gain.exponentialRampToValueAtTime(vol, t0 + 0.02);
    master.gain.setValueAtTime(vol, t0 + dur * 0.6);
    master.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);

    // A little clipping keeps it nasty instead of synthy.
    const shaper = ctx.createWaveShaper();
    const curve = new Float32Array(1024);
    for (let i = 0; i < curve.length; i++) {
      const x = (i / (curve.length - 1)) * 2 - 1;
      curve[i] = Math.tanh(x * 4);
    }
    shaper.curve = curve;
    shaper.oversample = "4x";

    shaper.connect(master);
    master.connect(ctx.destination);

    // 1. The shriek: two detuned saws sweeping up, wobbled by vibrato.
    const vibrato = ctx.createOscillator();
    const vibratoDepth = ctx.createGain();
    vibrato.frequency.setValueAtTime(11, t0);
    vibratoDepth.gain.setValueAtTime(70, t0);
    vibrato.connect(vibratoDepth);

    [0, 7].forEach((detune, i) => {
      const osc = ctx.createOscillator();
      osc.type = "sawtooth";
      osc.detune.setValueAtTime(detune * 14, t0);
      osc.frequency.setValueAtTime(320, t0);
      osc.frequency.exponentialRampToValueAtTime(1500, t0 + 0.18);
      osc.frequency.exponentialRampToValueAtTime(860, t0 + dur * 0.75);

      const gain = ctx.createGain();
      gain.gain.setValueAtTime(i === 0 ? 0.5 : 0.3, t0);
      gain.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);

      vibratoDepth.connect(osc.frequency);
      osc.connect(gain);
      gain.connect(shaper);
      osc.start(t0);
      osc.stop(t0 + dur);
    });

    vibrato.start(t0);
    vibrato.stop(t0 + dur);

    // 2. Static burst - the "camera glitch" layer.
    const noiseLen = Math.ceil(ctx.sampleRate * dur);
    const noiseBuf = ctx.createBuffer(1, noiseLen, ctx.sampleRate);
    const data = noiseBuf.getChannelData(0);
    for (let i = 0; i < noiseLen; i++) data[i] = Math.random() * 2 - 1;

    const noise = ctx.createBufferSource();
    noise.buffer = noiseBuf;

    const noiseFilter = ctx.createBiquadFilter();
    noiseFilter.type = "bandpass";
    noiseFilter.Q.setValueAtTime(1.2, t0);
    noiseFilter.frequency.setValueAtTime(5000, t0);
    noiseFilter.frequency.exponentialRampToValueAtTime(700, t0 + dur * 0.8);

    const noiseGain = ctx.createGain();
    noiseGain.gain.setValueAtTime(0.55, t0);
    noiseGain.gain.exponentialRampToValueAtTime(0.0001, t0 + dur * 0.7);

    noise.connect(noiseFilter);
    noiseFilter.connect(noiseGain);
    noiseGain.connect(shaper);
    noise.start(t0);
    noise.stop(t0 + dur);

    // 3. Sub-bass thud so it hits in the chest, not just the ears.
    const boom = ctx.createOscillator();
    boom.type = "sine";
    boom.frequency.setValueAtTime(120, t0);
    boom.frequency.exponentialRampToValueAtTime(32, t0 + 0.55);

    const boomGain = ctx.createGain();
    boomGain.gain.setValueAtTime(0.9, t0);
    boomGain.gain.exponentialRampToValueAtTime(0.0001, t0 + 0.9);

    boom.connect(boomGain);
    boomGain.connect(master);
    boom.start(t0);
    boom.stop(t0 + 0.95);
  }

  /* ------------------------------------------------------------------ face */

  const FACE_SVG = `
<svg viewBox="0 0 400 400" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <defs>
    <radialGradient id="sj-skin" cx="50%" cy="38%" r="68%">
      <stop offset="0%" stop-color="#f2d9c0"/>
      <stop offset="62%" stop-color="#c89a76"/>
      <stop offset="100%" stop-color="#4a2a22"/>
    </radialGradient>
    <radialGradient id="sj-eye" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#fff"/>
      <stop offset="70%" stop-color="#ffe9e0"/>
      <stop offset="100%" stop-color="#b08c80"/>
    </radialGradient>
    <filter id="sj-glow" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="6" result="b"/>
      <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
  </defs>

  <!-- hoodie -->
  <path d="M40 400 q10-120 160-128 q150 8 160 128 z" fill="#1b1b22"/>
  <path d="M96 400 q14-74 104-80 q90 6 104 80 z" fill="#0e0e13"/>

  <!-- head -->
  <ellipse cx="200" cy="186" rx="124" ry="140" fill="url(#sj-skin)"/>

  <!-- hair -->
  <path d="M76 168 q6-112 124-116 q118 4 124 116 q-26-54-62-62 q10 26-14 40
           q-18-30-50-30 q-30 0-44 26 q-16-18-12-40 q-44 16-66 66 z" fill="#15100e"/>

  <!-- brows, driven low and angry -->
  <path d="M104 120 q46 14 76 34" stroke="#15100e" stroke-width="15" stroke-linecap="round" fill="none"/>
  <path d="M296 120 q-46 14-76 34" stroke="#15100e" stroke-width="15" stroke-linecap="round" fill="none"/>

  <!-- eyes -->
  <ellipse cx="140" cy="178" rx="52" ry="48" fill="#2b1410" opacity=".85"/>
  <ellipse cx="260" cy="178" rx="52" ry="48" fill="#2b1410" opacity=".85"/>
  <g filter="url(#sj-glow)">
    <ellipse cx="140" cy="176" rx="44" ry="40" fill="url(#sj-eye)"/>
    <ellipse cx="260" cy="176" rx="44" ry="40" fill="url(#sj-eye)"/>
    <circle class="sj-pupil" cx="140" cy="178" r="19" fill="#07070a"/>
    <circle class="sj-pupil" cx="260" cy="178" r="19" fill="#07070a"/>
    <circle cx="133" cy="170" r="6" fill="#fff" opacity=".92"/>
    <circle cx="253" cy="170" r="6" fill="#fff" opacity=".92"/>
  </g>

  <!-- veins -->
  <path d="M106 150 q16 12 10 30 M174 150 q-16 12-10 30" stroke="#a8201a"
        stroke-width="3" fill="none" opacity=".75"/>
  <path d="M226 150 q16 12 10 30 M294 150 q-16 12-10 30" stroke="#a8201a"
        stroke-width="3" fill="none" opacity=".75"/>

  <!-- grin -->
  <path d="M112 246 q88 104 176 0 q-88 40-176 0 z" fill="#2a0708"/>
  <path d="M112 246 q88 34 176 0 q-88 22-176 0 z" fill="#f6f2ea"/>
  <path d="M150 258 l10 26 l10-26 z M190 262 l10 30 l10-30 z M230 258 l10 26 l10-26 z"
        fill="#f6f2ea"/>
  <path d="M196 290 q8 30 -2 54" stroke="#7d0f12" stroke-width="7"
        stroke-linecap="round" fill="none" opacity=".85"/>

  <!-- the number, stitched on the hoodie -->
  <text class="sj-number" x="112" y="372" text-anchor="middle"
        font-family="Impact, 'Arial Black', sans-serif" font-size="38"
        fill="#ff3a3a" stroke="#1a0000" stroke-width="2.5"
        paint-order="stroke">67</text>
</svg>`;

  /* --------------------------------------------------------------- overlay */

  const CSS = `
:host { all: initial; }
.sj-root {
  position: fixed;
  inset: 0;
  z-index: 2147483647;
  display: grid;
  place-items: center;
  overflow: hidden;
  background: #000;
  cursor: pointer;
  contain: strict;
  animation: sj-flash var(--sj-dur) steps(1) both;
}
.sj-static {
  position: absolute;
  inset: -20%;
  opacity: .35;
  mix-blend-mode: screen;
  pointer-events: none;
  background-image:
    repeating-linear-gradient(0deg, rgba(255,255,255,.18) 0 1px, transparent 1px 3px),
    repeating-linear-gradient(90deg, rgba(255,0,0,.12) 0 2px, transparent 2px 5px);
  animation: sj-static-shift .07s steps(2) infinite;
}
.sj-face {
  position: relative;
  width: min(74vmin, 88vw);
  height: min(74vmin, 72vh);
  margin-bottom: 9vh;
  filter: drop-shadow(0 0 48px rgba(255, 0, 0, .75)) contrast(1.25) saturate(1.1);
  transform-origin: center;
  animation:
    sj-rush .34s cubic-bezier(.17, .89, .32, 1.28) both,
    sj-shake .055s steps(2) infinite .34s;
}
.sj-face svg { width: 100%; height: 100%; display: block; }
.sj-pupil { animation: sj-dart .11s steps(2) infinite; }
.sj-number { animation: sj-numflick .19s steps(2) infinite; }
.sj-caption {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 6vh;
  text-align: center;
  font: 900 clamp(34px, 11vw, 150px)/1 Impact, "Arial Black", sans-serif;
  letter-spacing: .06em;
  color: #fff;
  text-shadow: 0 0 18px #f00, 4px 4px 0 #8a0000, 0 0 60px #f00;
  animation: sj-numflick .13s steps(2) infinite;
  pointer-events: none;
}
.sj-hint {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 1.6vh;
  text-align: center;
  font: 600 13px/1.4 system-ui, sans-serif;
  color: rgba(255,255,255,.5);
  pointer-events: none;
}
@keyframes sj-rush {
  from { transform: scale(.04) rotate(-9deg); opacity: 0; }
  70%  { transform: scale(1.14) rotate(2deg); opacity: 1; }
  to   { transform: scale(1) rotate(0deg); opacity: 1; }
}
@keyframes sj-shake {
  0%   { transform: translate3d(-13px, 7px, 0) rotate(-2.2deg) scale(1.02); }
  25%  { transform: translate3d(11px, -9px, 0) rotate(2deg) scale(1); }
  50%  { transform: translate3d(-8px, -6px, 0) rotate(-1.4deg) scale(1.03); }
  75%  { transform: translate3d(9px, 10px, 0) rotate(1.7deg) scale(1); }
  100% { transform: translate3d(-12px, 5px, 0) rotate(-2deg) scale(1.02); }
}
@keyframes sj-flash {
  0%, 6%   { background: #fff; }
  7%, 13%  { background: #000; }
  14%, 18% { background: #6b0000; }
  19%      { background: #000; }
  100%     { background: #000; }
}
@keyframes sj-static-shift {
  0%   { transform: translate3d(0, 0, 0); }
  50%  { transform: translate3d(-2%, 1.5%, 0); }
  100% { transform: translate3d(1.5%, -2%, 0); }
}
@keyframes sj-dart {
  0%   { transform: translate(0, 0); }
  50%  { transform: translate(5px, -3px); }
  100% { transform: translate(-4px, 2px); }
}
@keyframes sj-numflick {
  0%   { opacity: 1; }
  50%  { opacity: .34; }
  100% { opacity: 1; }
}`;

  function trigger(isTest) {
    if (!cfg.enabled && !isTest) return;
    if (scaring) return;
    if (siteBlocked() && !isTest) return;

    const now = Date.now();
    if (!isTest && now - lastScare < Math.max(0, Number(cfg.cooldownMs) || 0)) return;
    lastScare = now;
    scaring = true;

    const duration = Math.max(600, Math.min(Number(cfg.durationMs) || 2200, 8000));

    const host = document.createElement("div");
    host.setAttribute("data-sixty-seven-jumpscare", "");
    // Belt and braces: the page's own CSS must not be able to hide the host.
    host.style.cssText =
      "all:initial;position:fixed!important;inset:0!important;" +
      "z-index:2147483647!important;display:block!important;" +
      "opacity:1!important;visibility:visible!important;pointer-events:auto!important;";

    const shadow = host.attachShadow({ mode: "closed" });
    const style = document.createElement("style");
    style.textContent = CSS;

    const root = document.createElement("div");
    root.className = "sj-root";
    root.style.setProperty("--sj-dur", duration + "ms");
    root.innerHTML =
      '<div class="sj-static"></div>' +
      '<div class="sj-face">' + FACE_SVG + "</div>" +
      '<div class="sj-caption">6&nbsp;7</div>' +
      '<div class="sj-hint">click or press Esc to dismiss</div>';

    shadow.append(style, root);
    (document.body || document.documentElement).appendChild(host);

    scream();

    let done = false;
    const cleanup = () => {
      if (done) return;
      done = true;
      clearTimeout(timer);
      removeEventListener("keydown", onEscape, true);
      host.remove();
      // Short grace period: don't let the keystroke that dismissed it re-fire.
      setTimeout(() => { scaring = false; }, 250);
    };

    const onEscape = (e) => {
      if (e.key === "Escape") {
        e.preventDefault();
        e.stopPropagation();
        cleanup();
      }
    };

    root.addEventListener("click", cleanup);
    addEventListener("keydown", onEscape, true);
    const timer = setTimeout(cleanup, duration);

    if (!isTest) bumpCount();
  }

  function bumpCount() {
    try {
      chrome.storage.sync.get({ scareCount: 0 }, (res) => {
        if (chrome.runtime.lastError) return;
        chrome.storage.sync.set({ scareCount: (Number(res.scareCount) || 0) + 1 });
      });
    } catch (_) {}
  }
})();
