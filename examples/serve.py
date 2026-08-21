"""fides — a tiny, dependency-FREE web UI to try the grounded content studio. Enter your source data,
and fides brainstorms grounded posts / infographics / videos, renders the real SVG + HTML inline, and
shows the grounding score + source-documentation audit. Flip on "inject a fabricated stat" to watch the
gate drop a number that isn't in your data (keep the genuine, remove the fabricated).

Pure Python stdlib (http.server) — matches fides' zero-dep core. Run:

    python3 examples/serve.py           # then open http://localhost:8000

No API key needed (the deterministic grounded-by-construction path). The injected LLM ideator/composer
would slot in exactly where the fabricate toggle demonstrates.
"""
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fides import ContentStudio, Gate, NumericCheck, render_asset, render_audit_markdown
from fides.numeric import ledger

studio = ContentStudio(Gate(checks=[NumericCheck()]))

# one-click preset datasets (the 6 domains from examples/proof.py) — [value, subject, metric, period]
PRESETS = [
    {"title": "Apex Growth Fund — FY2024", "rows": [
        ["12.4%", "Apex Growth", "net return", "FY2024"], ["$1.2B", "Apex Growth", "AUM", "FY2024"],
        ["65 bps", "Apex Growth", "expense ratio", ""], ["9.8%", "benchmark", "return", "FY2024"]]},
    {"title": "Phase III trial — Drug DX-12", "rows": [
        ["34%", "DX-12", "absolute risk reduction", "52 weeks"], ["100 mg", "DX-12", "daily dose", ""],
        ["4,182", "DX-12 trial", "enrollment", ""]]},
    {"title": "Grid decarbonization — 2024", "rows": [
        ["18.6 GW", "state grid", "solar capacity", "2024"], ["27%", "state grid", "emissions cut vs 2019", "2024"],
        ["$41/MWh", "state grid", "avg clearing price", "2024"]]},
    {"title": "NorthStar SaaS — Q4", "rows": [
        ["$48M", "NorthStar", "ARR", "Q4-2024"], ["121%", "NorthStar", "net dollar retention", "Q4-2024"],
        ["1.8%", "NorthStar", "gross monthly churn", "Q4-2024"]]},
    {"title": "Striker FC — 2024 season", "rows": [
        ["89", "Striker FC", "goals scored", "2024"], ["78", "Striker FC", "points", "2024"],
        ["1.94", "Striker FC", "xG per match", "2024"]]},
    {"title": "Metro ballot measure — 2024", "rows": [
        ["58.3%", "Measure 7", "yes vote share", "2024"], ["62%", "Metro county", "turnout", "2024"],
        ["94,204", "Measure 7", "vote margin", "2024"]]},
]


def _fab_composer(idea, facts):
    """An 'LLM' post composer that fabricates a peer stat NOT present in the data — the gate drops it."""
    return {"format": "post", "spec": {"kind": "post", "text": "Peers averaged just 3% — we crushed them."},
            "spans": [{"id": "fab", "surface": "marketing", "text": "Peers averaged just 3%.", "facts_by_id": facts,
                       "numeric_claims": [{"emitted": "3%", "binding": {"kind": "unbound"},
                                           "context": {"surface": "marketing"}}]}]}


def generate(payload: dict) -> dict:
    title = (payload.get("title") or "Untitled").strip()
    facts = {}
    for i, r in enumerate(payload.get("facts", [])):
        if not (r.get("value") and r.get("metric")):
            continue
        fid = "f%d" % i
        facts[fid] = ledger.materialize_fact({
            "id": fid, "value": r["value"].strip(), "subject": (r.get("subject") or "").strip() or title,
            "metric": r["metric"].strip(), "period": (r.get("period") or "").strip(),
            "locatorText": (r.get("locator") or "").strip() or ("%s: %s" % (r["metric"].strip(), r["value"].strip()))})
    if not facts:
        return {"error": "Add at least one data row with a value and a metric."}

    formats = payload.get("formats") or ["post", "image", "video"]
    composer = _fab_composer if payload.get("fabricate") else None
    assets = studio.run(facts, title, formats=tuple(formats), post_composer=composer)

    out = []
    for a in assets:
        item = {"id": a.id, "format": a.format, "grounding": a.grounding, "shippable": a.shippable,
                "withheld": a.withheld, "spec": a.spec,
                "audit_md": render_audit_markdown(a.audit, title=a.spec.get("title", title)) if a.audit.get("summary", {}).get("total") else ""}
        try:
            if a.format == "image":
                item["svg"] = render_asset(a)
            elif a.format == "video":
                item["html"] = render_asset(a)
        except ValueError as e:
            item["render_refused"] = str(e)   # renderer refuses un-shippable → surface it honestly
        out.append(item)
    return {"title": title, "assets": out}


