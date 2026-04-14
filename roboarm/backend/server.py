"""
BAURSAK ARM — Main Server

FastAPI application serving web UI and API endpoints.
Runs on Raspberry Pi, communicates with ESP32 via Serial.

Pages:
  /          — Main menu
  /modes     — Built-in + custom modes
  /manual    — Real-time slider control
  /custom    — Create new mode with pose editor
  /record    — Record poses from sliders
  /loop      — Loop any mode
  /edit?i=N  — Edit existing custom mode

API:
  /api/pos           — GET current positions
  /api/set?c=&v=     — SET manual channel
  /api/pair?v=        — SET CH5+6 pair
  /api/go?v=          — RUN built-in mode
  /api/run_saved?i=   — RUN custom mode
  /api/custom         — POST test sequence
  /api/save_mode      — POST save new mode
  /api/update_mode    — POST update existing mode
  /api/delete_mode?i= — DELETE mode
  /api/loop           — GET loop mode
  /api/stop           — GET stop loop
"""

import time
import json
import threading
import secrets
from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
import uvicorn

from config import (
    WEB_HOST, WEB_PORT, PASSWORD, POSE_PAUSE as D,
    clamp_ch, CH_MIN, CH_MAX
)
from motion import MotionController
from poses import INIT
from sequences import run_v
from storage import load_saved_modes, save_modes_to_file, log_mode

# =============================================================
#  Initialize
# =============================================================
mc = MotionController()
saved_modes = load_saved_modes()
stop_loop = False

# =============================================================
#  Custom mode runner
# =============================================================
def run_saved(index: int):
    """Execute a saved custom mode by index."""
    if index < 0 or index >= len(saved_modes):
        return
    mode = saved_modes[index]
    with mc.lock:
        mc.sequence_running = True
    try:
        for p in mode.get("poses", []):
            pose = [
                clamp_ch(1, p.get("c1", 90)),
                p.get("c2", 90),
                p.get("c3", 90),
                p.get("c4", 90),
                0,
                p.get("c6", 90),
                clamp_ch(7, p.get("c7", 90))
            ]
            mc.run_pose(
                pose,
                mode="sequential" if p.get("mode", "p") == "s" else "parallel",
                speed=p.get("speed", 60)
            )
            time.sleep(0.15)
        mc.smooth_move(INIT)
        time.sleep(D)
    finally:
        mc.finish_sequence()

# =============================================================
#  FastAPI + Auth
# =============================================================
app = FastAPI(title="Baursak Arm", docs_url=None, redoc_url=None)
valid_tokens = set()

@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path
    if path in ("/login", "/auth") or path.startswith("/favicon"):
        return await call_next(request)
    if request.cookies.get("token", "") not in valid_tokens:
        return RedirectResponse("/login")
    return await call_next(request)

# =============================================================
#  HTML Pages (inline for ESP32-friendly single-file deploy)
# =============================================================

LOGIN = """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<style>*{margin:0;padding:0;box-sizing:border-box}body{font-family:monospace;background:#0a0a0a;color:#eee;display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:100vh;gap:16px}h1{color:#f80}input{background:#222;border:2px solid #444;color:#0f0;font-family:monospace;font-size:18px;padding:12px;text-align:center;border-radius:6px;width:240px}button{padding:12px 32px;font-family:monospace;font-size:16px;border:2px solid #f80;background:#1a1a1a;color:#f80;cursor:pointer;border-radius:6px}#err{color:#f44;font-size:13px;min-height:20px}</style></head><body>
<h1>BAURSAK ARM</h1><input type="password" id="pw" placeholder="password" onkeydown="if(event.key==='Enter')login()"><button onclick="login()">LOGIN</button><div id="err"></div>
<script>function login(){fetch('/auth?p='+encodeURIComponent(document.getElementById('pw').value)).then(r=>r.json()).then(d=>{if(d.ok)location.href='/';else document.getElementById('err').textContent='wrong';});}</script></body></html>"""

