const CACHE = "bizwrap-v1";
const SHELL = ["/", "/index.html", "/manifest.webmanifest", "/icon-192.png", "/icon-512.png"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const { request } = e;
  if (request.method !== "GET") return;
  const url = new URL(request.url);

  // network-first for navigation (always get latest site when online)
  if (request.mode === "navigate") {
    e.respondWith(fetch(request).catch(() => caches.match("/index.html")));
    return;
  }
  // cache-first for product images & static assets
  if (/\.(png|jpg|jpeg|webp|svg|woff2?|js|css)$/.test(url.pathname) || url.hostname.includes("cdn.shopify.com")) {
    e.respondWith(
      caches.match(request).then((hit) => hit || fetch(request).then((res) => {
        const copy = res.clone();
        caches.open(CACHE).then((c) => c.put(request, copy));
        return res;
      }).catch(() => hit))
    );
  }
});
