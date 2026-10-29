package it.ia517.strumento;

import android.Manifest;
import android.annotation.SuppressLint;
import android.bluetooth.BluetoothAdapter;
import android.bluetooth.BluetoothDevice;
import android.bluetooth.BluetoothManager;
import android.bluetooth.BluetoothSocket;
import android.content.Context;
import android.os.Build;

import com.getcapacitor.JSArray;
import com.getcapacitor.JSObject;
import com.getcapacitor.PermissionState;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;
import com.getcapacitor.annotation.Permission;
import com.getcapacitor.annotation.PermissionCallback;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.Set;
import java.util.UUID;

/**
 * Garmin GLO 2 (e qualunque GPS Bluetooth "classico" che parla NMEA sulla porta seriale SPP).
 * paired()      elenco dei dispositivi abbinati in Android
 * connect()     apre il canale RFCOMM e manda le frasi NMEA alla pagina (evento "nmea", a gruppi ogni 100 ms)
 * disconnect()  chiude
 * Evento "state" {connected:false,error} quando il collegamento cade.
 */
@CapacitorPlugin(
    name = "GloSerial",
    permissions = { @Permission(strings = { Manifest.permission.BLUETOOTH_CONNECT }, alias = "bluetooth") }
)
public class GloSerialPlugin extends Plugin {

    private static final UUID SPP = UUID.fromString("00001101-0000-1000-8000-00805F9B34FB");
    private BluetoothSocket socket;
    private Thread reader;
    private volatile boolean running = false;

    private boolean needsPermission() {
        return Build.VERSION.SDK_INT >= Build.VERSION_CODES.S && getPermissionState("bluetooth") != PermissionState.GRANTED;
    }

    private BluetoothAdapter adapter() {
        BluetoothManager bm = (BluetoothManager) getContext().getSystemService(Context.BLUETOOTH_SERVICE);
        return bm != null ? bm.getAdapter() : null;
    }

    @PluginMethod
    public void paired(PluginCall call) {
        if (needsPermission()) { requestPermissionForAlias("bluetooth", call, "permissionDone"); return; }
        listPaired(call);
    }

    @SuppressLint("MissingPermission")
    private void listPaired(PluginCall call) {
        BluetoothAdapter ad = adapter();
        if (ad == null) { call.reject("Bluetooth non presente"); return; }
        if (!ad.isEnabled()) { call.reject("Bluetooth spento: accendilo"); return; }
        JSArray list = new JSArray();
        Set<BluetoothDevice> devs = ad.getBondedDevices();
        if (devs != null) for (BluetoothDevice d : devs) {
            JSObject o = new JSObject();
            o.put("name", d.getName() != null ? d.getName() : "");
            o.put("address", d.getAddress());
            list.put(o);
        }
        JSObject ret = new JSObject();
        ret.put("devices", list);
        call.resolve(ret);
    }

    @PermissionCallback
    private void permissionDone(PluginCall call) {
        if (needsPermission()) { call.reject("Permesso Bluetooth negato"); return; }
        if ("connect".equals(call.getMethodName())) doConnect(call); else listPaired(call);
    }

    @PluginMethod
    public void connect(PluginCall call) {
        if (needsPermission()) { requestPermissionForAlias("bluetooth", call, "permissionDone"); return; }
        doConnect(call);
    }

    @SuppressLint("MissingPermission")
    private void doConnect(PluginCall call) {
        final String address = call.getString("address");
        final BluetoothAdapter ad = adapter();
        if (ad == null || address == null) { call.reject("Bluetooth non disponibile"); return; }
        if (!ad.isEnabled()) { call.reject("Bluetooth spento: accendilo"); return; }
        closeQuietly();
        new Thread(() -> {
            BluetoothSocket s = null;
            try {
                try { ad.cancelDiscovery(); } catch (SecurityException ignored) { }
                BluetoothDevice dev = ad.getRemoteDevice(address);
                try {
                    s = dev.createRfcommSocketToServiceRecord(SPP);
                    s.connect();
                } catch (IOException first) {
                    try { if (s != null) s.close(); } catch (IOException ignored) { }
                    s = dev.createInsecureRfcommSocketToServiceRecord(SPP);   // alcuni GPS non vogliono la connessione cifrata
                    s.connect();
                }
                socket = s;
                running = true;
                startReader(s);
                call.resolve();
            } catch (Exception e) {
                try { if (s != null) s.close(); } catch (IOException ignored) { }
                call.reject("Il GLO 2 non risponde: è acceso e abbinato? (" + e.getMessage() + ")");
            }
        }, "glo-connect").start();
    }

    private void startReader(final BluetoothSocket s) {
        reader = new Thread(() -> {
            String err = null;
            try (BufferedReader br = new BufferedReader(new InputStreamReader(s.getInputStream(), StandardCharsets.US_ASCII))) {
                JSArray batch = new JSArray();
                long last = System.currentTimeMillis();
                String line;
                while (running && (line = br.readLine()) != null) {
                    line = line.trim();
                    if (line.startsWith("$")) batch.put(line);
                    long now = System.currentTimeMillis();
                    if (batch.length() > 0 && (now - last >= 100 || batch.length() >= 40)) {
                        JSObject o = new JSObject();
                        o.put("lines", batch);
                        notifyListeners("nmea", o);
                        batch = new JSArray();
                        last = now;
                    }
                }
            } catch (IOException e) {
                err = e.getMessage();
            }
            if (running) {
                running = false;
                JSObject st = new JSObject();
                st.put("connected", false);
                st.put("error", err != null ? err : "collegamento chiuso");
                notifyListeners("state", st);
            }
            closeQuietly();
        }, "glo-reader");
        reader.start();
    }

    @PluginMethod
    public void disconnect(PluginCall call) {
        running = false;
        closeQuietly();
        call.resolve();
    }

    private void closeQuietly() {
        BluetoothSocket s = socket;
        socket = null;
        if (s != null) try { s.close(); } catch (IOException ignored) { }
    }

    @Override
    protected void handleOnDestroy() {
        running = false;
        closeQuietly();
    }
}
