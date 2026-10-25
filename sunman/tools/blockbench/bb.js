// Drives a real Blockbench (web build) headlessly. Used by tools/blockbench_run.py.
//   node bb.js job.json
// job = {url, model, out_dir, width, height,
//        report: bool,                          -> out_dir/report.json
//        shots: [{name, position, target, mode?, animation?, time?}],      -> out_dir/<name>.png
//        clips: [{animation, fps, position, target, frames_dir, hold_frames?}], -> frames
//        sample: {path, steps},                 -> Blockbench's own interpolated channel values
//        export: {bedrock_geo, bedrock_anim}}   -> files written by Blockbench's own codecs
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

(async () => {
  const job = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
  const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  const page = await browser.newPage({ viewport: { width: job.width || 1300, height: job.height || 1000 } });
  const pageErrors = [];
  page.on('pageerror', e => pageErrors.push(String(e && e.message || e)));
  await page.goto(job.url, { waitUntil: 'load' });
  await page.waitForFunction(() => window.Blockbench && Blockbench.setup_successful, null, { timeout: 120000 });
  const model = JSON.parse(fs.readFileSync(job.model, 'utf8'));
  const report = await page.evaluate(async ({ model, name }) => {
    const errs = [];
    try { Codecs.project.load(model, { path: name }); } catch (e) { errs.push(String(e && e.stack || e)); }
    await new Promise(r => setTimeout(r, 1200));
    const st = document.createElement('style');
    st.textContent = '.orbit_gizmo, .preview_menu { display: none !important; }';
    document.head.appendChild(st);
    try { Interface.data.left_bar_width = 0; Interface.data.right_bar_width = 0; resizeWindow(); } catch (e) {}
    return {
      blockbench: Blockbench.version, format: Format && Format.id, errors: errs,
      cubes: Cube.all.length, bones: Group.all.length,
      textures: Texture.all.map(t => ({ name: t.name, width: t.width, height: t.height, error: t.error })),
      animations: Animation.all.map(a => ({ name: a.name, length: a.length, loop: a.loop,
        keyframes: Object.values(a.animators).reduce((n, an) => n + (an.keyframes ? an.keyframes.length : 0), 0) })),
    };
  }, { model, name: path.basename(job.model) });
  console.log(JSON.stringify({ model: path.basename(job.model), ...report, animations: report.animations.length }));
  if (job.out_dir) fs.mkdirSync(job.out_dir, { recursive: true });
  if (job.report) fs.writeFileSync(path.join(job.out_dir, 'report.json'), JSON.stringify(report, null, 1));

  async function frame(opts) {
    return page.evaluate(async (o) => {
      if (o.animation) {
        if (!Modes.animate) Modes.options.animate.select();
        const a = Animation.all.find(x => x.name === o.animation);
        if (!a) return { err: 'no animation ' + o.animation };
        if (Animation.selected !== a) a.select();
        Timeline.setTime(o.time || 0);
        Animator.preview();
      } else if (!Modes.edit) Modes.options.edit.select();
      const p = Preview.selected || main_preview;
      if (o.background) { try { p.renderer.setClearColor(o.background, 1); } catch (e) {} }
      p.camera.position.set(...o.position);
      p.controls.target.set(...o.target);
      p.controls.update();
      await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
      const r = p.canvas.getBoundingClientRect();
      return { rect: [r.x, r.y, r.width, r.height] };
    }, opts);
  }

  for (const shot of (job.shots || [])) {
    const f = await frame(shot);
    if (f.err) { console.log('shot error', shot.name, f.err); continue; }
    const [x, y, w, h] = f.rect;
    await page.screenshot({ path: path.join(job.out_dir, shot.name + '.png'), clip: { x, y, width: w, height: h } });
  }

  for (const clip of (job.clips || [])) {
    const a = report.animations.find(x => x.name === clip.animation);
    if (!a) { console.log('missing animation', clip.animation); continue; }
    fs.mkdirSync(clip.frames_dir, { recursive: true });
    const fps = clip.fps || 12.5;
    const n = Math.max(1, Math.round(a.length * fps)) + (clip.hold_frames || 0);
    for (let i = 0; i < n; i++) {
      const f = await frame({ ...clip, time: Math.min(a.length, i / fps) });
      const [x, y, w, h] = f.rect;
      await page.screenshot({ path: path.join(clip.frames_dir, String(i).padStart(4, '0') + '.png'), clip: { x, y, width: w, height: h } });
    }
  }

  if (job.sample) {
    const res = await page.evaluate(async (steps) => {
      Modes.options.animate.select();
      const out = {};
      for (const a of Animation.all) {
        a.select();
        const rows = [];
        for (let i = 0; i <= steps; i++) {
          const t = a.length * i / steps;
          Timeline.setTime(t);
          const row = { t, bones: {} };
          for (const id in a.animators) {
            const an = a.animators[id];
            if (!an.group) continue;
            row.bones[an.name] = { r: an.rotation.length ? an.interpolate('rotation') : null,
                                   p: an.position.length ? an.interpolate('position') : null };
          }
          rows.push(row);
        }
        out[a.name] = rows;
      }
      return out;
    }, job.sample.steps || 37);
    fs.writeFileSync(job.sample.path, JSON.stringify(res));
  }

  if (job.export) {
    const ex = await page.evaluate(() => {
      const r = {};
      try { r.geo = Codecs.bedrock.compile(); } catch (e) { r.geo_err = String(e && e.stack || e); }
      try { r.anim = Format.animation_codec.compileFile(Animation.all); } catch (e) { r.anim_err = String(e && e.stack || e); }
      return r;
    });
    if (ex.geo_err || ex.anim_err) console.log('export error', ex.geo_err || '', ex.anim_err || '');
    if (ex.geo && job.export.bedrock_geo) fs.writeFileSync(job.export.bedrock_geo, typeof ex.geo === 'string' ? ex.geo : JSON.stringify(ex.geo, null, '\t'));
    if (ex.anim && job.export.bedrock_anim) fs.writeFileSync(job.export.bedrock_anim, JSON.stringify(ex.anim, null, '\t'));
  }
  const relevant = pageErrors.filter(e => !/plugin|ServiceWorker|news|^Object$/i.test(e));
  if (relevant.length) console.log('page errors:', relevant.slice(0, 5).join(' | '));
  await browser.close();
})();