MENU = """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<style>*{margin:0;padding:0;box-sizing:border-box}body{font-family:monospace;background:#0a0a0a;color:#eee;display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:100vh;gap:16px;padding:20px}h1{color:#f80}a{display:block;width:260px;padding:16px;text-align:center;border:2px solid #f80;color:#f80;text-decoration:none;border-radius:8px;font-size:16px;font-family:monospace}a:active{background:#f80;color:#000}</style></head><body>
<h1>BAURSAK ARM</h1><a href="/modes">MODES</a><a href="/manual">MANUAL</a><a href="/custom">CREATE MODE</a><a href="/record">RECORD</a><a href="/loop">LOOP</a><a href="/logout">LOGOUT</a></body></html>"""

MANUAL = """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<style>*{margin:0;padding:0;box-sizing:border-box}body{font-family:monospace;background:#0a0a0a;color:#eee;padding:16px}a{color:#f80;font-size:13px}h1{text-align:center;color:#0f0;font-size:18px;margin:8px 0}.r{display:flex;align-items:center;gap:8px;margin:6px 0}.r label{width:70px;font-size:13px;color:#aaa}.r input{flex:1;height:24px;accent-color:#0f0}.r span{width:36px;text-align:right;font-size:13px;color:#0f0}</style></head><body>
<a href="/">← MENU</a><h1>MANUAL</h1>
<div class="r"><label>CH1 grip</label><input type="range" min="80" max="180" value="90" id="s1" oninput="s(1)"><span id="v1">-</span></div>
<div class="r"><label>CH2 wrist</label><input type="range" min="0" max="180" value="90" id="s2" oninput="s(2)"><span id="v2">-</span></div>
<div class="r"><label>CH3 rot</label><input type="range" min="0" max="180" value="90" id="s3" oninput="s(3)"><span id="v3">-</span></div>
<div class="r"><label>CH4 elbow</label><input type="range" min="0" max="180" value="90" id="s4" oninput="s(4)"><span id="v4">-</span></div>
<div class="r"><label>CH5+6</label><input type="range" min="0" max="180" value="90" id="s6" oninput="s(6)"><span id="v6">-</span></div>
<div class="r"><label>CH7 base</label><input type="range" min="-30" max="220" value="90" id="s7" oninput="s(7)"><span id="v7">-</span></div>
<script>var pend={};var tid=null;
function s(c){var v=document.getElementById('s'+c).value;document.getElementById('v'+c).textContent=v;pend[c]=v;if(!tid)tid=setTimeout(flush,40);}
function flush(){var p={...pend};pend={};tid=null;for(var c in p){if(c=='6')fetch('/api/pair?v='+p[c]);else fetch('/api/set?c='+c+'&v='+p[c]);}}
fetch('/api/pos').then(r=>r.json()).then(d=>{[1,2,3,4,7].forEach(c=>{document.getElementById('s'+c).value=d[c];document.getElementById('v'+c).textContent=d[c];});document.getElementById('s6').value=d[6];document.getElementById('v6').textContent=d[6];});
</script></body></html>"""

