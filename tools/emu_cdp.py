# I-A517 Strumento di volo · © 2026 Enrico D'Amico · Tutti i diritti riservati.
# Copia, modifica e distribuzione solo con permesso scritto dell'autore (vedi il file LICENSE).
"""Collaudo sull'emulatore: entra nella WebView dell'app (DevTools via adb), la usa come un pilota,
salva schermate e risultati in out/. Uso: python3 emu_cdp.py out"""
import json, os, re, subprocess, sys, time
import urllib.request
import websocket  # websocket-client

OUT = sys.argv[1] if len(sys.argv) > 1 else "out"
PKG = "it.ia517.strumento"
os.makedirs(OUT, exist_ok=True)
res = []


def adb(*a, check=False):
    r = subprocess.run(["adb", *a], capture_output=True, text=True, timeout=60)
    return r.stdout.strip()


def shot(name):
    with open(f"{OUT}/{name}.png", "wb") as f:
        f.write(subprocess.run(["adb", "exec-out", "screencap", "-p"], capture_output=True, timeout=60).stdout)


def alive():
    return adb("shell", "pidof", PKG) != ""


def log(k, v):
    res.append([k, v]); print(f"{k:28s} {v}", flush=True)


def connect():
    for _ in range(40):
        socks = re.findall(r"@(webview_devtools_remote_\d+)", adb("shell", "cat", "/proc/net/unix"))
        if socks:
            adb("forward", "tcp:9222", f"localabstract:{socks[-1]}")
            try:
                pages = json.load(urllib.request.urlopen("http://127.0.0.1:9222/json", timeout=5))
                pg = [p for p in pages if p.get("type") == "page" and "localhost" in p.get("url", "")]
                if pg:
                    return websocket.create_connection(pg[0]["webSocketDebuggerUrl"], timeout=30, suppress_origin=True)
            except Exception as e:
                print("devtools:", e)
        time.sleep(2)
    return None


ws = None
mid = 0


def ev(expr, wait=True):
    global mid, ws
    mid += 1
    try:
        ws.send(json.dumps({"id": mid, "method": "Runtime.evaluate", "params": {"expression": expr, "returnByValue": True, "awaitPromise": wait}}))
        while True:
            m = json.loads(ws.recv())
            if m.get("id") == mid:
                r = m.get("result", {})
                if "exceptionDetails" in r:
                    return "ECCEZIONE: " + json.dumps(r["exceptionDetails"].get("exception", {}).get("description", r["exceptionDetails"]))[:400]
                return r.get("result", {}).get("value")
    except Exception as e:
        return f"(nessuna risposta: {e})"


def step(name, expr=None, pause=3):
    v = ev(expr) if expr else None
    time.sleep(pause)
    shot(name)
    log(name, v if v is not None else "")
    log(name + " · app viva", alive())


time.sleep(5)
ws = connect()
log("devtools collegati", ws is not None)
if ws:
    ev("window.__err=[];addEventListener('error',e=>__err.push(String(e.message)+' @'+(e.filename||'').split('/').pop()+':'+e.lineno));addEventListener('unhandledrejection',e=>__err.push('promise: '+String(e.reason&&e.reason.message||e.reason)));1")
    step("01_avvio", "JSON.stringify({ver:window.IA517_BUILD, termini:!!document.getElementById('phTerms'), native:!!(window.IA517&&IA517.native), dpr:devicePixelRatio, w:innerWidth, h:innerHeight})")
    step("02_accetto", "(()=>{const c=document.getElementById('phTermsOk'); if(!c) return 'già accettate'; c.click(); document.getElementById('phTermsGo').click(); return 'ok';})()")
    time.sleep(20)
    step("03_volo_gps", "JSON.stringify({fix:PH.lastFix||null, err:__err})", pause=2)
    step("04_impostazioni", "PH.show('imp'),'ok'")
    step("05_piano", "PH.show('piano'),'ok'", pause=8)
    step("06_info", "PH.show('info'),'ok'", pause=4)
    step("07_volo", "PH.show('volo'),'ok'")
    # cambi di pagina come li fa il pilota: tocco lungo sullo strumento (il dito scivola un po'), poi il pulsante PAGINA
    ev("window.__gap=0;window.__lt=0;(function f(t){ if(__lt&&t-__lt>__gap) __gap=t-__lt; __lt=t; requestAnimationFrame(f); })(performance.now());1")
    rc=json.loads(ev("JSON.stringify((()=>{const r=document.getElementById('pfd').getBoundingClientRect();return [r.x+r.width/2,r.y+r.height/2,devicePixelRatio]})())"))
    x,y=int(rc[0]*rc[2]),int(rc[1]*rc[2])
    for i in range(6):
        if i%2==0: adb("shell","input","swipe",str(x),str(y),str(x),str(y),"1100")      # tocco lungo fermo
        else:      adb("shell","input","swipe",str(x),str(y),str(x+4),str(y+3),"2200")  # tocco lungo, poi il dito scivola a fine pressione
        time.sleep(3)
        log(f"tocco lungo {i+1}", [ev("PAGE"), ev("ZOOMS[zi]"), alive(), round(ev("__gap") or 0)])
        if i in (0,3): shot(f"07{'ab'[i//3]}_pagina_{ev('PAGE')}")
    for i in range(6):
        ev("document.getElementById('phPage').click(),1"); time.sleep(2)
        log(f"pulsante PAGINA {i+1}", [ev("PAGE"), alive(), round(ev("__gap") or 0)])
    log("scatola nera", ev("JSON.stringify(PH.trail.slice(-12))"))
    log("prestazioni", ev("JSON.stringify({ms:PH.perf.avg.toFixed(1),blocchi:PH.perf.stalls,fps:PH.fps,vicini:PH.nearF&&PH.nearF.length,terreno:PH.dem.size,tessere:PH.tiles.size})"))
    step("08_demo", "(typeof PH.setDemo==='function'?(PH.setDemo(true),'demo'):'manca setDemo')", pause=25)
    log("errori JS", ev("JSON.stringify(__err)"))
    log("errori app", ev("JSON.stringify(PH.errLog||[])"))
    ev("PH.setDemo(false),1"); time.sleep(2)
    for i in range(4):
        ev("document.getElementById('phPage').click(),1"); time.sleep(3)
        log(f"senza demo, PAGINA {i+1}", [ev("PAGE"), alive(), round(ev("__gap") or 0)])
    log("memoria", ev("performance.memory?Math.round(performance.memory.usedJSHeapSize/1e6)+' MB':'n.d.'"))

# orizzontale (tablet)
adb("shell", "settings", "put", "system", "accelerometer_rotation", "0")
adb("shell", "settings", "put", "system", "user_rotation", "1")
time.sleep(6)
shot("09_orizzontale")
log("orizzontale · app viva", alive())
adb("shell", "settings", "put", "system", "user_rotation", "0")

# due minuti in demo: memoria e stabilità
for i in range(4):
    time.sleep(30)
    log(f"dopo {30*(i+1)} s · app viva", alive())
shot("10_fine")
if ws:
    log("errori JS (fine)", ev("JSON.stringify(__err)"))
    log("memoria (fine)", ev("performance.memory?Math.round(performance.memory.usedJSHeapSize/1e6)+' MB':'n.d.'"))
json.dump(res, open(f"{OUT}/risultati.json", "w"), ensure_ascii=False, indent=1)
