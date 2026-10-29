#!/usr/bin/env python3
# I-A517 Strumento di volo · © 2026 Enrico D'Amico · Tutti i diritti riservati.
# Copia, modifica e distribuzione solo con permesso scritto dell'autore (vedi il file LICENSE).
"""Prepara www/ dell'APK dalla versione telefono costruita da build_android.py (cartella www/ della PWA).
Aggiunge il runtime di Capacitor, così la pagina usa le funzioni native (GLO 2, voce, file, METAR)."""
import shutil, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent.parent
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE.parent / "android" / "www"
DST = HERE / "www"
if DST.exists(): shutil.rmtree(DST)
DST.mkdir()
for f in ["index.html", "app.html", "version.js", "regole.js", "LICENZE.txt", "sw.js", "manifest.webmanifest", "icon-192.png", "icon-512.png", "icon-maskable-512.png"]:
    shutil.copy(SRC / f, DST / f)
shutil.copy(HERE / "node_modules/@capacitor/core/dist/capacitor.js", DST / "capacitor.js")
idx = (DST / "index.html").read_text(encoding="utf-8")
tag = '<script src="capacitor.js"></script>\n'
assert "</head>" in idx
idx = idx.replace("</head>", tag + "</head>", 1)
(DST / "index.html").write_text(idx, encoding="utf-8")
print("www pronta:", ", ".join(sorted(p.name for p in DST.iterdir())))
