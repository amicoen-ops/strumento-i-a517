// I-A517 Strumento di volo · © 2026 Enrico D'Amico · Tutti i diritti riservati.
// Copia, modifica e distribuzione solo con permesso scritto dell'autore (vedi il file LICENSE).
// =====================================================================================
//  Regole per tipo di volo: VDS basico, VDS avanzato, aviazione generale VFR.
//  Fonte: DPR 9 luglio 2010 n. 133, art. 8 e art. 9; classi di spazio aereo ICAO/SERA.
//  Le usa il piano (briefing della rotta) e lo strumento (spazio in cui sei, avvisi).
//  Sono un aiuto: valgono l'AIP in vigore, i NOTAM e le autorizzazioni ENAC.
// =====================================================================================
window.IA517_RULES = (function () {
  const KEY = 'ia517_profilo';
  const PROFILES = {
    vds_basico: { name: 'VDS basico', short: 'VDS BASICO' },
    vds_avanzato: { name: 'VDS avanzato', short: 'VDS AVANZATO' },
    vfr: { name: 'Aviazione generale VFR', short: 'VFR' },
  };
  const get = () => { try { const v = JSON.parse(localStorage.getItem(KEY) || 'null'); return PROFILES[v] ? v : 'vds_basico'; } catch (e) { return 'vds_basico'; } };
  const set = v => { if (PROFILES[v]) try { localStorage.setItem(KEY, JSON.stringify(v)); } catch (e) {} };

  // Pasqua (algoritmo di Gauss/Meeus) per il lunedì dell'Angelo
  function easter(y) {
    const a = y % 19, b = Math.floor(y / 100), c = y % 100, d = Math.floor(b / 4), e = b % 4, f = Math.floor((b + 8) / 25),
      g = Math.floor((b - f + 1) / 3), h = (19 * a + b - d - g + 15) % 30, i = Math.floor(c / 4), k = c % 4,
      l = (32 + 2 * e + 2 * i - h - k) % 7, m = Math.floor((a + 11 * h + 22 * l) / 451), mo = Math.floor((h + l - 7 * m + 114) / 31),
      da = ((h + l - 7 * m + 114) % 31) + 1;
    return new Date(y, mo - 1, da);
  }
  // sabato, domenica e festività nazionali: limite VDS basico 1000 ft invece di 500 (DPR 133/2010 art. 9 c. 3)
  function holiday(dt) {
    const d = dt || new Date(), w = d.getDay(); if (w === 0 || w === 6) return true;
    const md = (d.getMonth() + 1) * 100 + d.getDate();
    if ([101, 106, 425, 501, 602, 815, 1101, 1208, 1225, 1226].includes(md)) return true;
    const e = easter(d.getFullYear()); e.setDate(e.getDate() + 1);
    return e.getMonth() === d.getMonth() && e.getDate() === d.getDate();
  }
  const vdsMaxAgl = dt => holiday(dt) ? 1000 : 500;
  const isATZ = a => /\b(M?ATZ)\b/i.test(a.name || '') || a.cls === 'ATZ';
  const controlled = a => /^(A|B|C|D|E|CTR|CTA|TMA)$/.test(a.cls);

  // giudizio su uno spazio aereo che la rotta (o l'aereo) occupa alla sua quota
  function verdict(a, prof) {
    prof = prof || get(); const p = PROFILES[prof].name, c = a.cls;
    if (c === 'P') return { status: 'bad', text: 'Area proibita: non si entra, cambia rotta' };
    if (c === 'FMC') { const sq = (String(a.name).match(/SSR\s*(\d{4})/i) || [])[1];
      return { status: 'ok', text: `Area FMC: con il transponder è raccomandato il codice${sq ? ' ' + sq : ''} e l'ascolto sulla frequenza indicata (AIP ENR 1.6); non è un divieto` }; }
    if (prof === 'vds_basico') {
      if (isATZ(a)) return { status: 'bad', text: `${p}: vietato entrare nelle zone di traffico aeroportuale (ATZ), salvo autorizzazione ENAC` };
      if (controlled(a)) return { status: 'bad', text: `${p}: vietato, è spazio controllato (classe ${c}). Passa sotto la base o giralo intorno` };
      if (c === 'R') return { status: 'bad', text: `${p}: area regolamentata, evitala (o verifica in AIP, AUP e NOTAM che sia disattivata e aperta al VDS)` };
      if (c === 'TMZ') return { status: 'bad', text: `${p}: zona con transponder obbligatorio, il VDS basico non lo ha` };
      if (c === 'RMZ') return { status: 'warn', text: `${p}: zona con radio obbligatoria, servono radio e contatto` };
      if (c === 'Q') return { status: 'warn', text: 'Area pericolosa: verifica attività e orari prima del volo' };
      if (c === 'OFR') return { status: 'warn', text: 'Sorvolo limitato (per esempio un parco): rispetta la quota minima indicata' };
      if (c === 'SPORT' || c === 'W' || c === 'GSEC') return { status: 'warn', text: 'Area di attività sportive o volo a vela: occhi aperti' };
      if (c === 'G') return { status: 'ok', text: `Classe G: consentito al ${p}` };
      return { status: 'warn', text: 'Spazio non classificato: verifica in AIP' };
    }
    // VDS avanzato e aviazione generale: tutto lo spazio aperto al VFR, con le regole della classe
    if (c === 'A') return { status: 'bad', text: 'Classe A: il VFR non è ammesso' };
    if (c === 'R') return { status: 'bad', text: 'Area regolamentata: evitala o verifica in AIP, AUP e NOTAM che sia disattivata' };
    if (/^(B|C|D|CTR|CTA|TMA)$/.test(c)) return { status: 'warn', text: `Classe ${c}: serve l'autorizzazione ATC, radio sempre in ascolto${prof === 'vds_avanzato' ? ' e transponder' : ''}` };
    if (isATZ(a)) return { status: 'warn', text: 'ATZ: contatto radio con l\'ente o il traffico del campo' };
    if (c === 'E') return { status: 'ok', text: 'Classe E: VFR ammesso senza autorizzazione; radio consigliata' };
    if (c === 'TMZ') return { status: 'warn', text: 'Zona con transponder obbligatorio' };
    if (c === 'RMZ') return { status: 'warn', text: 'Zona con radio obbligatoria' };
    if (c === 'Q') return { status: 'warn', text: 'Area pericolosa: verifica attività e orari prima del volo' };
    if (c === 'OFR') return { status: 'warn', text: 'Sorvolo limitato: rispetta la quota minima indicata' };
    if (c === 'SPORT' || c === 'W' || c === 'GSEC') return { status: 'warn', text: 'Area di attività sportive o volo a vela: occhi aperti' };
    if (c === 'G') return { status: 'ok', text: 'Classe G: VFR ammesso' };
    return { status: 'warn', text: 'Spazio non classificato: verifica in AIP' };
  }
  // per gli avvisi in volo: questo spazio merita un avviso con questo profilo?
  function alerting(a, prof) { const v = verdict(a, prof); return v.status !== 'ok' && !/^(SPORT|W|GSEC|FMC)$/.test(a.cls); }

  return { PROFILES, KEY, get, set, holiday, vdsMaxAgl, verdict, alerting, isATZ, controlled,
    SOURCE: 'DPR 133/2010 art. 8–9 (VDS); classi ICAO/SERA (VFR)' };
})();
