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
    volume: 0.8,
    sound: true,
    durationMs: 2600,
    cooldownMs: 1500,
    intensity: "nightmare", // mild | normal | nightmare
    looseMatch: true,       // "6-7" and "6 7" count too
    skipPassword: true,     // never fire while typing in a password field
    blocklist: [],          // hostnames that are left alone
    scareCount: 0
  };

  // How mean each intensity is. dread = the silent beat before the hit.
  const INTENSITY = {
    mild:      { dread: 0,   strobe: false, glitch: false, pageShake: false, hijackTitle: false },
    normal:    { dread: 350, strobe: true,  glitch: true,  pageShake: false, hijackTitle: false },
    nightmare: { dread: 600, strobe: true,  glitch: true,  pageShake: true,  hijackTitle: true }
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

  const profile = () => INTENSITY[cfg.intensity] || INTENSITY.nightmare;

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

  function audio(dreadMs) {
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
    const vol = Math.max(0, Math.min(Number(cfg.volume), 1));
    if (vol === 0) return;

    const t0 = ctx.currentTime;
    const hit = t0 + dreadMs / 1000;               // when the scream lands
    const dur = Math.max(0.6, Math.min(cfg.durationMs / 1000, 6));
    const end = hit + dur;

    const master = ctx.createGain();
    master.gain.setValueAtTime(vol, t0);
    master.gain.setValueAtTime(vol, end - 0.25);
    master.gain.exponentialRampToValueAtTime(0.0001, end);
    master.connect(ctx.destination);

    // Hard clipping is what makes it sound like a scream and not a synth.
    const crush = ctx.createWaveShaper();
    const curve = new Float32Array(2048);
    for (let i = 0; i < curve.length; i++) {
      const x = (i / (curve.length - 1)) * 2 - 1;
      curve[i] = Math.tanh(x * 7);
    }
    crush.curve = curve;
    crush.oversample = "4x";
    crush.connect(master);

    // A short feedback delay stands in for room reverb - it keeps the tail wet.
    const delay = ctx.createDelay(0.5);
    delay.delayTime.setValueAtTime(0.11, t0);
    const feedback = ctx.createGain();
    feedback.gain.setValueAtTime(0.34, t0);
    const wet = ctx.createGain();
    wet.gain.setValueAtTime(0.4, t0);
    crush.connect(delay);
    delay.connect(feedback);
    feedback.connect(delay);
    delay.connect(wet);
    wet.connect(master);

    const noiseBuffer = (seconds) => {
      const len = Math.max(1, Math.ceil(ctx.sampleRate * seconds));
      const buf = ctx.createBuffer(1, len, ctx.sampleRate);
      const data = buf.getChannelData(0);
      for (let i = 0; i < len; i++) data[i] = Math.random() * 2 - 1;
      return buf;
    };

    // --- the dread: a slow shuddering inhale while the screen is still black
    if (dreadMs > 120) {
      const breath = ctx.createBufferSource();
      breath.buffer = noiseBuffer(dreadMs / 1000);

      const breathFilter = ctx.createBiquadFilter();
      breathFilter.type = "bandpass";
      breathFilter.Q.setValueAtTime(5, t0);
      breathFilter.frequency.setValueAtTime(320, t0);
      breathFilter.frequency.exponentialRampToValueAtTime(1300, hit);

      const breathGain = ctx.createGain();
      breathGain.gain.setValueAtTime(0.0001, t0);
      breathGain.gain.exponentialRampToValueAtTime(0.32 * vol, hit - 0.03);
      breathGain.gain.exponentialRampToValueAtTime(0.0001, hit);

      breath.connect(breathFilter);
      breathFilter.connect(breathGain);
      breathGain.connect(master);
      breath.start(t0);
      breath.stop(hit);
    }

    // --- the impact transient: the crack that makes you flinch
    const smack = ctx.createBufferSource();
    smack.buffer = noiseBuffer(0.14);
    const smackFilter = ctx.createBiquadFilter();
    smackFilter.type = "highpass";
    smackFilter.frequency.setValueAtTime(1200, hit);
    const smackGain = ctx.createGain();
    smackGain.gain.setValueAtTime(1, hit);
    smackGain.gain.exponentialRampToValueAtTime(0.0001, hit + 0.14);
    smack.connect(smackFilter);
    smackFilter.connect(smackGain);
    smackGain.connect(crush);
    smack.start(hit);
    smack.stop(hit + 0.15);

    // --- the shriek: a dissonant cluster, not a clean tone.
    // Minor-second and tritone ratios are what make it feel wrong.
    const vibrato = ctx.createOscillator();
    const vibratoDepth = ctx.createGain();
    vibrato.frequency.setValueAtTime(13, hit);
    vibrato.frequency.linearRampToValueAtTime(23, end);
    vibratoDepth.gain.setValueAtTime(95, hit);
    vibrato.connect(vibratoDepth);
    vibrato.start(hit);
    vibrato.stop(end);

    [
      { ratio: 1,     type: "sawtooth", gain: 0.5 },
      { ratio: 1.059, type: "sawtooth", gain: 0.34 }, // minor 2nd against the root
      { ratio: 1.414, type: "square",   gain: 0.2 },  // tritone
      { ratio: 2.03,  type: "sawtooth", gain: 0.16 }  // detuned octave
    ].forEach(({ ratio, type, gain }) => {
      const osc = ctx.createOscillator();
      osc.type = type;
      osc.frequency.setValueAtTime(300 * ratio, hit);
      osc.frequency.exponentialRampToValueAtTime(1650 * ratio, hit + 0.16);
      osc.frequency.exponentialRampToValueAtTime(900 * ratio, hit + dur * 0.55);
      osc.frequency.exponentialRampToValueAtTime(420 * ratio, end);

      const g = ctx.createGain();
      g.gain.setValueAtTime(gain, hit);
      g.gain.exponentialRampToValueAtTime(0.0001, end);

      vibratoDepth.connect(osc.frequency);
      osc.connect(g);
      g.connect(crush);
      osc.start(hit);
      osc.stop(end);
    });

    // --- static burst, the "the signal broke" layer
    const noise = ctx.createBufferSource();
    noise.buffer = noiseBuffer(dur);
    const noiseFilter = ctx.createBiquadFilter();
    noiseFilter.type = "bandpass";
    noiseFilter.Q.setValueAtTime(1.1, hit);
    noiseFilter.frequency.setValueAtTime(6000, hit);
    noiseFilter.frequency.exponentialRampToValueAtTime(600, hit + dur * 0.8);
    const noiseGain = ctx.createGain();
    noiseGain.gain.setValueAtTime(0.6, hit);
    noiseGain.gain.exponentialRampToValueAtTime(0.0001, hit + dur * 0.75);
    noise.connect(noiseFilter);
    noiseFilter.connect(noiseGain);
    noiseGain.connect(crush);
    noise.start(hit);
    noise.stop(end);

    // --- sub drop, so it hits in the chest and not just the ears
    const boom = ctx.createOscillator();
    boom.type = "sine";
    boom.frequency.setValueAtTime(150, hit);
    boom.frequency.exponentialRampToValueAtTime(26, hit + 0.7);
    const boomGain = ctx.createGain();
    boomGain.gain.setValueAtTime(1, hit);
    boomGain.gain.exponentialRampToValueAtTime(0.0001, hit + 1.1);
    boom.connect(boomGain);
    boomGain.connect(master);
    boom.start(hit);
    boom.stop(hit + 1.15);
  }

  /* ------------------------------------------------------------------ faces */

  // Shared gradients/filters, defined once and referenced by both faces.
  const DEFS = `
  <defs>
    <radialGradient id="sj-skin" cx="50%" cy="34%" r="72%">
      <stop offset="0%" stop-color="#e9e0cb"/>
      <stop offset="40%" stop-color="#c3b296"/>
      <stop offset="72%" stop-color="#7d6652"/>
      <stop offset="100%" stop-color="#1d1411"/>
    </radialGradient>
    <radialGradient id="sj-sclera" cx="50%" cy="46%" r="52%">
      <stop offset="0%" stop-color="#fffdf8"/>
      <stop offset="62%" stop-color="#f3d9cf"/>
      <stop offset="100%" stop-color="#8e4a40"/>
    </radialGradient>
    <radialGradient id="sj-socket" cx="50%" cy="42%" r="60%">
      <stop offset="0%" stop-color="#2a0f0c"/>
      <stop offset="100%" stop-color="#0a0403"/>
    </radialGradient>
    <radialGradient id="sj-maw" cx="50%" cy="22%" r="86%">
      <stop offset="0%" stop-color="#4a0206"/>
      <stop offset="46%" stop-color="#1a0002"/>
      <stop offset="100%" stop-color="#000"/>
    </radialGradient>
    <filter id="sj-grain" x="0" y="0" width="100%" height="100%">
      <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="3" seed="67"/>
      <feColorMatrix type="saturate" values="0"/>
      <feComponentTransfer><feFuncA type="linear" slope="0.45"/></feComponentTransfer>
      <feComposite operator="in" in2="SourceGraphic"/>
    </filter>
    <filter id="sj-soft" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="7"/>
    </filter>
  </defs>`;

  // Face A - the stare. Sunken, bloodshot, grinning too wide.
  const FACE_A = `<svg viewBox="0 0 400 440" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  ${DEFS}
  <path d="M26 440 q14-130 174-140 q160 10 174 140 z" fill="#0b0b11"/>
  <path d="M92 440 q16-86 108-94 q92 8 108 94 z" fill="#050509"/>

  <ellipse cx="200" cy="196" rx="126" ry="150" fill="url(#sj-skin)"/>
  <ellipse cx="104" cy="240" rx="32" ry="54" fill="#2b1d17" opacity=".5" filter="url(#sj-soft)"/>
  <ellipse cx="296" cy="240" rx="32" ry="54" fill="#2b1d17" opacity=".5" filter="url(#sj-soft)"/>
  <ellipse cx="200" cy="196" rx="126" ry="150" fill="#fff" opacity=".22" filter="url(#sj-grain)"/>

  <!-- hair sits high so it frames the eyes instead of swallowing them -->
  <path d="M74 160 C74 58 126 22 200 22 C274 22 326 58 326 160 C310 114 286 90 258 82 C240 102 222 110 200 110 C178 110 160 102 142 82 C114 90 90 114 74 160 Z" fill="#0c0908"/>

  <ellipse cx="138" cy="186" rx="52" ry="46" fill="#1c0c09" opacity=".8" filter="url(#sj-soft)"/>
  <ellipse cx="262" cy="186" rx="52" ry="46" fill="#1c0c09" opacity=".8" filter="url(#sj-soft)"/>

  <path d="M92 132 q52 12 84 34" stroke="#0c0908" stroke-width="15" stroke-linecap="round" fill="none"/>
  <path d="M308 132 q-52 12-84 34" stroke="#0c0908" stroke-width="15" stroke-linecap="round" fill="none"/>

  <ellipse cx="138" cy="186" rx="45" ry="41" fill="url(#sj-sclera)"/>
  <ellipse cx="262" cy="186" rx="45" ry="41" fill="url(#sj-sclera)"/>
  <g stroke="#b01a14" stroke-width="2.2" fill="none" opacity=".85">
    <path d="M98 178 q24 6 32 10 M102 200 q26-2 36 2 M178 178 q-24 6-32 10 M174 202 q-24-2-34 2"/>
    <path d="M222 178 q24 6 32 10 M226 200 q26-2 36 2 M302 178 q-24 6-32 10 M298 202 q-24-2-34 2"/>
  </g>
  <!-- pin-prick pupils in too much white: that is the part that reads as wrong -->
  <circle class="sj-pupil" cx="138" cy="186" r="11" fill="#000"/>
  <circle class="sj-pupil" cx="262" cy="186" r="11" fill="#000"/>
  <circle cx="133" cy="179" r="4" fill="#fff" opacity=".95"/>
  <circle cx="257" cy="179" r="4" fill="#fff" opacity=".95"/>

  <path d="M134 224 q-6 42 2 70" stroke="#8d0f10" stroke-width="7" stroke-linecap="round" fill="none" opacity=".9"/>
  <path d="M268 224 q7 36-1 60" stroke="#8d0f10" stroke-width="6" stroke-linecap="round" fill="none" opacity=".85"/>

  <path d="M98 262 Q200 300 302 262 Q200 398 98 262 Z" fill="url(#sj-maw)"/>
  <path d="M107.2 265.3 L112.6 274.8 L118.0 268.7 Z M121.5 269.7 L128.2 283.9 L134.9 273.3 Z M135.7 273.5 L142.4 291.7 L149.1 276.3 Z M150.0 276.4 L156.2 303.0 L162.5 278.4 Z M164.3 278.7 L169.9 296.8 L175.5 279.9 Z M178.6 280.2 L184.1 299.2 L189.7 280.8 Z M192.9 280.9 L198.8 301.3 L204.7 281.0 Z M207.1 280.9 L212.6 303.2 L218.0 280.4 Z M221.4 280.2 L227.3 308.2 L233.2 279.0 Z M235.7 278.7 L241.0 301.0 L246.3 277.1 Z M250.0 276.4 L256.6 295.0 L263.3 273.7 Z M264.3 273.5 L269.8 283.1 L275.3 270.6 Z M278.5 269.7 L284.4 273.9 L290.2 266.1 Z M114.3 282.0 L121.6 279.3 L128.9 296.9 Z M129.9 297.9 L136.9 289.0 L143.9 309.4 Z M145.5 310.6 L152.8 298.7 L160.1 319.6 Z M161.1 320.1 L166.7 304.1 L172.4 325.0 Z M176.6 326.4 L183.0 302.7 L189.3 329.3 Z M192.2 329.6 L197.8 303.3 L203.4 329.9 Z M207.8 329.6 L214.0 312.1 L220.2 327.3 Z M223.4 326.4 L230.0 299.5 L236.7 321.2 Z M238.9 320.1 L245.6 296.2 L252.2 312.2 Z M254.5 310.6 L260.9 292.0 L267.2 300.4 Z M270.1 297.9 L275.8 280.4 L281.4 286.7 Z" fill="#ddd2b6"/>
  <path d="M98 262 Q200 300 302 262" stroke="#5e0a0c" stroke-width="5" fill="none" opacity=".75"/>
  <path d="M206 330 q10 46-4 78" stroke="#8d0f10" stroke-width="9" stroke-linecap="round" fill="none"/>

  <text class="sj-number" x="104" y="414" text-anchor="middle"
        font-family="Impact, 'Arial Black', sans-serif" font-size="40"
        fill="#ff2f2f" stroke="#140000" stroke-width="2.5" paint-order="stroke">67</text>
</svg>`;

  // Face B - the scream. Eyes gone, jaw unhinged. Flickers against A.
  const FACE_B = `<svg viewBox="0 0 400 440" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  ${DEFS}
  <path d="M26 440 q14-130 174-140 q160 10 174 140 z" fill="#0b0b11"/>
  <ellipse cx="200" cy="192" rx="128" ry="152" fill="url(#sj-skin)"/>
  <ellipse cx="200" cy="192" rx="128" ry="152" fill="#fff" opacity=".26" filter="url(#sj-grain)"/>

  <path d="M74 160 C74 58 126 22 200 22 C274 22 326 58 326 160 C310 114 286 90 258 82 C240 102 222 110 200 110 C178 110 160 102 142 82 C114 90 90 114 74 160 Z" fill="#0c0908"/>

  <!-- the eyes are gone -->
  <ellipse cx="136" cy="182" rx="44" ry="50" fill="#000"/>
  <ellipse cx="264" cy="182" rx="44" ry="50" fill="#000"/>
  <ellipse cx="136" cy="176" rx="30" ry="30" fill="#4a0707" opacity=".55" filter="url(#sj-soft)"/>
  <ellipse cx="264" cy="176" rx="30" ry="30" fill="#4a0707" opacity=".55" filter="url(#sj-soft)"/>
  <path d="M124 228 q-8 64 4 102 M148 230 q6 50-2 82" stroke="#7d0c0e" stroke-width="9"
        stroke-linecap="round" fill="none"/>
  <path d="M256 228 q-6 58 3 94 M280 230 q7 44-3 74" stroke="#7d0c0e" stroke-width="8"
        stroke-linecap="round" fill="none"/>

  <!-- jaw unhinged -->
  <ellipse cx="200" cy="302" rx="66" ry="82" fill="url(#sj-maw)"/>
  <path d="M265.8 309.0 L247.3 310.9 L264.5 319.4 Z M261.3 332.5 L249.1 331.4 L257.4 342.5 Z M252.0 352.6 L237.3 345.0 L244.5 362.6 Z M237.5 369.5 L222.2 349.9 L228.3 376.1 Z M220.6 379.9 L211.6 365.2 L208.7 383.3 Z M200.8 384.0 L195.8 371.0 L189.4 382.9 Z M180.5 380.3 L179.9 365.6 L171.4 375.9 Z M162.1 369.1 L168.3 351.4 L155.8 362.9 Z M138.9 333.0 L149.1 321.5 L135.5 319.1 Z M134.2 308.7 L153.9 302.0 L134.2 295.3 Z M135.4 285.5 L150.9 283.2 L139.1 270.4 Z M142.2 262.3 L163.5 271.1 L149.2 249.7 Z M154.2 243.0 L167.8 251.8 L163.9 233.4 Z M190.6 220.8 L196.1 237.0 L199.5 220.0 Z M210.4 221.0 L212.5 234.1 L218.9 223.5 Z M228.0 227.7 L226.7 244.6 L237.8 234.8 Z M256.6 259.9 L244.9 275.1 L261.8 273.2 Z M264.5 284.5 L255.5 291.6 L265.8 295.1 Z" fill="#d6cab0"/>
  <ellipse cx="200" cy="302" rx="66" ry="82" fill="none" stroke="#4a0608" stroke-width="5" opacity=".6"/>

  <text class="sj-number" x="104" y="420" text-anchor="middle"
        font-family="Impact, 'Arial Black', sans-serif" font-size="40"
        fill="#ff2f2f" stroke="#140000" stroke-width="2.5" paint-order="stroke">67</text>
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
}
.sj-root.sj-strobe {
  animation: sj-flash var(--sj-dur) steps(1) var(--sj-dread) forwards;
}

/* the creeping shape during the silent beat before the hit */
.sj-dread {
  position: absolute;
  width: 46vmin;
  height: 46vmin;
  opacity: 0;
  filter: blur(7px) brightness(.22);
  animation: sj-creep var(--sj-dread) ease-in forwards;
}
.sj-dread svg { width: 100%; height: 100%; display: block; }

.sj-stage {
  position: relative;
  width: min(78vmin, 92vw);
  height: min(78vmin, 76vh);
  margin-bottom: 8vh;
  transform-origin: center;
  animation:
    sj-rush .26s cubic-bezier(.16, .9, .3, 1.35) var(--sj-dread) both,
    sj-shake .048s steps(2) infinite var(--sj-hit);
  /* cheap chromatic split - the red/cyan fringe sells the "broken feed" look */
  filter:
    drop-shadow(-7px 0 0 rgba(255, 0, 0, .55))
    drop-shadow(7px 0 0 rgba(0, 240, 255, .32))
    drop-shadow(0 0 54px rgba(255, 0, 0, .8))
    contrast(1.3) saturate(1.15);
}
.sj-stage svg { position: absolute; inset: 0; width: 100%; height: 100%; display: block; }

/* face B cuts in over face A - duplicated keyframes give a hard flicker */
.sj-b { opacity: 0; animation: sj-swap .118s linear infinite var(--sj-hit); }

/* a torn copy that slides in horizontal bands */
.sj-ghost {
  mix-blend-mode: screen;
  opacity: 0;
  filter: hue-rotate(-25deg) saturate(2.6) brightness(1.3);
}
.sj-root.sj-glitch .sj-ghost {
  animation: sj-tear .085s steps(1) infinite var(--sj-hit);
}

.sj-pupil { animation: sj-dart .1s steps(2) infinite; }
.sj-number { animation: sj-numflick .17s steps(2) infinite; }

.sj-scan {
  position: absolute;
  inset: -20%;
  opacity: .4;
  mix-blend-mode: screen;
  pointer-events: none;
  background-image:
    repeating-linear-gradient(0deg, rgba(255,255,255,.2) 0 1px, transparent 1px 3px),
    repeating-linear-gradient(90deg, rgba(255,0,0,.14) 0 2px, transparent 2px 5px);
  animation: sj-static-shift .06s steps(2) infinite;
}
.sj-vignette {
  position: absolute;
  inset: 0;
  pointer-events: none;
  background: radial-gradient(ellipse at center, transparent 36%, rgba(0,0,0,.92) 100%);
}
.sj-caption {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 5vh;
  text-align: center;
  font: 900 clamp(34px, 12vw, 165px)/1 Impact, "Arial Black", sans-serif;
  letter-spacing: .06em;
  color: #fff;
  opacity: 0;
  text-shadow: 0 0 20px #f00, 5px 5px 0 #6d0000, 0 0 70px #f00;
  animation:
    sj-appear .01s linear var(--sj-hit) forwards,
    sj-numflick .12s steps(2) infinite var(--sj-hit);
  pointer-events: none;
}
.sj-hint {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 1.4vh;
  text-align: center;
  font: 600 13px/1.4 system-ui, sans-serif;
  color: rgba(255,255,255,.45);
  opacity: 0;
  animation: sj-appear .01s linear calc(var(--sj-hit) + .9s) forwards;
  pointer-events: none;
}

@keyframes sj-creep {
  0%   { opacity: 0;    transform: scale(.5); }
  70%  { opacity: .16;  transform: scale(.92); }
  100% { opacity: .30;  transform: scale(1.12); }
}
@keyframes sj-appear { to { opacity: 1; } }
@keyframes sj-rush {
  from { transform: scale(.03) rotate(-11deg); opacity: 0; }
  68%  { transform: scale(1.2) rotate(2.5deg); opacity: 1; }
  to   { transform: scale(1) rotate(0deg); opacity: 1; }
}
@keyframes sj-shake {
  0%   { transform: translate3d(-17px, 9px, 0) rotate(-2.8deg) scale(1.03); }
  20%  { transform: translate3d(14px, -12px, 0) rotate(2.4deg) scale(1); }
  40%  { transform: translate3d(-10px, -8px, 0) rotate(-1.7deg) scale(1.05); }
  60%  { transform: translate3d(13px, 13px, 0) rotate(2.1deg) scale(1); }
  80%  { transform: translate3d(-15px, 4px, 0) rotate(-2.4deg) scale(1.04); }
  100% { transform: translate3d(16px, -6px, 0) rotate(1.9deg) scale(1.01); }
}
@keyframes sj-swap {
  0%, 57%   { opacity: 0; }
  58%, 100% { opacity: 1; }
}
@keyframes sj-tear {
  0%   { clip-path: inset(10% 0 72% 0); transform: translate(-17px, 0); opacity: .9; }
  16%  { clip-path: inset(41% 0 36% 0); transform: translate(19px, 0);  opacity: .75; }
  32%  { clip-path: inset(68% 0 10% 0); transform: translate(-12px, 0); opacity: .95; }
  48%  { opacity: 0; }
  64%  { clip-path: inset(24% 0 58% 0); transform: translate(14px, 0);  opacity: .7; }
  80%  { clip-path: inset(55% 0 24% 0); transform: translate(-16px, 0); opacity: .85; }
  100% { opacity: 0; }
}
@keyframes sj-flash {
  0%, 4%   { background: #fff; }
  5%, 8%   { background: #000; }
  9%, 11%  { background: #7d0000; }
  12%, 14% { background: #fff; }
  15%, 19% { background: #000; }
  20%, 22% { background: #4a0000; }
  23%      { background: #000; }
  100%     { background: #000; }
}
@keyframes sj-static-shift {
  0%   { transform: translate3d(0, 0, 0); }
  50%  { transform: translate3d(-2%, 1.5%, 0); }
  100% { transform: translate3d(1.5%, -2%, 0); }
}
@keyframes sj-dart {
  0%   { transform: translate(0, 0); }
  50%  { transform: translate(6px, -4px); }
  100% { transform: translate(-5px, 3px); }
}
@keyframes sj-numflick {
  0%   { opacity: 1; }
  50%  { opacity: .3; }
  100% { opacity: 1; }
}`;

  // Shaking the page itself (not just the overlay) is most of why this lands.
  // The overlay host hangs off <html>, so it stays rock-steady while <body> moves.
  const PAGE_CSS = `
@keyframes sj-page-quake {
  0%   { transform: translate3d(-9px, 5px, 0) rotate(-.5deg); }
  25%  { transform: translate3d(8px, -7px, 0) rotate(.45deg); }
  50%  { transform: translate3d(-6px, -4px, 0) rotate(-.3deg); }
  75%  { transform: translate3d(7px, 6px, 0) rotate(.4deg); }
  100% { transform: translate3d(-8px, 3px, 0) rotate(-.45deg); }
}
body.sj-quake { animation: sj-page-quake .05s steps(2) infinite !important; will-change: transform; }`;

  function trigger(isTest) {
    if (!cfg.enabled && !isTest) return;
    if (scaring) return;
    if (siteBlocked() && !isTest) return;

    const now = Date.now();
    if (!isTest && now - lastScare < Math.max(0, Number(cfg.cooldownMs) || 0)) return;
    lastScare = now;
    scaring = true;

    const look = profile();
    const duration = Math.max(600, Math.min(Number(cfg.durationMs) || 2600, 8000));
    const dread = look.dread;
    const total = dread + duration;

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
    root.className =
      "sj-root" + (look.strobe ? " sj-strobe" : "") + (look.glitch ? " sj-glitch" : "");
    root.style.setProperty("--sj-dur", duration + "ms");
    root.style.setProperty("--sj-dread", dread + "ms");
    root.style.setProperty("--sj-hit", dread + 260 + "ms"); // when the rush finishes landing

    root.innerHTML =
      (dread > 0 ? '<div class="sj-dread">' + FACE_A + "</div>" : "") +
      '<div class="sj-stage">' +
        FACE_A +
        '<div class="sj-b">' + FACE_B + "</div>" +
        (look.glitch ? '<div class="sj-ghost">' + FACE_B + "</div>" : "") +
      "</div>" +
      '<div class="sj-scan"></div>' +
      '<div class="sj-vignette"></div>' +
      '<div class="sj-caption">6&nbsp;7</div>' +
      '<div class="sj-hint">click or press Esc to dismiss</div>';

    shadow.append(style, root);
    (document.documentElement || document.body).appendChild(host);

    // --- page-level effects, each with its own restore
    const restore = [];
    const docEl = document.documentElement;

    const prevOverflow = docEl.style.overflow;
    docEl.style.overflow = "hidden"; // the shake must not spawn scrollbars
    restore.push(() => { docEl.style.overflow = prevOverflow; });

    if (look.pageShake && document.body) {
      const pageStyle = document.createElement("style");
      pageStyle.setAttribute("data-sixty-seven-jumpscare-css", "");
      pageStyle.textContent = PAGE_CSS;
      docEl.appendChild(pageStyle);
      const body = document.body;
      const quakeTimer = setTimeout(() => body.classList.add("sj-quake"), dread);
      restore.push(() => {
        clearTimeout(quakeTimer);
        body.classList.remove("sj-quake");
        pageStyle.remove();
      });
    }

    if (look.hijackTitle) {
      const prevTitle = document.title;
      const titleTimer = setTimeout(() => { document.title = "6 7"; }, dread);
      restore.push(() => {
        clearTimeout(titleTimer);
        document.title = prevTitle;
      });
    }

    if (look.pageShake && navigator.vibrate) {
      try {
        setTimeout(() => navigator.vibrate([90, 40, 220]), dread);
      } catch (_) {}
    }

    audio(dread);

    let done = false;
    const cleanup = () => {
      if (done) return;
      done = true;
      clearTimeout(timer);
      removeEventListener("keydown", onEscape, true);
      restore.forEach((fn) => { try { fn(); } catch (_) {} });
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
    const timer = setTimeout(cleanup, total);

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