PAGE = r"""<!doctype html><html><head><meta charset=utf-8><title>fides — grounded content studio</title>
<style>
:root{--bg:#0b1220;--panel:#111a2e;--ink:#e9eef7;--muted:#8aa0c0;--accent:#38bdf8;--good:#34d399;--bad:#fb7185;--line:#22304d}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 Inter,Segoe UI,Helvetica,Arial,sans-serif}
header{padding:22px 28px;border-bottom:1px solid var(--line)}h1{margin:0;font-size:22px}
header .sub{color:var(--muted);font-size:13px;margin-top:4px}
.wrap{display:grid;grid-template-columns:380px 1fr;gap:0;min-height:calc(100vh - 74px)}
.left{padding:22px 24px;border-right:1px solid var(--line)}.right{padding:22px 28px}
label{display:block;color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.06em;margin:14px 0 6px}
input,select{width:100%;background:#0a1526;border:1px solid var(--line);color:var(--ink);border-radius:8px;padding:9px 10px;font-size:14px}
table{width:100%;border-collapse:collapse;margin-top:6px}td{padding:3px 3px}td input{padding:7px 8px;font-size:13px}
.rowbtn{background:none;border:none;color:var(--muted);cursor:pointer;font-size:18px;padding:0 4px}
button.primary{margin-top:18px;width:100%;background:var(--accent);color:#04121f;border:none;border-radius:10px;padding:12px;font-weight:700;font-size:15px;cursor:pointer}
button.ghost{margin-top:8px;width:100%;background:none;border:1px dashed var(--line);color:var(--muted);border-radius:8px;padding:8px;cursor:pointer}
.chk{display:flex;align-items:center;gap:8px;margin-top:14px;color:var(--muted)}.chk input{width:auto}
.card{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:16px 18px;margin-bottom:18px}
.card h3{margin:0 0 10px;font-size:13px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);display:flex;justify-content:space-between;align-items:center}
.badge{font-size:12px;font-weight:700;padding:3px 9px;border-radius:20px}
.ship{background:rgba(52,211,153,.15);color:var(--good)}.hold{background:rgba(251,113,133,.15);color:var(--bad)}
.post{font-size:16px;line-height:1.55}.svgwrap svg{max-width:100%;height:auto;border-radius:10px;border:1px solid var(--line)}
iframe{width:100%;height:340px;border:1px solid var(--line);border-radius:10px;background:#000}
details{margin-top:10px}summary{cursor:pointer;color:var(--muted);font-size:13px}
pre{white-space:pre-wrap;font:12px/1.5 ui-monospace,Menlo,monospace;color:#cdd8ea;background:#0a1526;padding:10px;border-radius:8px;overflow:auto}
.withheld{color:var(--bad);font-size:13px;margin-top:8px}.hint{color:var(--muted);font-size:13px}
.empty{color:var(--muted);text-align:center;margin-top:80px}
.presets{display:flex;flex-wrap:wrap;gap:8px;margin-top:6px}
.pill{background:#0a1526;border:1px solid var(--line);color:var(--ink);border-radius:20px;padding:6px 12px;font-size:12px;cursor:pointer}
.pill:hover{border-color:var(--accent);color:var(--accent)}
</style></head><body>
<header><h1>fides <span style="color:var(--muted);font-weight:400">grounded content studio</span></h1>
<div class=sub>Enter your data. Every number in every asset is verified against it — genuine kept, fabricated dropped.</div></header>
<div class=wrap>
 <div class=left>
  <label>Preset datasets (6 domains)</label><div class=presets id=presets></div>
  <label style="margin-top:16px">Title</label><input id=title value="Apex Growth — FY2024">
  <label>Source data (your facts)</label>
  <table id=rows></table>
  <button class=ghost onclick=addRow()>+ add data row</button>
  <label style="margin-top:18px">Formats</label>
  <div class=chk><input type=checkbox id=f_post checked><span>Post</span></div>
  <div class=chk><input type=checkbox id=f_image checked><span>Infographic (SVG)</span></div>
  <div class=chk><input type=checkbox id=f_video checked><span>Video storyboard (HTML)</span></div>
  <div class=chk><input type=checkbox id=fab><span>Inject a fabricated stat (watch it get dropped)</span></div>
  <button class=primary onclick=go()>Generate grounded assets</button>
  <div class=hint style="margin-top:12px">Deterministic path — no API key. An LLM ideator/composer would slot in where “fabricate” demonstrates.</div>
 </div>
 <div class=right id=out><div class=empty>Your grounded, verified assets will appear here.</div></div>
</div>
<script>
const PRESETS=/*PRESETS*/;
function addRow(v){v=v||["","","",""];const t=document.getElementById('rows');const tr=document.createElement('tr');
 tr.innerHTML=`<td><input placeholder=value value="${v[0]}"></td><td><input placeholder=subject value="${v[1]}"></td><td><input placeholder=metric value="${v[2]}"></td><td style=width:64px><input placeholder=period value="${v[3]}"></td><td><button class=rowbtn onclick="this.closest('tr').remove()">×</button></td>`;
 t.appendChild(tr);}
function loadPreset(i,run){const p=PRESETS[i];title.value=p.title;document.getElementById('rows').innerHTML='';p.rows.forEach(addRow);if(run)go();}
PRESETS.forEach((p,i)=>{const b=document.createElement('button');b.className='pill';b.textContent=p.title;b.onclick=()=>loadPreset(i,true);document.getElementById('presets').appendChild(b);});
loadPreset(0,false);
function esc(s){return (s||'').replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));}
async function go(){
 const facts=[...document.querySelectorAll('#rows tr')].map(tr=>{const i=tr.querySelectorAll('input');return {value:i[0].value,subject:i[1].value,metric:i[2].value,period:i[3].value};});
 const formats=[];if(f_post.checked)formats.push('post');if(f_image.checked)formats.push('image');if(f_video.checked)formats.push('video');
 const body={title:title.value,facts,formats,fabricate:fab.checked};
 document.getElementById('out').innerHTML='<div class=empty>Verifying…</div>';
 const r=await fetch('/api/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
 const d=await r.json();const out=document.getElementById('out');
 if(d.error){out.innerHTML='<div class=empty>'+esc(d.error)+'</div>';return;}
 out.innerHTML=d.assets.map(a=>{
  const badge=a.shippable?'<span class="badge ship">SHIPPABLE · '+Math.round(a.grounding*100)+'% grounded</span>':'<span class="badge hold">HELD · '+a.withheld.length+' dropped</span>';
  let inner='';
  if(a.format==='post') inner='<div class=post>'+esc(a.spec.text)+'</div>';
  else if(a.format==='image') inner='<div class=svgwrap>'+(a.svg||('<div class=withheld>'+esc(a.render_refused||'not rendered')+'</div>'))+'</div>';
  else if(a.format==='video') inner=a.html?('<iframe srcdoc="'+a.html.replace(/"/g,'&quot;')+'"></iframe>'):('<div class=withheld>'+esc(a.render_refused||'not rendered')+'</div>');
  const wh=a.withheld.length?'<div class=withheld>⊘ dropped fabricated span(s): '+a.withheld.join(', ')+'</div>':'';
  const audit=a.audit_md?('<details><summary>source-documentation audit</summary><pre>'+esc(a.audit_md)+'</pre></details>'):'';
  return '<div class=card><h3>'+a.format+' '+badge+'</h3>'+inner+wh+audit+'</div>';
 }).join('');
}
go();
</script></body></html>"""


class H(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        b = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._send(200, PAGE.replace("/*PRESETS*/", json.dumps(PRESETS)), "text/html")
        else:
            self._send(404, json.dumps({"error": "not found"}))

    def do_POST(self):
        if self.path != "/api/generate":
            return self._send(404, json.dumps({"error": "not found"}))
        try:
            n = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(n) or b"{}")
            self._send(200, json.dumps(generate(payload)))
        except Exception as e:  # never leak a stack to the browser; surface a clean message
            self._send(200, json.dumps({"error": "%s: %s" % (type(e).__name__, e)}))

    def log_message(self, *a):  # quiet
        pass


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    print("fides studio UI  →  http://localhost:%d   (Ctrl-C to stop)" % port)
    ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
