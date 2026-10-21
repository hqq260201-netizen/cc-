// Croft 开屏：每次打开随机一个。源头是 splash-preview.html，由 croft-splash/build_croft.py 生成，别直接改这里。

const W = ['日', '一', '二', '三', '四', '五', '六'];
const now = new Date();
const DATE = (now.getMonth() + 1) + '月' + now.getDate() + '日 · 周' + W[now.getDay()];
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const dpr = Math.min(2, window.devicePixelRatio || 1);
function fit(cv, w, h) { cv.width = w * dpr; cv.height = h * dpr; const c = cv.getContext('2d'); c.scale(dpr, dpr); return c; }
const letters = (word, colors, start, step) => [...word].map((ch, i) =>
  `<span style="color:${colors[i % colors.length]};--r:${[-6, 4, -3, 5, -4][i % 5]}deg;animation-delay:${(start + i * step).toFixed(2)}s,${(start + 0.6 + i * 0.1).toFixed(2)}s">${ch}</span>`).join('');

const V = [
  { id: 'lamp', name: '一盏灯', html: () => `<div class="mark"><div class="lamp"><b></b><i></i></div>
      <div class="word sx-in" style="animation-delay:.7s">Croft</div><div class="lamp-rule"></div><div class="sub fadein" style="animation-delay:1.6s">${DATE}</div></div>` },

  { id: 'door', name: '推门', html: () => `<div class="mark"><div class="dw"><div class="halo"></div>
      <div class="door"><div class="room"></div><div class="leaf"><i></i></div></div>
      <svg class="frame" viewBox="0 0 58 100" aria-hidden="true"><path pathLength="1" d="M.65 100 V29 A28.35 28.35 0 0 1 57.35 29 V100"/></svg></div>
      <div class="door-ground"></div><div class="word sx-in" style="animation-delay:1.4s;font-size:38px">Croft</div>
      <div class="sub fadein" style="animation-delay:1.8s;margin-top:12px">${DATE}</div></div>` },

  { id: 'moon', name: '月升', html: () => `<div class="mark"><div class="sky"><div class="moon"><svg viewBox="0 0 46 46" aria-hidden="true"><path d="M30 4a20 20 0 1 0 12 30A16 16 0 1 1 30 4z"/></svg></div></div>
      <div class="hz"></div><div class="word sx-in" style="animation-delay:1.2s;font-size:40px">Croft</div>
      <div class="sub fadein" style="animation-delay:1.6s;margin-top:14px">${DATE}</div></div>` },

  { id: 'ink', name: '墨晕', html: () => `<div class="mark"><div class="sx-ink"></div><div class="ink-word">Croft</div>
      <svg class="brush" viewBox="0 0 120 14" aria-hidden="true"><path pathLength="1" d="M4 9 C 30 4, 70 12, 116 6"/></svg></div>` },

  { id: 'stars', name: '星河', html: () => `<canvas></canvas><div class="mark" style="margin-top:150px"><div class="sub fadein" style="animation-delay:1.7s">${DATE}</div></div>`,
    start(el) {
      // 满屏星点飘过来，聚成 Croft 的字形；离开时向四周散开
      const cv = el.querySelector('canvas'), w = el.clientWidth, h = el.clientHeight, c = fit(cv, w, h);
      const fs = Math.min(w * .3, 128), off = document.createElement('canvas'), oc = off.getContext('2d');
      off.width = w; off.height = h; oc.font = `${fs}px WenKai, serif`; oc.textAlign = 'center'; oc.textBaseline = 'middle'; oc.fillText('Croft', w / 2, h * .45);
      const data = oc.getImageData(0, 0, w, h).data, pts = [], gap = w < 500 ? 4 : 5;
      for (let y = 0; y < h; y += gap) for (let x = 0; x < w; x += gap) if (data[(y * w + x) * 4 + 3] > 128) pts.push([x, y]);
      const ink = css('--ink'), warm = css('--warm');
      const P = pts.slice(0, 1400).map(([tx, ty]) => ({ tx, ty, x: Math.random() * w, y: Math.random() * h, d: Math.random() * .6,
        r: Math.random() * .7 + .7, warm: Math.random() < .14, tw: Math.random() * 6 }));
      const S = Array.from({ length: 90 }, () => ({ x: Math.random() * w, y: Math.random() * h, r: Math.random() * .9 + .3, tw: Math.random() * 6 }));
      const t0 = performance.now(); let out = 0, raf;
      const ease = t => 1 - Math.pow(1 - t, 3);
      (function frame(t) {
        const s = (t - t0) / 1000; c.clearRect(0, 0, w, h);
        for (const p of S) { c.globalAlpha = .25 + .25 * Math.sin(s * 2 + p.tw); c.fillStyle = ink; c.beginPath(); c.arc(p.x, p.y, p.r, 0, 7); c.fill(); }
        for (const p of P) {
          let k = ease(Math.min(1, Math.max(0, (s - p.d) / 1.5))), x = p.x + (p.tx - p.x) * k, y = p.y + (p.ty - p.y) * k, a = .25 + .75 * k;
          if (out) { const o = Math.min(1, (t - out) / 900), dx = p.tx - w / 2, dy = p.ty - h * .45; x = p.tx + dx * o * 1.6; y = p.ty + dy * o * 1.6; a *= 1 - o; }
          c.globalAlpha = a * (.8 + .2 * Math.sin(s * 3 + p.tw)); c.fillStyle = p.warm ? `rgb(${warm})` : ink;
          c.beginPath(); c.arc(x, y, p.r, 0, 7); c.fill();
        }
        raf = requestAnimationFrame(frame);
      })(t0);
      return { exit() { out = performance.now(); }, stop() { cancelAnimationFrame(raf); } };
    } },

  { id: 'petals', name: '落花', html: () => `<canvas></canvas><div class="mark"><div class="word sx-in" style="animation-delay:.6s;font-size:48px">Croft</div>
      <div class="sub fadein" style="animation-delay:1.3s;margin-top:14px">${DATE}</div></div>`,
    start(el) {
      const cv = el.querySelector('canvas'), w = el.clientWidth, h = el.clientHeight, c = fit(cv, w, h), col = css('--petal');
      const P = Array.from({ length: 38 }, () => ({ x: Math.random() * w, y: Math.random() * h * 1.1 - h * .5, v: 45 + Math.random() * 55,
        a: 14 + Math.random() * 26, f: .6 + Math.random() * .9, ph: Math.random() * 6, s: 5 + Math.random() * 6, rot: Math.random() * 6, vr: (Math.random() - .5) * 3 }));
      let last = performance.now(), raf;
      (function frame(t) {
        const dt = Math.min(.05, (t - last) / 1000); last = t; c.clearRect(0, 0, w, h);
        for (const p of P) {
          p.y += p.v * dt; p.rot += p.vr * dt; p.ph += p.f * dt * 2;
          if (p.y > h + 20) { p.y = -20; p.x = Math.random() * w; }
          const x = p.x + Math.sin(p.ph) * p.a;
          c.save(); c.translate(x, p.y); c.rotate(p.rot); c.scale(1, .55 + .45 * Math.abs(Math.cos(p.ph)));
          c.globalAlpha = .85; c.fillStyle = `rgb(${col})`;
          c.beginPath(); c.moveTo(0, -p.s); c.quadraticCurveTo(p.s, -p.s * .2, 0, p.s); c.quadraticCurveTo(-p.s, -p.s * .2, 0, -p.s); c.fill(); c.restore();
        }
        raf = requestAnimationFrame(frame);
      })(last);
      return { stop() { cancelAnimationFrame(raf); } };
    } },

  { id: 'gold', name: '鎏金', html: () => `<div class="mark"><div class="gold-box">
      <div class="gold-frame"></div><i class="corner t"></i><i class="corner b"></i>
      <div class="gold-word">Croft</div><div class="gold-sub">${DATE}</div></div></div>` },

  { id: 'crayon', name: '蜡笔小屋', html: () => `<div class="mark">
      <svg class="crayon" viewBox="0 0 200 160" aria-hidden="true">
        <defs><filter id="cr"><feTurbulence type="fractalNoise" baseFrequency=".05" numOctaves="2" seed="7"/><feDisplacementMap in="SourceGraphic" scale="3.2"/></filter></defs>
        <g filter="url(#cr)">
          <g class="sun"><circle cx="164" cy="30" r="13" fill="#F2C14E"/>
            <g class="rays" stroke="#F2C14E" stroke-width="3.5" stroke-linecap="round"><path d="M164 8v-5M164 52v5M142 30h-5M186 30h5M148 14l-3-3M180 46l3 3M180 14l3-3M148 46l-3 3"/></g></g>
          <path class="d" pathLength="1" d="M50 72 V138 H138 V72" stroke="var(--ink)" stroke-width="4.5" style="animation-delay:.2s"/>
          <path class="d" pathLength="1" d="M38 78 L94 34 L150 78" stroke="#E07A5F" stroke-width="6" style="animation-delay:.55s"/>
          <rect class="f" x="83" y="100" width="22" height="38" rx="3" fill="#7FB069" style="animation-delay:.9s"/>
          <rect class="f" x="60" y="88" width="16" height="16" rx="2" fill="#F2C14E" style="animation-delay:1s"/>
          <rect class="f" x="112" y="88" width="16" height="16" rx="2" fill="#F2C14E" style="animation-delay:1.05s"/>
          <path class="d" pathLength="1" d="M8 144 q8 -8 16 0 t16 0 t16 0 t16 0 t16 0 t16 0 t16 0 t16 0 t16 0 t16 0 t16 0 t16 0" stroke="#7FB069" stroke-width="4" style="animation-delay:.1s"/>
          <path class="d" pathLength="1" d="M124 50 V30 h10 V60" stroke="var(--ink)" stroke-width="4" style="animation-delay:.8s"/>
          <path class="d" pathLength="1" d="M129 24 q-8 -6 0 -12 q8 -6 0 -12" stroke="var(--ink-3)" stroke-width="3" style="animation-delay:1.2s"/>
        </g>
      </svg>
      <div class="pop">${letters('Croft', ['#E07A5F', '#E9A93B', '#7FB069', '#5B8DEF', '#C77DBB'], 1.15, .12)}</div></div>` },

  { id: 'clawd', name: 'Clawd', html: () => `<div class="mark"><div class="cl">
      <img class="walk" src="/pet-assets/clawd-full/clawd-mini-crabwalk.svg" alt="">
      <img class="wave" src="/pet-assets/clawd-full/croft-wave.svg" alt=""><div class="sx-bubble">嗨～</div></div>
      <div class="pop" style="font-size:44px">${letters('Croft', ['var(--clawd)', 'var(--ink)'], 1.5, .1)}</div></div>` },
  { id: 'bird', name: '啄羊鹦鹉', html: () => `<div class="mark">
      <svg class="sx-scene" viewBox="0 0 230 175" aria-hidden="true">
        <line x1="6" y1="162" x2="224" y2="162" stroke="var(--ink-3)" stroke-width="1.2"/>
        <rect x="140" y="52" width="14" height="30" fill="var(--ink-3)"/>
        <rect class="walls" x="62" y="96" width="106" height="66"/>
        <path class="roof" d="M50 100 L115 52 L180 100 Z"/>
        <rect x="104" y="122" width="22" height="40" rx="2" fill="var(--ink)" opacity=".75"/>
        <rect class="win" x="76" y="112" width="18" height="18" rx="2"/><rect class="win" x="138" y="112" width="18" height="18" rx="2"/>
        <g transform="translate(115 52)"><g class="bird-x"><g class="bird-y"><g class="bird-b">
          <path d="M-14 -10 q-12 -2 -16 -10 q8 0 16 4z" fill="#4E6B34"/>
          <ellipse cx="0" cy="-15" rx="18" ry="16" fill="#6F8C45"/><ellipse cx="6" cy="-22" rx="11" ry="9" fill="#8E928C"/>
          <ellipse cx="3" cy="-9" rx="11" ry="8" fill="#8A9A6A"/>
          <path d="M-9 -17 q6 10 16 6 q-4 -9 -16 -6z" fill="#55733A"/><path d="M-6 -9 q5 3 9 1" stroke="#D9772B" stroke-width="1.6" fill="none" stroke-linecap="round"/>
          
          <circle class="bird-eye" cx="8" cy="-21" r="2" fill="#2A2722"/>
          <path d="M15 -23 q8 -1 8 6 q-1 3 -3 3 q0 -4 -5 -5z" fill="#4A4C4E"/>
          <path d="M-3 0 v-3 M4 0 v-3" stroke="#6B6E70" stroke-width="1.6" stroke-linecap="round"/>
        </g></g></g></g>
        <text class="chirp" x="146" y="26">啾</text>
      </svg>
      <div class="word sx-in" style="animation-delay:1.3s;font-size:40px">Croft</div>
      <div class="sub fadein" style="animation-delay:1.7s;margin-top:12px">${DATE}</div></div>` },

  { id: 'smoke', name: '炊烟小屋', html: () => `<div class="mark">
      <svg class="sx-scene smoke" viewBox="0 0 230 175" aria-hidden="true">
        <path class="hill" d="M0 170 Q60 132 120 150 T230 138 V175 H0Z"/>
        <path class="house" d="M66 150 V104 L112 70 L158 104 V150Z"/>
        <rect class="house" x="136" y="72" width="12" height="24"/>
        <rect class="win" x="102" y="116" width="20" height="22" rx="10" style="filter:drop-shadow(0 0 6px rgba(var(--warm),.9))"/>
        ${[0, .52, 1.04, 1.56, 2.08].map(d => `<circle class="puff" cx="142" cy="66" r="6" style="animation-delay:${(0.5 + d).toFixed(2)}s"/>`).join('')}
      </svg>
      <div class="word sx-in" style="animation-delay:.9s;font-size:40px">Croft</div>
      <div class="sub fadein" style="animation-delay:1.4s;margin-top:12px">${DATE}</div></div>` },

  { id: 'clawdwake', name: 'Clawd 睡醒', html: () => `<div class="mark"><div class="cl">
      <img class="sleep" src="/pet-assets/clawd-full/clawd-sleeping.svg" alt="">
      <img class="wake" src="/pet-assets/clawd-full/croft-wakeup.svg" alt="">
      <div class="zzz"><span>z</span><span>z</span><span>Z</span></div><div class="sx-bubble">早呀～</div></div>
      <div class="pop" style="font-size:44px">${letters('Croft', ['var(--clawd)', 'var(--ink)'], 1.55, .1)}</div></div>` },

  { id: 'vault', name: '保险柜', html: () => {
      const gear = (cx, cy, r, n, d) => { let p = ''; for (let i = 0; i < n * 4; i++) { const a = i / (n * 4) * Math.PI * 2, rr = i % 4 < 2 ? r : r - d; p += (i ? 'L' : 'M') + (cx + rr * Math.cos(a)).toFixed(1) + ' ' + (cy + rr * Math.sin(a)).toFixed(1); } return p + 'Z'; };
      const ticks = Array.from({ length: 72 }, (_, i) => { const a = i * 5 * Math.PI / 180, r2 = i % 6 ? 108 : 112; return `<line class="tick" x1="${(150 + 104 * Math.cos(a)).toFixed(1)}" y1="${(130 + 104 * Math.sin(a)).toFixed(1)}" x2="${(150 + r2 * Math.cos(a)).toFixed(1)}" y2="${(130 + r2 * Math.sin(a)).toFixed(1)}"/>`; }).join('');
      const ang = [30, 90, 150, 210, 270, 330];
      const rods = ang.map(a => { const t = (a - 90) * Math.PI / 180; return `<line class="rod" x1="${(150 + 30 * Math.cos(t)).toFixed(1)}" y1="${(130 + 30 * Math.sin(t)).toFixed(1)}" x2="${(150 + 76 * Math.cos(t)).toFixed(1)}" y2="${(130 + 76 * Math.sin(t)).toFixed(1)}"/>`; }).join('');
      const bolts = ang.map(a => `<g transform="rotate(${a} 150 130)"><g class="slide"><rect class="bolt" x="146" y="22" width="8" height="30" rx="1"/><path class="hatch" d="M147 30 l6 -5 M147 37 l6 -5 M147 44 l6 -5"/></g></g>`).join('');
      return `<div class="mark"><div class="vw">
      <svg class="vbase" viewBox="0 0 300 260" aria-hidden="true">
        <path class="axis" d="M14 130 H286 M150 4 V256"/>
        <circle class="ln" pathLength="1" cx="150" cy="130" r="114" stroke-width="1.4"/><circle class="ln" pathLength="1" cx="150" cy="130" r="104" stroke-width=".8"/>${ticks}
        <path class="lead" d="M228 52 L250 26 H292"/><text class="lab" x="252" y="21">锁栓 ×6</text>
        <path class="lead" d="M110 120 L60 30 H8"/><text class="lab" x="8" y="25">齿轮组</text>
        <path class="lead" d="M96 196 L62 236 H8"/><text class="lab" x="8" y="249">门体 ⌀192</text>
      </svg>
      <div class="vlight"></div>
      <div class="vpersp"><svg class="vdoor" viewBox="0 0 300 260" aria-hidden="true">
        <circle class="face" cx="150" cy="130" r="96"/><circle class="thin" cx="150" cy="130" r="88" stroke-dasharray="2 3"/><circle class="thin" cx="150" cy="130" r="62"/>
        ${rods}${bolts}
        <g class="gear g1"><path d="${gear(106, 130, 14, 8, 3)}"/><circle cx="106" cy="130" r="3" fill="none" stroke="var(--ink)"/></g>
        <g class="gear g2"><path d="${gear(194, 130, 14, 8, 3)}"/><circle cx="194" cy="130" r="3" fill="none" stroke="var(--ink)"/></g>
        <g class="gear g0"><path d="${gear(150, 130, 30, 16, 4)}"/><circle cx="150" cy="130" r="9" fill="none" stroke="var(--ink)"/>
          <path d="M150 104 V156 M124 130 H176" stroke="var(--ink-2)" stroke-width=".8"/></g>
        <circle cx="150" cy="130" r="2.5" fill="var(--ink)"/>
      </svg></div></div>
      <div class="word sx-in" style="animation-delay:1.1s;font-size:34px">Croft</div>
      <div class="sub fadein" style="animation-delay:1.4s;margin-top:10px">${DATE}</div></div>`; } },

  { id: 'dawn', name: '日升月落', html: () => `<div class="sk a"></div><div class="sk b"></div><div class="sk c"></div><div class="dmoon"></div><div class="dsun"></div>
      <svg class="hills" viewBox="0 0 400 200" preserveAspectRatio="none" aria-hidden="true"><path class="h1" d="M0 90 Q90 30 190 80 T400 60 V200 H0Z"/><path class="h2" d="M0 140 Q120 90 230 130 T400 110 V200 H0Z"/></svg>
      <div class="mark"><div class="dword">Croft</div><div class="dsub">${DATE}</div></div>` },

  { id: 'tide', name: '涨潮', html: () => `<canvas></canvas><div class="mark" style="margin-top:-120px"><div class="word sx-in" style="animation-delay:.2s;font-size:46px">Croft</div>
      <div class="sub fadein" style="animation-delay:.8s;margin-top:14px">${DATE}</div></div>`,
    start(el) {
      // 海水慢慢涨上来，一只纸船漂着；加载好以后一个浪头盖过整屏，进首页
      const cv = el.querySelector('canvas'), w = el.clientWidth, h = el.clientHeight, c = fit(cv, w, h), t0 = performance.now();
      let flood = 0, raf;
      const layers = [{ a: 9, k: .018, sp: 1.3, top: '#5FA4A8', bot: '#2E6F78', al: .55, off: -14 }, { a: 7, k: .024, sp: -1.7, top: '#3E8790', bot: '#1F5560', al: .75, off: 0 }, { a: 5, k: .031, sp: 2.2, top: '#2C6E78', bot: '#163F4C', al: 1, off: 12 }];
      (function frame(t) {
        const s = (t - t0) / 1000; c.clearRect(0, 0, w, h);
        let lv = h + 30 - (h * .4 + 30) * (1 - Math.pow(1 - Math.min(1, s / 1.7), 3));
        if (flood) { const f = Math.min(1, (t - flood) / 900); lv = lv - (lv + h * .15) * f * f; }
        layers.forEach((L, i) => {
          const g = c.createLinearGradient(0, lv, 0, h); g.addColorStop(0, L.top); g.addColorStop(1, L.bot);
          c.globalAlpha = L.al; c.fillStyle = g; c.beginPath(); c.moveTo(0, h);
          for (let x = 0; x <= w + 8; x += 8) c.lineTo(x, lv + L.off + Math.sin(x * L.k + s * L.sp) * L.a + Math.sin(x * L.k * 2.3 - s) * L.a * .35);
          c.lineTo(w, h); c.closePath(); c.fill();
          if (i === 0) { c.globalAlpha = .5; c.strokeStyle = '#E8F4F2'; c.lineWidth = 1.2; c.stroke(); }
        });
        const bx = w * .72, by = lv + Math.sin(bx * .024 - s * 1.7) * 7 - 2, tilt = Math.cos(bx * .024 - s * 1.7) * .12;
        c.globalAlpha = 1; c.save(); c.translate(bx, by); c.rotate(tilt);
        c.fillStyle = '#F3EFE7'; c.beginPath(); c.moveTo(-16, -4); c.lineTo(16, -4); c.lineTo(10, 4); c.lineTo(-10, 4); c.closePath(); c.fill();
        c.fillStyle = '#E4DCCB'; c.beginPath(); c.moveTo(0, -4); c.lineTo(0, -22); c.lineTo(11, -6); c.closePath(); c.fill(); c.restore();
        raf = requestAnimationFrame(frame);
      })(t0);
      return { exit() { flood = performance.now(); }, stop() { cancelAnimationFrame(raf); } };
    } },

  { id: 'type', name: '打字机', html: () => `<div class="mark"><div class="paper"><span class="ding">叮</span><div class="tw big"></div><div class="tw small"></div></div></div>`,
    start(el) {
      const big = el.querySelector('.big'), small = el.querySelector('.small'), ding = el.querySelector('.ding'), timers = [];
      const caret = '<span class="caret"></span>';
      const type = (node, text, at, step, done) => [...text].forEach((ch, i) => timers.push(setTimeout(() => {
        node.innerHTML = text.slice(0, i + 1).replace(/&/g, '&amp;').replace(/</g, '&lt;') + caret;
        if (i === text.length - 1 && done) done();
      }, at + i * step)));
      big.innerHTML = caret;
      type(big, 'Croft', 700, 150, () => timers.push(setTimeout(() => { big.innerHTML = 'Croft'; ding.classList.add('on'); type(small, DATE, 80, 45); }, 160)));
      return { stop() { timers.forEach(clearTimeout); } };
    } },

  { id: 'neon', name: '霓虹灯', html: () => `<div class="mark">
      <svg class="nhouse" viewBox="0 0 92 70" aria-hidden="true"><path d="M8 34 L46 6 L84 34 M16 28 V64 H76 V28 M40 64 V46 H52 V64"/></svg>
      <div class="nword">Croft</div><div class="nsub">${DATE}</div></div>` },

  { id: 'letter', name: '拆信', html: () => `<div class="mark"><div class="env"><div class="back"></div>
      <div class="card"><b>Croft</b><span class="sub">${DATE}</span></div><div class="pocket"></div><div class="flap"></div><div class="sx-seal"></div></div></div>` },
];


// 每次打开随机一个，不和上一次一样；still（新版接管后的那次静默刷新）就重放上一次的，动画直接到最后一帧
let run = null, stopT = 0, done = false;
export function mountSplash(el, still) {
  if (run && run.stop) run.stop();
  clearTimeout(stopT); done = false;
  let last = null;
  try { last = localStorage.getItem('splash_last'); } catch (e) {}
  const pool = V.filter(v => v.id !== last);
  const v = still ? (V.find(x => x.id === last) || V[0]) : pool[Math.floor(Math.random() * pool.length)];
  el.className = 'splash stage v-' + v.id + (still ? ' still' : '');
  el.innerHTML = v.html();
  run = v.start ? v.start(el) : null;
  try { localStorage.setItem('splash_last', v.id); } catch (e) {}
}
export function watchSplash(el) {
  new MutationObserver(() => {
    if (!el.classList.contains('out') || done) return;
    done = true;
    if (run && run.exit) run.exit();
    stopT = setTimeout(() => { if (run && run.stop) run.stop(); run = null; }, 1800);
  }).observe(el, { attributes: true, attributeFilter: ['class'] });
}