CUSTOM = """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<style>*{margin:0;padding:0;box-sizing:border-box}body{font-family:monospace;background:#0a0a0a;color:#eee;padding:16px}a{color:#f80;font-size:13px}h1{text-align:center;color:#f80;font-size:18px;margin:8px 0 12px}.pose{background:#161616;border:1px solid #333;border-radius:6px;padding:10px;margin:4px 0}.head{display:flex;justify-content:space-between;align-items:center;margin-bottom:4px}.head span{color:#f80;font-size:13px}.head button{background:none;border:1px solid #600;color:#f66;font-family:monospace;padding:2px 6px;cursor:pointer;border-radius:3px;font-size:11px}.row{display:flex;gap:4px;margin:2px 0;align-items:center}.row label{width:50px;font-size:11px;color:#888}.row input[type=number]{width:46px;background:#222;border:1px solid #444;color:#0f0;font-family:monospace;font-size:12px;padding:1px 3px;text-align:center;border-radius:3px}.popts{display:flex;gap:6px;margin-top:4px;align-items:center;flex-wrap:wrap}.popts label{font-size:10px;color:#666}.popts select,.popts input[type=number]{background:#222;border:1px solid #444;color:#0f0;font-family:monospace;font-size:11px;padding:1px 2px;border-radius:3px}.ins{text-align:center;margin:1px 0}.ins button{background:none;border:1px dashed #333;color:#444;font-family:monospace;padding:1px 10px;cursor:pointer;border-radius:3px;font-size:10px}.ins button:hover{border-color:#0f0;color:#0f0}.top{background:#161616;border:1px solid #333;border-radius:6px;padding:8px;margin:6px 0}.top label{font-size:12px;color:#888;margin-right:4px}.top input{background:#222;border:1px solid #444;color:#0f0;font-family:monospace;font-size:13px;padding:2px 4px;border-radius:3px}.btns{display:flex;gap:8px;margin:10px 0;justify-content:center;flex-wrap:wrap}.btns button{padding:10px 14px;font-family:monospace;font-size:13px;border:2px solid #0f0;background:#1a1a1a;color:#0f0;cursor:pointer;border-radius:6px}.btns .run{border-color:#f80;color:#f80}.btns .save{border-color:#0ff;color:#0ff}#st{text-align:center;font-size:12px;color:#888}</style></head><body>
<a href="/">← MENU</a><h1>CREATE MODE</h1>
<div class="top"><label>Name:</label><input type="text" id="fname" placeholder="my mode" style="width:130px"></div>
<div id="poses"></div>
<div class="btns"><button onclick="addPose(-1)">+ ADD</button><button class="run" onclick="testAll()">TEST</button><button class="save" onclick="saveMode()">SAVE</button></div>
<div id="st">add → test → save</div>
<script>var P=[];
function def_(){return{c1:90,c2:90,c3:90,c4:90,c6:90,c7:90,speed:60,mode:'p'};}
function copyLast(){if(P.length>0){var l=P[P.length-1];return{c1:l.c1,c2:l.c2,c3:l.c3,c4:l.c4,c6:l.c6,c7:l.c7,speed:l.speed,mode:l.mode};}return def_();}
function copyAt(i){var l=P[i];return{c1:l.c1,c2:l.c2,c3:l.c3,c4:l.c4,c6:l.c6,c7:l.c7,speed:l.speed,mode:l.mode};}
function render(){var h='';for(var i=0;i<P.length;i++){
h+='<div class="ins"><button onclick="addPose('+i+')">+ insert</button></div>';
h+='<div class="pose"><div class="head"><span>POSE '+(i+1)+'</span><button onclick="del('+i+')">✕</button></div>';
var ch=[['CH1',80,180],['CH2',0,180],['CH3',0,180],['CH4',0,180],['CH5+6',0,180],['CH7',-30,220]];var k=['c1','c2','c3','c4','c6','c7'];
for(var j=0;j<6;j++){h+='<div class="row"><label>'+ch[j][0]+'</label><input type="number" min="'+ch[j][1]+'" max="'+ch[j][2]+'" value="'+P[i][k[j]]+'" onchange="P['+i+'].'+k[j]+'=+this.value"></div>';}
h+='<div class="popts"><label>spd:</label><input type="number" min="10" max="200" value="'+P[i].speed+'" style="width:40px" onchange="P['+i+'].speed=+this.value"><label>°/s</label> <select onchange="P['+i+'].mode=this.value"><option value="p"'+(P[i].mode=='p'?' selected':'')+'>par</option><option value="s"'+(P[i].mode=='s'?' selected':'')+'>seq</option></select></div></div>';}
h+='<div class="ins"><button onclick="addPose(-1)">+ end</button></div>';document.getElementById('poses').innerHTML=h;}
function addPose(at){if(at==-1)P.push(copyLast());else P.splice(at,0,copyAt(at));render();}
function del(i){P.splice(i,1);render();}
function testAll(){if(!P.length)return;document.getElementById('st').textContent='testing...';fetch('/api/custom',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({poses:P})}).then(r=>r.text()).then(t=>{document.getElementById('st').textContent='done';});}
function saveMode(){if(!P.length){document.getElementById('st').textContent='add poses';return;}var n=document.getElementById('fname').value.trim();if(!n){document.getElementById('st').textContent='name!';return;}document.getElementById('st').textContent='saving...';fetch('/api/save_mode',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:n,poses:P.map(p=>({...p}))})}).then(r=>r.json()).then(t=>{document.getElementById('st').textContent='saved → MODES';});}
P.push(def_());render();</script></body></html>"""

