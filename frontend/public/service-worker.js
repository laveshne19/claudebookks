// Minimal service worker for installability (PWA).
// We don't aggressively cache app shell to keep data fresh — backend is live.
const CACHE = "nalanda-v1";

self.addEventListener("install", (event) => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(self.clients.claim());
});

// Network-first for everything (live data); fall back to cache only on offline.
self.addEventListener("fetch", (event) => {
  const req = event.request;
  // Don't intercept non-GET or cross-origin API
  if (req.method !== "GET") return;
  event.respondWith(
    fetch(req)
      .then((res) => {
        const copy = res.clone();
        // Only cache same-origin static resources
        if (req.url.startsWith(self.location.origin) && req.url.includes("/static/")) {
          caches.open(CACHE).then((cache) => cache.put(req, copy));
        }
        return res;
      })
      .catch(() => caches.match(req))
  );
});
