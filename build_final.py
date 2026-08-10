import json, re

LETTERS = "ABCD"

def strip_html(s):
    if not s:
        return ''
    s = re.sub(r'<[^>]+>', '', s)
    s = re.sub(r'&nbsp;', ' ', s)
    s = re.sub(r'&amp;', '&', s)
    s = re.sub(r'&lt;', '<', s)
    s = re.sub(r'&gt;', '>', s)
    s = re.sub(r'&quot;', '"', s)
    s = re.sub(r'&#\d+;', '', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def norm(s):
    return re.sub(r'\W', '', s or '').lower()

def ans_to_idx(ans):
    if isinstance(ans, int):
        return ans
    ans = str(ans).strip().upper()
    if ans in LETTERS:
        return LETTERS.index(ans)
    return -1

def clean_opt(o):
    # strip any leading "A．" / "A." / "A、" so we can re-label uniformly
    o = strip_html(o)
    o = re.sub(r'^[A-D][．.、]\s*', '', o).strip()
    return o

def relabel(opts):
    return [f"{LETTERS[i]}. {clean_opt(o)}" for i, o in enumerate(opts)]

# ---- load existing bank (941) ----
existing = json.load(open('questions.json'))['questions']

# ---- load knowledge bank (4137) ----
cb = json.load(open('src_data/case-bank.json'))
kb = cb['knowledge']['questions']

def from_knowledge(q):
    raw_opts = [o.get('html') or o.get('text', '') for o in q.get('options', [])]
    if len(raw_opts) != 4:
        return None
    ans = q.get('correctAnswer') or next((o['label'] for o in q['options'] if o.get('correct')), '')
    idx = ans_to_idx(ans)
    if idx < 0:
        return None
    label = q.get('sourceLabel', '')
    cat0 = q.get('sourceCategory', '')
    is_paper = any(k in label for k in ['上午题', '批次', '密卷', '真题']) or cat0 in ('真题', '模拟')
    if is_paper:
        cat = '历年真题' if ('上午题' in label or '批次' in label or '真题' in label) else '模拟密卷'
        paper = label
    else:
        cat = label
        paper = None
    return {
        'id': 'kb-' + q.get('id', ''),
        'cat': cat,
        'q': strip_html(q.get('stemText') or q.get('stemHtml', '')),
        'opts': relabel(raw_opts),
        'ans': idx,
        'exp': strip_html(q.get('explanationHtml', '')),
        'paper': paper,
        'src': 'IHKYoung-章节/真题',
        '_pri': 5 if q.get('explanationHtml') else 1,
    }

knowledge_items = []
for q in kb:
    r = from_knowledge(q)
    if r:
        knowledge_items.append(r)

print('knowledge usable:', len(knowledge_items), '/', len(kb))

def norm_existing(it):
    it = dict(it)
    # ensure opts are cleanly labeled and ans is int index
    opts = relabel([it['opts'][i] if i < len(it['opts']) else '' for i in range(4)])
    it['opts'] = opts
    it['ans'] = ans_to_idx(it.get('ans'))
    it['_pri'] = 4 if it.get('exp') else 2
    return it

existing_items = [norm_existing(it) for it in existing if ans_to_idx(it.get('ans')) >= 0]

def dkey(it):
    return norm(it['q']) + '|' + norm(it['opts'][0] if it['opts'] else '') + '|' + str(it['ans'])

merged = {}
order = []
def add(it):
    k = dkey(it)
    if k in merged:
        prev = merged[k]
        if it['_pri'] > prev['_pri'] or (it['_pri'] == prev['_pri'] and len(it.get('exp', '')) > len(prev.get('exp', ''))):
            merged[k] = it
    else:
        merged[k] = it
        order.append(k)

for it in knowledge_items:
    add(it)
for it in existing_items:
    add(it)

final = [merged[k] for k in order]
for it in final:
    it.pop('_pri', None)

clean = [it for it in final if len(it.get('opts', [])) == 4 and it.get('ans') in (0, 1, 2, 3) and it.get('q')]
print('final clean:', len(clean))

from collections import Counter, OrderedDict
papers = OrderedDict()
for it in clean:
    if it.get('paper'):
        papers.setdefault(it['paper'], 0)
        papers[it['paper']] += 1
cats = Counter(it['cat'] for it in clean)

out = {
    'questions': clean,
    'papers': [{'name': n, 'count': c} for n, c in papers.items()],
    'note': 'merged real banks: IHKYoung 章节练习+历年真题(2019-2025)+押题密卷 + cnitpm历年真题(2021下~2025上) + 自研补充',
}
json.dump(out, open('questions.json', 'w'), ensure_ascii=False, indent=1)
print('TOTAL:', len(clean))
print('papers:', len(papers))
print('by cat (top 20):')
for c, n in cats.most_common(20):
    print(f'  {n:4d}  {c}')