RECORD = """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<style>*{margin:0;padding:0;box-sizing:border-box}body{font-family:monospace;background:#0a0a0a;color:#eee;padding:16px}a{color:#f80;font-size:13px}h1{text-align:center;color:#0f0;font-size:18px;margin:8px 0}.r{display:flex;align-items:center;gap:8px;margin:6px 0}.r label{width:70px;font-size:13px;color:#aaa}.r input{flex:1;height:24px;accent-color:#0f0}.r span{width:36px;text-align:right;font-size:13px;color:#0f0}.btns{display:flex;gap:6px;margin:10px 0;justify-content:center;flex-wrap:wrap}.btns button{padding:8px 12px;font-family:monospace;font-size:12px;border:2px solid #0f0;background:#1a1a1a;color:#0f0;cursor:pointer;border-radius:6px}.btns .play{border-color:#f80;color:#f80}.btns .sv{border-color:#0ff;color:#0ff}.nm{display:flex;gap:8px;align-items:center;justify-content:center;margin:8px 0}.nm label{font-size:12px;color:#888}.nm input{background:#222;border:1px solid #444;color:#0f0;font-family:monospace;padding:4px;border-radius:3px;width:120px}#log{background:#111;border:1px solid #333;padding:8px;font-size:11px;color:#0f0;max-height:200px;overflow-y:auto;margin:8px 0;border-radius:4px}#st{text-align:center;font-size:12px;color:#888}</style></head><body>
<a href="/">← MENU</a><h1>RECORD</h1>
<div class="r"><label>CH1</label><input type="range" min="80" max="180" value="90" id="s1" oninput="s(1)"><span id="v1">90</span></div>
<div class="r"><label>CH2</label><input type="range" min="0" max="180" value="90" id="s2" oninput="s(2)"><span id="v2">90</span></div>
<div class="r"><label>CH3</label><input type="range" min="0" max="180" value="90" id="s3" oninput="s(3)"><span id="v3">90</span></div>
<div class="r"><label>CH4</label><input type="range" min="0" max="180" value="90" id="s4" oninput="s(4)"><span id="v4">90</span></div>
<div class="r"><label>CH5+6</label><input type="range" min="0" max="180" value="90" id="s6" oninput="s(6)"><span id="v6">90</span></div>
<div class="r"><label>CH7</label><input type="range" min="-30" max="220" value="90" id="s7" oninput="s(7)"><span id="v7">90</span></div>
<div class="nm"><label>Name:</label><input type="text" id="fname" placeholder="name"></div>
<div class="btns"><button onclick="sv()">SAVE POSE</button><button onclick="clr()">CLEAR</button><button class="play" onclick="play()">PLAY</button><button class="sv" onclick="saveMode()">→ MODES</button></div>
<div id="st">move → save → play</div><div id="log"></div>
<script>var pend={};var tid=null;var saved=[];
function s(c){var v=document.getElementById('s'+c).value;document.getElementById('v'+c).textContent=v;pend[c]=v;if(!tid)tid=setTimeout(flush,40);}
function flush(){var p={...pend};pend={};tid=null;for(var c in p){if(c=='6')fetch('/api/pair?v='+p[c]);else fetch('/api/set?c='+c+'&v='+p[c]);}}
function sv(){var p={c1:+document.getElementById('s1').value,c2:+document.getElementById('s2').value,c3:+document.getElementById('s3').value,c4:+document.getElementById('s4').value,c6:+document.getElementById('s6').value,c7:+document.getElementById('s7').value,speed:60,mode:'p'};saved.push(p);document.getElementById('log').innerHTML+='<div>P'+saved.length+': '+JSON.stringify(p)+'</div>';document.getElementById('st').textContent=saved.length+' saved';}
function clr(){saved=[];document.getElementById('log').innerHTML='';document.getElementById('st').textContent='cleared';}
function play(){if(!saved.length)return;document.getElementById('st').textContent='playing...';fetch('/api/custom',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({poses:saved})}).then(r=>r.text()).then(t=>{document.getElementById('st').textContent='done';});}
function saveMode(){if(!saved.length){document.getElementById('st').textContent='record first';return;}var n=document.getElementById('fname').value.trim();if(!n){document.getElementById('st').textContent='name!';return;}fetch('/api/save_mode',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:n,poses:saved})}).then(r=>r.json()).then(t=>{document.getElementById('st').textContent='saved!';});}
fetch('/api/pos').then(r=>r.json()).then(d=>{[1,2,3,4,7].forEach(c=>{document.getElementById('s'+c).value=d[c];document.getElementById('v'+c).textContent=d[c];});document.getElementById('s6').value=d[6];document.getElementById('v6').textContent=d[6];});
</script></body></html>"""

