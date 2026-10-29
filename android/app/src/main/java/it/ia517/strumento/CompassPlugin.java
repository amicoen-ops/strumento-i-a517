// I-A517 Strumento di volo · © 2026 Enrico D'Amico · Tutti i diritti riservati.
// Copia, modifica e distribuzione solo con permesso scritto dell'autore (vedi il file LICENSE).
package it.ia517.strumento;

import android.content.Context;
import android.hardware.Sensor;
import android.hardware.SensorEvent;
import android.hardware.SensorEventListener;
import android.hardware.SensorManager;

import com.getcapacitor.JSArray;
import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

/**
 * Bussola: il sensore di rotazione di Android (magnetometro + giroscopio + accelerometro).
 * Evento "rot" {R:[9 numeri], acc:0..3} circa 20 volte al secondo.
 * R porta dagli assi del telefono a quelli della Terra: X verso Est, Y verso il Nord magnetico, Z in alto.
 */
@CapacitorPlugin(name = "Compass")
public class CompassPlugin extends Plugin implements SensorEventListener {

    private SensorManager sm;
    private Sensor rv;
    private boolean on = false;
    private long last = 0;
    private int accuracy = -1;
    private final float[] R = new float[9];

    @Override
    public void load() {
        sm = (SensorManager) getContext().getSystemService(Context.SENSOR_SERVICE);
        if (sm != null) {
            rv = sm.getDefaultSensor(Sensor.TYPE_ROTATION_VECTOR);
            if (rv == null) rv = sm.getDefaultSensor(Sensor.TYPE_GEOMAGNETIC_ROTATION_VECTOR);
        }
    }

    @PluginMethod
    public void start(PluginCall call) {
        if (sm == null || rv == null) { call.reject("bussola non presente su questo telefono"); return; }
        if (!on) { sm.registerListener(this, rv, SensorManager.SENSOR_DELAY_GAME); on = true; }
        JSObject r = new JSObject();
        r.put("sensor", rv.getName());
        call.resolve(r);
    }

    @PluginMethod
    public void stop(PluginCall call) {
        if (on && sm != null) sm.unregisterListener(this);
        on = false;
        call.resolve();
    }

    @Override
    public void onSensorChanged(SensorEvent e) {
        long now = System.currentTimeMillis();
        if (now - last < 50) return;
        last = now;
        try {
            SensorManager.getRotationMatrixFromVector(R, e.values);
            JSArray a = new JSArray();
            for (float f : R) a.put((double) f);
            JSObject o = new JSObject();
            o.put("R", a);
            o.put("acc", accuracy);
            notifyListeners("rot", o);
        } catch (Exception ignored) { }
    }

    @Override
    public void onAccuracyChanged(Sensor s, int acc) { accuracy = acc; }

    @Override
    protected void handleOnPause() { if (on && sm != null) sm.unregisterListener(this); }

    @Override
    protected void handleOnResume() { if (on && sm != null) sm.registerListener(this, rv, SensorManager.SENSOR_DELAY_GAME); }

    @Override
    protected void handleOnDestroy() { if (sm != null) sm.unregisterListener(this); on = false; }
}
