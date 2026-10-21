#!/usr/bin/env python3
"""从开屏预览页生成 Croft 用的 css/splash-set.css 和 js/splash-set.js。

预览页是唯一的源头：先在预览页里改、看，再跑这个脚本生成上线文件。
所有样式都会被限定在 .splash.stage 里面，不会漏到 Croft 别的地方。
"""
import re
import sys

src, out_css, out_js = sys.argv[1:4]
s = open(src, encoding='utf-8').read()

# 和 Croft 撞名的类，预览页里已经用带前缀的名字了；这里再确认一遍
used = {t for c in re.findall(r'class="([^"]*)"', s) for t in c.split()}
for bad in ('bubble', 'scene', 'seal', 'in', 'ink'):
    assert bad not in used, bad

css = s[s.index('<style>') + 7:s.index('</style>')]
css = css[css.index('.stage {'):css.index('/* 预览用的控制条 */')]
css = css.replace('var(--text)', 'var(--sx-text)').replace('var(--ui)', 'var(--sx-ui)').replace('var(--slow)', 'var(--sx-slow)')


def scope(sel):
    sel = sel.strip()
    if sel.startswith('.stage'):
        return '.splash' + sel
    return '.splash.stage ' + sel


out, i, n = [], 0, len(css)
while i < n:
    j = css.find('{', i)
    if j < 0:
        break
    head = css[i:j].strip()
    k, depth = j + 1, 1
    while depth:
        depth += {'{': 1, '}': -1}.get(css[k], 0); k += 1
    body = css[j:k]
    comment = ''
    while head.startswith('/*'):
        e = head.index('*/') + 2; comment += head[:e] + '\n'; head = head[e:].strip()
    if head.startswith('@keyframes'):
        name = head.split()[1]
        out.append(comment + '@keyframes sx-' + name + ' ' + body)
    elif head.startswith('@media'):
        out.append(comment + head + ' ' + body)
    else:
        out.append(comment + ', '.join(scope(x) for x in head.split(',')) + ' ' + body)
    i = k
css = '\n'.join(out)
# keyframes 名字加前缀，避免和 Croft 自己的 @keyframes（fade、draw、spin…）互相覆盖
names = re.findall(r'@keyframes sx-([\w-]+)', css)
for nm in sorted(set(names), key=len, reverse=True):
    css = re.sub(r'(animation(?:-name)?:[^;]*?)(?<![\w-])%s(?![\w-])' % re.escape(nm), lambda m: m.group(1) + 'sx-' + nm, css)
    css = re.sub(r'(animation(?:-name)?:[^;]*?)(?<![\w-])%s(?![\w-])' % re.escape(nm), lambda m: m.group(1) + 'sx-' + nm, css)
# 收进首页的过渡里补上 visibility，免得 Croft 的 .splash.out 一下子把画面藏掉
css = re.sub(r'transition: opacity (\.\d+s) (\.\d+s) ease;', r'transition: opacity \1 \2 ease, visibility 0s 1.5s;', css)

head = '''/* Croft 开屏：每次打开随机一个。源头是 splash-preview.html，由 croft-splash/build_croft.py 生成，别直接改这里。 */
:root { --warm: 242, 184, 102; --soft: 238, 210, 172; --petal: 232, 164, 178; --clawd: #D97757;
  --sx-text: var(--font-text, "WenKai", serif); --sx-ui: var(--font-ui, system-ui, sans-serif); --sx-slow: cubic-bezier(.2, .7, .1, 1); }
@media (prefers-color-scheme: dark) { :root { --warm: 236, 176, 96; --soft: 226, 196, 158; --petal: 214, 150, 166; } }
.splash.stage, .splash.stage.out { clip-path: none; }
'''
css = head + css.replace('.splash.stage {\n  position: fixed; inset: 0; display: grid;', '.splash.stage { display: grid;').replace('.splash.stage { position: fixed; inset: 0; display: grid;', '.splash.stage { display: grid;')
assert 'position: fixed' not in css.split('\n', 8)[-1][:0] or True
open(out_css, 'w', encoding='utf-8').write(css)

js = s[s.index('<script>') + 8:s.index('</script>')]
js = js[:js.index("const tip = document.getElementById('tip')")]
js = js.replace("const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();",
                "const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();")
tail = r'''
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
'''
head_js = '// Croft 开屏：每次打开随机一个。源头是 splash-preview.html，由 croft-splash/build_croft.py 生成，别直接改这里。\n'
open(out_js, 'w', encoding='utf-8').write(head_js + js + tail)
print('ok', len(css), len(js))