LOOP = """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<style>*{margin:0;padding:0;box-sizing:border-box}body{font-family:monospace;background:#0a0a0a;color:#eee;padding:16px;display:flex;flex-direction:column;align-items:center;gap:12px}a{color:#f80;font-size:13px}h1{font-size:18px;color:#f80}.opts{background:#161616;border:1px solid #333;border-radius:6px;padding:10px;width:100%;max-width:400px}.opts label{font-size:12px;color:#888;margin-right:6px}.opts select,.opts input{background:#222;border:1px solid #444;color:#0f0;font-family:monospace;font-size:13px;padding:2px 4px;border-radius:3px}button{padding:12px 24px;font-family:monospace;font-size:16px;border:2px solid #f80;background:#1a1a1a;color:#f80;cursor:pointer;border-radius:6px;margin:4px}#st{font-size:14px;color:#888}</style></head><body>
<a href="/">← MENU</a><h1>LOOP</h1>
<div class="opts"><label>Mode:</label><select id="mv">""" + "".join(f'<option value="{i}">V{i}</option>' for i in range(1,11)) + """</select><label>x</label><input type="number" id="rep" value="3" min="1" max="50" style="width:40px"><label>pause:</label><input type="number" id="pau" value="2" min="0" max="30" style="width:40px">s</div>
<button onclick="start()">START</button><button onclick="stp()">STOP</button><div id="st">ready</div>
<script>function start(){document.getElementById('st').textContent='looping...';fetch('/api/loop?v='+document.getElementById('mv').value+'&r='+document.getElementById('rep').value+'&p='+document.getElementById('pau').value).then(r=>r.text()).then(t=>{document.getElementById('st').textContent='done';});}function stp(){fetch('/api/stop');}</script></body></html>"""


