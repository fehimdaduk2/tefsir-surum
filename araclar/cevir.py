#!/usr/bin/env python3
"""The introduction page in English and Arabic: docs/index.html (and gizlilik.html) are the Turkish pages; this rewrites
their texts and alt / content / aria-label attributes through sayfa.json (gizlilik.json) — {Turkish text: [English,
Arabic]} — into docs/en/ and docs/ar/. duzeltmeler.py holds what is not a text: paths, lang/dir, the script's words.
  cevir.py eksik      lists the texts of the Turkish pages missing from the tables (after the Turkish page changes)
  cevir.py            builds the pages; a missing text is reported and left in Turkish"""
import html, json, os, re, sys
from html.parser import HTMLParser
D = os.path.dirname(os.path.abspath(__file__)); DOCS = os.path.join(D, '..', 'docs')
ATTRS = ('alt', 'content', 'aria-label', 'title', 'placeholder')

class Parts(HTMLParser):
    """Splits the page into pieces: markup as it stands and the texts between, so that a text can be swapped."""
    def __init__(self):
        super().__init__(convert_charrefs=False); self.out = []; self.skip = 0
    def handle_starttag(self, tag, attrs): self._tag(self.get_starttag_text(), tag, start=True)
    def handle_startendtag(self, tag, attrs): self._tag(self.get_starttag_text(), tag)
    def handle_endtag(self, tag):
        if tag in ('script', 'style'): self.skip -= 1
        self.out.append(('m', f'</{tag}>'))
    def _tag(self, raw, tag, start=False):
        if start and tag in ('script', 'style'): self.skip += 1
        self.out.append(('t', raw))
    def handle_data(self, d): self.out.append(('s' if self.skip else 'x', d))
    def handle_entityref(self, n): self.out.append(('x', f'&{n};'))
    def handle_charref(self, n): self.out.append(('x', f'&#{n};'))
    def handle_comment(self, d): self.out.append(('m', f'<!--{d}-->'))
    def handle_decl(self, d): self.out.append(('m', f'<!{d}>'))

def pieces(path):
    p = Parts(); p.feed(open(path, encoding='utf-8').read()); p.close()
    # join neighbouring text pieces (entities split them)
    out = []
    for k, v in p.out:
        if k == 'x' and out and out[-1][0] == 'x': out[-1] = ('x', out[-1][1] + v)
        else: out.append((k, v))
    return out

def texts(ps):
    seen = []
    for k, v in ps:
        if k == 'x':
            t = re.sub(r'\s+', ' ', html.unescape(v)).strip()
            if re.search(r'[A-Za-zÇĞİÖŞÜçğıöşüâîû]{2}', t) and t not in seen: seen.append(t)
        elif k == 't':
            for a in ATTRS:
                for m in re.finditer(rf'\b{a}="([^"]*)"', v):
                    t = html.unescape(m.group(1)).strip()
                    if re.search(r'[A-Za-zÇĞİÖŞÜçğıöşüâîû]{3}', t) and t not in seen: seen.append(t)
    return seen

def table(name):
    d = json.load(open(os.path.join(D, name), encoding='utf-8'))
    return {'en': {k: v[0] for k, v in d.items()}, 'ar': {k: v[1] for k, v in d.items()}}

def build(src, dst, tb, L, fix):
    ps = pieces(src); miss = []
    def tr(t):
        k = re.sub(r'\s+', ' ', html.unescape(t)).strip()
        if not k or not re.search(r'[A-Za-zÇĞİÖŞÜçğıöşüâîû]{2}', k): return t
        if k in tb: lead = re.match(r'\s*', t).group(0); tail = re.search(r'\s*$', t).group(0); return lead + html.escape(tb[k], quote=False) + tail
        miss.append(k); return t
    out = []
    for k, v in ps:
        if k == 'x': out.append(tr(v))
        elif k == 't':
            for a in ATTRS:
                v = re.sub(rf'\b({a})="([^"]*)"', lambda m: f'{m.group(1)}="{html.escape(tb.get(html.unescape(m.group(2)).strip(), html.unescape(m.group(2))), quote=True)}"', v)
            out.append(v)
        else: out.append(v)
    s = ''.join(out)
    for a, b in fix: s = s.replace(a, b)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    open(dst, 'w', encoding='utf-8').write(s)
    return miss

PAGES = [('index.html', 'sayfa.json'), ('gizlilik.html', 'gizlilik.json')]
SKIP = {'TR', 'EN', 'عربي'}   # the language switch
sys.path.insert(0, D); import duzeltmeler
for src, tab in PAGES:
    tb = table(tab)
    if sys.argv[1:] == ['eksik']:
        print(src, [k for k in texts(pieces(os.path.join(DOCS, src))) if k not in tb['en'] and k not in SKIP]); continue
    for L in ('en', 'ar'):
        miss = [m for m in build(os.path.join(DOCS, src), os.path.join(DOCS, L, src), tb[L], L, duzeltmeler.FIX[L](src)) if m not in SKIP]
        print(L, src, 'eksik:', len(miss), miss[:5])
