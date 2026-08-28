const CACHE_NAME = 'rollcall-v1';
const STATIC_ASSETS = [
  '/static/css/style.css',
  '/static/js/theme.js',
  '/static/js/webcam.js',
  '/static/manifest.json',
  '/static/images/logo.png'
];

self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(STATIC_ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener('fetch', (e) => {
  if (e.request.method !== 'GET') return;
  e.respondWith(
    caches.match(e.request).then(cached => {
      if (cached) return cached;
      return fetch(e.request).then(response => {
        if (e.request.url.includes('/static/')) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(e.request, clone));
        }
        return response;
      }).catch(() => {
        if (e.request.mode === 'navigate') {
          return new Response(
            '<html><head><meta name="viewport" content="width=device-width"><style>body{font-family:system-ui;display:flex;align-items:center;justify-content:center;height:100vh;margin:0;background:#F3F1E7;color:#171B2E;}</style></head><body><div style="text-align:center;padding:20px;"><h1>Roll Call</h1><p>You are offline.<br>Please connect to the internet.</p></div></body></html>',
            { headers: { 'Content-Type': 'text/html' } }
          );
        }
      });
    })
  );
});

self.addEventListener('activate', (e) => {
  e.waitUntil(self.clients.claim());
});