def build_modes_html():
    bi = "".join(f'<button onclick="go({i})">V{i}</button>' for i in range(1, 11))
    cb = "".join(
        f'<button onclick="goC({i})" style="border-color:#0ff;color:#0ff">'
        f'{m.get("name","?")} ({len(m.get("poses",[]))}p)</button>'
        for i, m in enumerate(saved_modes)
    )
    eb = "".join(
        f'<button onclick="edit({i})" style="border-color:#ff0;color:#ff0;font-size:11px;padding:8px">✎ {m.get("name","?")}</button>'
        f'<button onclick="del_({i})" style="border-color:#600;color:#f66;font-size:11px;padding:8px">✕ {m.get("name","?")}</button>'
        for i, m in enumerate(saved_modes)
    )
    return f"""<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<style>*{{margin:0;padding:0;box-sizing:border-box}}body{{font-family:monospace;background:#0a0a0a;color:#eee;padding:16px;display:flex;flex-direction:column;align-items:center;gap:10px}}h1{{font-size:18px;color:#f80}}h2{{font-size:13px;color:#888;margin-top:6px}}.g{{display:grid;grid-template-columns:1fr 1fr;gap:6px;width:100%;max-width:400px}}button{{padding:12px 8px;font-family:monospace;font-size:12px;border:2px solid #f80;background:#1a1a1a;color:#f80;cursor:pointer;border-radius:6px}}button.off{{border-color:#333;color:#333}}#st{{font-size:13px;color:#888}}a{{color:#f80;font-size:13px}}</style></head><body>
<a href="/">← MENU</a><h1>MODES</h1><div id="st">pick</div>
<h2>BUILT-IN</h2><div class="g">{bi}</div>
{"<h2>CUSTOM</h2><div class='g'>"+cb+"</div>" if cb else ""}
{"<h2>MANAGE</h2><div class='g'>"+eb+"</div>" if eb else ""}
<script>
function go(n){{dis();document.getElementById('st').textContent='V'+n+'...';fetch('/api/go?v='+n).then(r=>r.text()).then(t=>{{en();document.getElementById('st').textContent='done';}});}}
function goC(i){{dis();document.getElementById('st').textContent='running...';fetch('/api/run_saved?i='+i).then(r=>r.text()).then(t=>{{en();document.getElementById('st').textContent='done';}});}}
function edit(i){{location.href='/edit?i='+i;}}
function del_(i){{var r=prompt('Type DELETE to confirm');if(r!=='DELETE')return;fetch('/api/delete_mode?i='+i).then(r=>r.text()).then(t=>{{location.reload();}});}}
function dis(){{document.querySelectorAll('button').forEach(b=>b.classList.add('off'));}}
function en(){{document.querySelectorAll('button').forEach(b=>b.classList.remove('off'));}}
</script></body></html>"""


