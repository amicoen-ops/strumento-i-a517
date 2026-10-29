# I-A517 Strumento — app Android

Orizzonte sintetico, mappa, rotte, circuito, piano di volo e meteo per l'Avid Flyer I-A517, per telefono e tablet.
È la stessa pagina della versione installabile da browser (PWA), chiusa in un'app nativa con Capacitor. Così ha in più:

- **Garmin GLO 2** letto direttamente via Bluetooth (plugin `GloSerial`, in `android/app/src/main/java/it/ia517/strumento/`);
- **METAR e TAF** scaricati da aviationweather.gov;
- **voce** del telefono per gli avvisi, **schermo sempre acceso**, **schermo intero**;
- esportazione di **GPX** e del diario con il pannello «Condividi»;
- mappe dei servizi solo `http`, come l'IGM 1:25.000 e le ortofoto del Geoportale Nazionale.

## Compilazione
Ogni push su `main` avvia GitHub Actions. L'APK finisce tra le **Release**, firmato sempre con la stessa chiave (`keystore/strumento.keystore`), così gli aggiornamenti si installano sopra senza perdere i dati.

## Aggiornare le pagine
Le pagine si generano dai sorgenti dello strumento (`pfd.html`, `companion.html`) con `build_android.py`, poi `tools/prepare_www.py` le copia in `www/` aggiungendo il runtime di Capacitor.

## Permessi chiesti al primo uso
- Posizione: GPS del telefono.
- Dispositivi nelle vicinanze: solo quando colleghi il GLO 2.

Strumento sperimentale, non certificato: altimetro, anemometro, vista fuori e radio restano il riferimento.
