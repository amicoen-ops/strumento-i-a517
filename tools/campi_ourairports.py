#!/usr/bin/env python3
# I-A517 Strumento di volo · © 2026 Enrico D'Amico · Tutti i diritti riservati.
# Copia, modifica e distribuzione solo con permesso scritto dell'autore (vedi il file LICENSE).
"""Campi del Nord Italia da OurAirports (pubblico dominio) per la versione telefono.

Uso:  python3 campi_ourairports.py cartella_con_airports.csv_e_runways.csv
Scrive src/campi_nord.json nel formato di FIELDS_RAW:
  [id, sigla, nome, lat, lon, quota_ft|null, [[le, he, prua_vera, lunghezza_m, asfalto 0/1], ...], tipo]
tipo: aero (aeroporto), ulm (aviosuperficie), alti (altiporto), glac (ghiacciaio).
I campi che ci sono già nello strumento restano come sono: questo elenco li completa soltanto.
"""
import csv, json, re, sys
from pathlib import Path

REGIONI = {"IT-21", "IT-23", "IT-25", "IT-32", "IT-34", "IT-36", "IT-42", "IT-45"}  # Piemonte, VdA, Lombardia, Trentino-AA, Veneto, FVG, Liguria, Emilia-Romagna
TIPI = {"small_airport", "medium_airport", "large_airport"}
PAVED = re.compile(r"asp|con|bit|pem|tar|pav|cem", re.I)
VIA = re.compile(r"\b(aviosuperficie|avio\s?superficie|airfield|airstrip|airport|aeroporto( di)?|aerodromo|campo( di)? volo|ultralight( field)?|field|ulm|ultraleggeri|club)\b", re.I)
GLAC = re.compile(r"ghiacciaio|glacier|\bgh\.", re.I)


def pulito(nome):
    n = VIA.sub(" ", nome)
    n = re.sub(r"\s+", " ", n).strip(" -·,")
    return n or nome.strip()


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def main(cart):
    cart = Path(cart)
    piste = {}
    for r in csv.DictReader(open(cart / "runways.csv", encoding="utf-8")):
        piste.setdefault(r["airport_ident"], []).append(r)
    out = []
    for a in csv.DictReader(open(cart / "airports.csv", encoding="utf-8")):
        if a["iso_country"] != "IT" or a["type"] not in TIPI:
            continue
        lat, lon = num(a["latitude_deg"]), num(a["longitude_deg"])
        if lat is None or lon is None:
            continue
        if a["iso_region"] not in REGIONI and not (a["iso_region"].startswith("IT-U") and lat > 44.0):
            continue
        if re.search(r"heli|elisuperficie|eliporto|hospital|ospedale", a["name"], re.I):
            continue
        ident = a["ident"]
        icao = (a["icao_code"] or a["gps_code"] or "").strip()
        aero = bool(re.fullmatch(r"LI[A-Z]{2}", ident) or re.fullmatch(r"LI[A-Z]{2}", icao)) or a["type"] != "small_airport"
        elev = num(a["elevation_ft"])
        nome = pulito(a["name"])
        kind = "aero" if aero else ("glac" if GLAC.search(a["name"]) else ("alti" if elev and elev > 4000 else "ulm"))
        sigla = (icao if aero and re.fullmatch(r"LI[A-Z]{2}", icao or "") else (ident if aero and re.fullmatch(r"LI[A-Z]{2}", ident) else nome.upper()))[:13]
        rws = []
        for r in piste.get(ident, []):
            if r.get("closed") == "1":
                continue
            le, he = (r["le_ident"] or "").strip(), (r["he_ident"] or "").strip()
            if not le or le.upper().startswith("H"):
                continue
            L = num(r["length_ft"])
            if not L or L < 150:
                continue
            hdg = num(r["le_heading_degT"])
            if hdg is None:
                d = re.match(r"\d+", le)
                if not d:
                    continue
                hdg = (int(d.group()) * 10 + 3) % 360          # declinazione nel Nord Italia circa +3°
            if not he:
                d = re.match(r"(\d+)([LRC]?)", le)
                if d:
                    n = (int(d.group(1)) + 18 - 1) % 36 + 1
                    he = f"{n:02d}" + {"L": "R", "R": "L", "C": "C"}.get(d.group(2), "")
            rws.append([le, he, round(hdg, 1), round(L * 0.3048), 1 if PAVED.search(r["surface"] or "") else 0])
        out.append([ident, sigla, nome, round(lat, 5), round(lon, 5), int(elev) if elev is not None else None, rws, kind])
    out.sort(key=lambda f: f[0])
    dest = Path(__file__).resolve().parent / "src" / "campi_nord.json"
    dest.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    from collections import Counter
    print(len(out), "campi", dict(Counter(f[7] for f in out)), "con piste", sum(1 for f in out if f[6]), "->", dest)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ".")
