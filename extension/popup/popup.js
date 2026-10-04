/* Popup: reads and writes the same chrome.storage.sync keys the content script watches,
 * so every change takes effect on open tabs immediately. */
(() => {
  "use strict";

  const DEFAULTS = {
    enabled: true,
    volume: 0.7,
    sound: true,
    durationMs: 2200,
    cooldownMs: 1500,
    looseMatch: true,
    skipPassword: true,
    blocklist: [],
    scareCount: 0
  };

  const $ = (id) => document.getElementById(id);
  const el = {
    enabled: $("enabled"),
    volume: $("volume"),
    volumeOut: $("volumeOut"),
    durationMs: $("durationMs"),
    durationOut: $("durationOut"),
    cooldownMs: $("cooldownMs"),
    cooldownOut: $("cooldownOut"),
    sound: $("sound"),
    looseMatch: $("looseMatch"),
    skipPassword: $("skipPassword"),
    blocklist: $("blocklist"),
    count: $("count"),
    test: $("test"),
    status: $("status")
  };

  const secs = (ms) => (ms / 1000).toFixed(1).replace(/\.0$/, "") + "s";

  function paintLabels() {
    el.volumeOut.textContent = el.volume.value + "%";
    el.durationOut.textContent = secs(Number(el.durationMs.value));
    el.cooldownOut.textContent =
      Number(el.cooldownMs.value) === 0 ? "none" : secs(Number(el.cooldownMs.value));
  }

  function paintCount(n) {
    const count = Number(n) || 0;
    el.count.textContent = count === 1 ? "1 scare so far" : count + " scares so far";
  }

  /* ---- load ---- */
  chrome.storage.sync.get(DEFAULTS, (cfg) => {
    el.enabled.checked = !!cfg.enabled;
    el.sound.checked = !!cfg.sound;
    el.looseMatch.checked = !!cfg.looseMatch;
    el.skipPassword.checked = !!cfg.skipPassword;
    el.volume.value = Math.round((Number(cfg.volume) || 0) * 100);
    el.durationMs.value = Number(cfg.durationMs) || DEFAULTS.durationMs;
    el.cooldownMs.value = Number(cfg.cooldownMs) || 0;
    el.blocklist.value = (cfg.blocklist || []).join("\n");
    paintLabels();
    paintCount(cfg.scareCount);
  });

  /* ---- save ---- */
  const save = (patch) => chrome.storage.sync.set(patch);

  el.enabled.addEventListener("change", () => {
    save({ enabled: el.enabled.checked });
    flash(el.enabled.checked ? "Armed." : "Disarmed.");
  });
  el.sound.addEventListener("change", () => save({ sound: el.sound.checked }));
  el.looseMatch.addEventListener("change", () => save({ looseMatch: el.looseMatch.checked }));
  el.skipPassword.addEventListener("change", () => save({ skipPassword: el.skipPassword.checked }));

  el.volume.addEventListener("input", () => {
    paintLabels();
    save({ volume: Number(el.volume.value) / 100 });
  });
  el.durationMs.addEventListener("input", () => {
    paintLabels();
    save({ durationMs: Number(el.durationMs.value) });
  });
  el.cooldownMs.addEventListener("input", () => {
    paintLabels();
    save({ cooldownMs: Number(el.cooldownMs.value) });
  });

  let blockTimer;
  el.blocklist.addEventListener("input", () => {
    clearTimeout(blockTimer);
    blockTimer = setTimeout(() => {
      const list = el.blocklist.value
        .split(/[\s,]+/)
        .map((s) => s.trim().toLowerCase().replace(/^https?:\/\//, "").replace(/\/.*$/, ""))
        .filter(Boolean);
      save({ blocklist: [...new Set(list)] });
    }, 400);
  });

  /* ---- live scare counter ---- */
  chrome.storage.onChanged.addListener((changes, area) => {
    if (area === "sync" && changes.scareCount) paintCount(changes.scareCount.newValue);
  });

  /* ---- test ---- */
  let statusTimer;
  function flash(text) {
    el.status.textContent = text;
    clearTimeout(statusTimer);
    statusTimer = setTimeout(() => { el.status.textContent = ""; }, 3200);
  }

  el.test.addEventListener("click", () => {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      const tab = tabs && tabs[0];
      if (!tab || tab.id == null) {
        flash("No tab to scare here.");
        return;
      }
      chrome.tabs.sendMessage(tab.id, { type: "SIXTY_SEVEN_TEST" }, () => {
        if (chrome.runtime.lastError) {
          flash("Can't reach this page — reload the tab, or try a normal website.");
        } else {
          window.close();
        }
      });
    });
  });
})();
