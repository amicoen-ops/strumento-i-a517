#!/bin/bash
# I-A517 Strumento di volo · © 2026 Enrico D'Amico · Tutti i diritti riservati.
# Copia, modifica e distribuzione solo con permesso scritto dell'autore (vedi il file LICENSE).
# Collaudo dell'APK sull'emulatore. Uso: emu_test.sh file.apk cartella_uscita
APK="$1"; OUT="$2"; PKG=it.ia517.strumento
mkdir -p "$OUT"
adb wait-for-device
adb shell input keyevent 82 || true
adb logcat -c
echo "== installazione"; adb install -r "$APK" 2>&1 | tail -2

echo "== A: primo avvio senza permessi"
adb shell am start -W -n $PKG/.MainActivity
sleep 15
adb exec-out screencap -p > "$OUT/00_primo_avvio.png"
echo "viva: $(adb shell pidof $PKG)"
adb shell uiautomator dump /sdcard/ui.xml >/dev/null 2>&1; adb pull /sdcard/ui.xml "$OUT/ui_primo_avvio.xml" >/dev/null 2>&1 || true
# consento la posizione dalla finestra di sistema, se c'è
for t in "While using the app" "Only this time" "Allow"; do
  b=$(grep -o "text=\"$t\"[^>]*bounds=\"\[[0-9]*,[0-9]*\]\[[0-9]*,[0-9]*\]\"" "$OUT/ui_primo_avvio.xml" 2>/dev/null | head -1 | grep -o '\[[0-9]*,[0-9]*\]\[[0-9]*,[0-9]*\]')
  if [ -n "$b" ]; then x=$(echo $b | sed -E 's/\[([0-9]+),([0-9]+)\]\[([0-9]+),([0-9]+)\]/\1 \3/' | awk '{print int(($1+$2)/2)}'); y=$(echo $b | sed -E 's/\[([0-9]+),([0-9]+)\]\[([0-9]+),([0-9]+)\]/\2 \4/' | awk '{print int(($1+$2)/2)}'); echo "tocco $t ($x,$y)"; adb shell input tap $x $y; break; fi
done
sleep 5
adb exec-out screencap -p > "$OUT/00b_dopo_permesso.png"
echo "viva dopo permesso: $(adb shell pidof $PKG)"

echo "== B: posizione simulata sulla Carolina e collaudo nella pagina"
adb shell pm grant $PKG android.permission.ACCESS_FINE_LOCATION || true
adb shell pm grant $PKG android.permission.ACCESS_COARSE_LOCATION || true
adb emu geo fix 7.8656 45.2683 230 || true
( for i in $(seq 1 120); do adb emu geo fix 7.8656 45.2683 230 >/dev/null 2>&1; sleep 2; done ) &
GEO=$!
adb shell pidof $PKG >/dev/null || adb shell am start -W -n $PKG/.MainActivity
python3 tools/emu_cdp.py "$OUT" 2>&1 | tee "$OUT/cdp.txt"
kill $GEO 2>/dev/null || true

echo "== registro"
adb logcat -d -v time > "$OUT/logcat.txt"
{
  echo "### Crash Java"; grep -n -A40 "FATAL EXCEPTION" "$OUT/logcat.txt" | head -120
  echo; echo "### WebView / renderer"; grep -n -i -E "renderer|crashed|chromium.*(error|fatal)|OutOfMemory|lowmemorykiller|ANR in|Fatal signal" "$OUT/logcat.txt" | head -60
  echo; echo "### Console della pagina (errori)"; grep -n -E "Capacitor/Console|Console" "$OUT/logcat.txt" | grep -i -E "error|uncaught|exception" | head -60
  echo; echo "### Capacitor"; grep -n -E " (Capacitor|Capacitor/Plugin|GloSerial)" "$OUT/logcat.txt" | head -60
  echo; echo "### Processo"; grep -n -E "Process.*$PKG|$PKG.*(died|crash|Force)" "$OUT/logcat.txt" | head -30
} > "$OUT/sintesi.txt"
echo "fatto"
