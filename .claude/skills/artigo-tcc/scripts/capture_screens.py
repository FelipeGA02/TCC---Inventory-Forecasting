# -*- coding: utf-8 -*-
"""Captura telas do protótipo React (app-react) pelo Chrome DevTools Protocol.

Pré-requisito: servidor de desenvolvimento rodando em segundo plano, numa porta livre:
    cd app-react && npx vite --port 5199 --strictPort         (run_in_background)

    MSYS_NO_PATHCONV=1 python "C:\...\capture_screens.py" "C:\...\saida" <porta-cdp> "C:\...\planilha.xlsx" [job ...]

(com MSYS_NO_PATHCONV=1 o Git Bash não converte nada: todos os caminhos em formato Windows,
inclusive o do próprio script; use "$(cygpath -w ...)")

job = rota=nome=LARGURAxALTURA[=upload], por exemplo "/=fig06=1950x869".
Sem jobs, captura o conjunto padrão das Figuras 6 a 12 (proporções iguais às do artigo).

Por que assim (lições da consolidação de 30/09/2026):
- `chrome --screenshot` captura antes de a animação do Recharts terminar (linhas vazias) e o Edge
  headless trava com o perfil do usuário aberto; o CDP com espera em tempo real resolve.
- O Git Bash converte argumentos que começam com "/" em caminhos do Windows: rode com
  MSYS_NO_PATHCONV=1, senão a navegação falha com "invalid URL".
- Espera o #root ter texto e mais 4 s (animações). Largura 1950 px reproduz a escala das capturas
  originais; a imagem fica com mais resolução e o tamanho na página é dado pelo DOCX.
- A tela de validação (Fig. 8) precisa de um arquivo no input: usa DOM.setFileInputFiles com uma
  planilha real de ia-predictor/data/raw (só leitura; o protótipo não envia nada).
"""
import base64
import json
import os
import subprocess
import sys
import time
import urllib.request

import websocket  # websocket-client

sys.stdout.reconfigure(encoding="utf-8")

OUT, PORT, XLSX = sys.argv[1], int(sys.argv[2]), sys.argv[3]
APP = os.environ.get("APP_URL", "http://localhost:5199")
CHROME = os.environ.get("CHROME", r"C:\Program Files\Google\Chrome\Application\chrome.exe")
DEFAULT = [
    "/=fig06=1950x869", "/importar=fig07=1950x857", "/importar=fig08=1950x863=upload",
    "/pre-visualizacao=fig09=1950x881", "/previsao=fig10=1950x860", "/simulador=fig11=1950x861",
    "/exportar=fig12=1950x865",
]
jobs = [j.split("=") for j in (sys.argv[4:] or DEFAULT)]
os.makedirs(OUT, exist_ok=True)
prof = os.path.join(OUT, f"_chrome_profile_{PORT}")
proc = subprocess.Popen([CHROME, "--headless=new", "--hide-scrollbars", "--no-first-run",
                         "--remote-allow-origins=*", f"--user-data-dir={prof}",
                         f"--remote-debugging-port={PORT}", "--window-size=1950,870", "about:blank"])
try:
    tabs = None
    for _ in range(120):
        try:
            tabs = json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json"))
            break
        except Exception:
            time.sleep(0.5)
    tab = [t for t in tabs if t.get("type") == "page"][0]
    ws = websocket.create_connection(tab["webSocketDebuggerUrl"], timeout=60, suppress_origin=True)
    mid = [0]

    def call(method, params=None):
        mid[0] += 1
        ws.send(json.dumps({"id": mid[0], "method": method, "params": params or {}}))
        while True:
            m = json.loads(ws.recv())
            if m.get("id") == mid[0]:
                return m.get("result", m.get("error", {}))

    def ev(expr):
        return call("Runtime.evaluate", {"expression": expr, "returnByValue": True}).get("result", {}).get("value")

    call("Page.enable")
    call("Runtime.enable")
    for job in jobs:
        route, name, size = job[:3]
        action = job[3] if len(job) > 3 else None
        w, h = map(int, size.split("x"))
        call("Emulation.setDeviceMetricsOverride", {"width": w, "height": h, "deviceScaleFactor": 1, "mobile": False})
        nav = call("Page.navigate", {"url": APP + route})
        if "errorText" in nav or "message" in nav:
            raise SystemExit(f"navegação falhou em {route}: {nav} (rodou com MSYS_NO_PATHCONV=1?)")
        for _ in range(90):
            if (ev('(document.querySelector("#root")||{innerText:""}).innerText.length') or 0) > 0:
                break
            time.sleep(0.5)
        time.sleep(4)
        if action == "upload":
            root = call("DOM.getDocument", {"depth": -1})["root"]["nodeId"]
            node = call("DOM.querySelector", {"nodeId": root, "selector": "input[type=file]"})
            call("DOM.setFileInputFiles", {"files": [XLSX], "nodeId": node["nodeId"]})
            for _ in range(60):
                body = ev("document.body.innerText") or ""
                if "Pronto" in body and "sucesso" in body:
                    break
                time.sleep(0.5)
            time.sleep(2)
        shot = call("Page.captureScreenshot", {"format": "png"})
        open(os.path.join(OUT, name + ".png"), "wb").write(base64.b64decode(shot["data"]))
        print("ok", name, route)
    ws.close()
finally:
    proc.kill()
