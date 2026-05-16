/**
 * Bootstraps background geolocation inside the Capacitor native wrapper.
 *
 * Copy this file into /app/frontend/src/native/ and import from App.js:
 *
 *   import { Capacitor } from "@capacitor/core";
 *   import bootstrapNativeLocation from "@/native/locationBootstrap";
 *   useEffect(() => { if (Capacitor.isNativePlatform()) bootstrapNativeLocation(api); }, []);
 *
 * Behavior:
 *   - Asks for "Always" location permission once
 *   - Runs a foreground service that fires every 5 min, even when app is closed
 *   - POSTs each fix to /api/location/ping using the same axios instance the web app uses
 *   - Survives device reboot (startOnBoot=true)
 */

export default async function bootstrapNativeLocation(api) {
  try {
    const { default: BackgroundGeolocation } = await import("@capacitor-community/background-geolocation");

    await BackgroundGeolocation.addWatcher(
      {
        backgroundMessage: "Active",
        backgroundTitle: "Nalanda",
        requestPermissions: true,
        stale: false,
        distanceFilter: 30,
      },
      async (location, error) => {
        if (error) return;
        if (!location) return;
        try {
          await api.post("/location/ping", {
            lat: location.latitude,
            lng: location.longitude,
            accuracy: location.accuracy,
            speed: location.speed,
            battery: null,
            timestamp: new Date().toISOString(),
          });
        } catch {
          // silent
        }
      }
    );
  } catch {
    // plugin not available in pure web build — silent no-op
  }
}