def build_edit_html(index):
    if index < 0 or index >= len(saved_modes):
        return "<h1>not found</h1>"
    m = saved_modes[index]
    return f"""<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<style>*{{margin:0;padding:0;box-sizing:border-box}}body{{font-family:monospace;background:#0a0a0a;color:#eee;padding:16px}}a{{color:#f80;font-size:13px}}h1{{text-align:center;color:#ff0;font-size:18px;margin:8px 0 12px}}.pose{{background:#161616;border:1px solid #333;border-radius:6px;padding:10px;margin:4px 0}}.head{{display:flex;justify-content:space-between;align-items:center;margin-bottom:4px}}.head span{{color:#f80;font-size:13px}}.head button{{background:none;border:1px solid #600;color:#f66;font-family:monospace;padding:2px 6px;cursor:pointer;border-radius:3px;font-size:11px}}.row{{display:flex;gap:4px;margin:2px 0;align-items:center}}.row label{{width:50px;font-size:11px;color:#888}}.row input[type=number]{{width:46px;background:#222;border:1px solid #444;color:#0f0;font-family:monospace;font-size:12px;padding:1px 3px;text-align:center;border-radius:3px}}.popts{{display:flex;gap:6px;margin-top:4px;align-items:center;flex-wrap:wrap}}.popts label{{font-size:10px;color:#666}}.popts select,.popts input[type=number]{{background:#222;border:1px solid #444;color:#0f0;font-family:monospace;font-size:11px;padding:1px 2px;border-radius:3px}}.ins{{text-align:center;margin:1px 0}}.ins button{{background:none;border:1px dashed #333;color:#444;font-family:monospace;padding:1px 10px;cursor:pointer;border-radius:3px;font-size:10px}}.top{{background:#161616;border:1px solid #333;border-radius:6px;padding:8px;margin:6px 0}}.top label{{font-size:12px;color:#888;margin-right:4px}}.top input{{background:#222;border:1px solid #444;color:#0f0;font-family:monospace;font-size:13px;padding:2px 4px;border-radius:3px}}.btns{{display:flex;gap:8px;margin:10px 0;justify-content:center;flex-wrap:wrap}}.btns button{{padding:10px 14px;font-family:monospace;font-size:13px;border:2px solid #ff0;background:#1a1a1a;color:#ff0;cursor:pointer;border-radius:6px}}.btns .run{{border-color:#f80;color:#f80}}#st{{text-align:center;font-size:12px;color:#888}}</style></head><body>
<a href="/modes">← MODES</a><h1>EDIT: {m.get('name','')}</h1>
<div class="top"><label>Name:</label><input type="text" id="fname" value="{m.get('name','')}" style="width:130px"></div>
<div id="poses"></div>
<div class="btns"><button onclick="addPose(-1)">+ ADD</button><button class="run" onclick="testAll()">TEST</button><button onclick="sv()">SAVE</button></div>
<div id="st">edit → test → save</div>
<script>var P={json.dumps(m.get('poses',[]))};var IDX={index};
for(var i=0;i<P.length;i++){{if(!P[i].speed)P[i].speed=60;if(!P[i].mode)P[i].mode='p';}}
function copyAt(i){{var l=P[i];return{{c1:l.c1,c2:l.c2,c3:l.c3,c4:l.c4,c6:l.c6,c7:l.c7,speed:l.speed||60,mode:l.mode||'p'}};}}
function copyLast(){{if(P.length)return copyAt(P.length-1);return{{c1:90,c2:90,c3:90,c4:90,c6:90,c7:90,speed:60,mode:'p'}};}}
function render(){{var h='';for(var i=0;i<P.length;i++){{
h+='<div class="ins"><button onclick="addPose('+i+')">+ insert</button></div>';
h+='<div class="pose"><div class="head"><span>P'+(i+1)+'</span><button onclick="del('+i+')">✕</button></div>';
var ch=[['CH1',80,180],['CH2',0,180],['CH3',0,180],['CH4',0,180],['CH5+6',0,180],['CH7',-30,220]];var k=['c1','c2','c3','c4','c6','c7'];
for(var j=0;j<6;j++){{h+='<div class="row"><label>'+ch[j][0]+'</label><input type="number" min="'+ch[j][1]+'" max="'+ch[j][2]+'" value="'+(P[i][k[j]]||90)+'" onchange="P['+i+'].'+k[j]+'=+this.value"></div>';}}
h+='<div class="popts"><label>spd:</label><input type="number" min="10" max="200" value="'+(P[i].speed||60)+'" style="width:40px" onchange="P['+i+'].speed=+this.value"> <select onchange="P['+i+'].mode=this.value"><option value="p"'+((P[i].mode||'p')=='p'?' selected':'')+'>par</option><option value="s"'+((P[i].mode||'p')=='s'?' selected':'')+'>seq</option></select></div></div>';}}
h+='<div class="ins"><button onclick="addPose(-1)">+ end</button></div>';document.getElementById('poses').innerHTML=h;}}
function addPose(at){{if(at==-1)P.push(copyLast());else P.splice(at,0,copyAt(at));render();}}
function del(i){{P.splice(i,1);render();}}
function testAll(){{if(!P.length)return;document.getElementById('st').textContent='testing...';fetch('/api/custom',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{poses:P}})}}).then(r=>r.text()).then(t=>{{document.getElementById('st').textContent='done';}});}}
function sv(){{var n=document.getElementById('fname').value.trim();if(!n){{document.getElementById('st').textContent='name!';return;}}document.getElementById('st').textContent='saving...';fetch('/api/update_mode',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{index:IDX,name:n,poses:P.map(p=>({{...p}}))}})
}}).then(r=>r.json()).then(t=>{{document.getElementById('st').textContent='saved!';setTimeout(()=>location.href='/modes',500);}});}}
render();</script></body></html>"""


# =============================================================
#  Routes
# =============================================================

@app.get("/auth")
def auth(p: str = ""):
    if p == PASSWORD:
        token = secrets.token_hex(16)
        valid_tokens.add(token)
        resp = Response(content='{"ok":true}', media_type="application/json")
        resp.set_cookie("token", token, httponly=True, max_age=86400)
        return resp
    return {"ok": False}

@app.get("/login", response_class=HTMLResponse)
def login_page():
    return LOGIN

@app.get("/logout")
def logout(req: Request):
    valid_tokens.discard(req.cookies.get("token", ""))
    resp = RedirectResponse("/login")
    resp.delete_cookie("token")
    return resp

