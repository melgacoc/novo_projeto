// Service worker mínimo: torna o site instalável (PWA) e guarda os arquivos estáticos.
// Nunca guarda respostas da API (dados sempre atuais).
const CACHE = 'tur-static-v1'
self.addEventListener('install', () => self.skipWaiting())
self.addEventListener('activate', (e) => e.waitUntil(self.clients.claim()))
self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url)
  if (e.request.method !== 'GET' || url.origin !== self.location.origin || !url.pathname.startsWith('/assets/')) return
  e.respondWith(
    caches.open(CACHE).then(async (cache) => {
      const hit = await cache.match(e.request)
      if (hit) return hit
      const res = await fetch(e.request)
      if (res.ok) cache.put(e.request, res.clone())
      return res
    }),
  )
})