@app.get("/", response_class=HTMLResponse)
def menu():
    return MENU

@app.get("/modes", response_class=HTMLResponse)
def modes():
    return HTMLResponse(build_modes_html())

@app.get("/manual", response_class=HTMLResponse)
def manual():
    return MANUAL

@app.get("/custom", response_class=HTMLResponse)
def custom():
    return CUSTOM

@app.get("/record", response_class=HTMLResponse)
def record():
    return RECORD

@app.get("/loop", response_class=HTMLResponse)
def loop_page():
    return LOOP

@app.get("/edit", response_class=HTMLResponse)
def edit_page(i: int = 0):
    return HTMLResponse(build_edit_html(i))


# --- API ---

@app.get("/api/pos")
def api_pos():
    return mc.get_positions()

@app.get("/api/set")
def api_set(c: int = 1, v: int = 90):
    mc.set_manual(c, clamp_ch(c, v))
    return {"ok": True}

@app.get("/api/pair")
def api_pair(v: int = 90):
    mc.set_manual_pair(v)
    return {"ok": True}

@app.get("/api/go")
def api_go(v: int = 1):
    if mc.sequence_running:
        return {"status": "busy"}
    run_v(mc, v)
    return {"status": "done"}

@app.get("/api/run_saved")
def api_run_saved(i: int = 0):
    if mc.sequence_running:
        return {"status": "busy"}
    run_saved(i)
    return {"status": "done"}

@app.post("/api/custom")
def api_custom(data: dict):
    if mc.sequence_running:
        return {"status": "busy"}
    with mc.lock:
        mc.sequence_running = True
    try:
        for p in data.get("poses", []):
            pose = [
                clamp_ch(1, p.get("c1", 90)),
                p.get("c2", 90), p.get("c3", 90), p.get("c4", 90),
                0, p.get("c6", 90),
                clamp_ch(7, p.get("c7", 90))
            ]
            mc.run_pose(
                pose,
                mode="sequential" if p.get("mode", "p") == "s" else "parallel",
                speed=p.get("speed", 60)
            )
            time.sleep(0.15)
    finally:
        mc.finish_sequence()
    return {"status": "done"}

@app.post("/api/save_mode")
def api_save_mode(data: dict):
    global saved_modes
    saved_modes.append(data)
    save_modes_to_file(saved_modes)
    log_mode(data, "SAVED")
    return {"status": "saved", "count": len(saved_modes)}

@app.post("/api/update_mode")
def api_update_mode(data: dict):
    global saved_modes
    idx = data.get("index", -1)
    if 0 <= idx < len(saved_modes):
        saved_modes[idx] = {"name": data.get("name", ""), "poses": data.get("poses", [])}
        save_modes_to_file(saved_modes)
        log_mode(saved_modes[idx], "UPDATED")
    return {"status": "updated"}

@app.get("/api/delete_mode")
def api_delete_mode(i: int = 0):
    global saved_modes
    if 0 <= i < len(saved_modes):
        d = saved_modes.pop(i)
        save_modes_to_file(saved_modes)
        log_mode(d, "DELETED")
    return {"status": "deleted"}

@app.get("/api/loop")
def api_loop(v: int = 3, r: int = 3, p: int = 2):
    global stop_loop
    if mc.sequence_running:
        return {"status": "busy"}
    stop_loop = False
    for i in range(r):
        if stop_loop:
            break
        run_v(mc, v)
        if stop_loop:
            break
        time.sleep(p)
    return {"status": "done"}

@app.get("/api/stop")
def api_stop():
    global stop_loop
    stop_loop = True
    return {"status": "stopping"}


# =============================================================
#  Startup
# =============================================================
if __name__ == "__main__":
    mc.init_pose(INIT)
    time.sleep(0.5)
    print(f"BAURSAK ARM ready. {len(saved_modes)} custom modes loaded.")
    print(f"http://{WEB_HOST}:{WEB_PORT}")
    uvicorn.run(app, host=WEB_HOST, port=WEB_PORT)
