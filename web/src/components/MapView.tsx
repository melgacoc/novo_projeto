import { useEffect, useRef } from 'react'
import 'maplibre-gl/dist/maplibre-gl.css'
import type { Map as MLMap, Marker } from 'maplibre-gl'

// Mapa gratuito: MapLibre GL JS + tiles do OpenFreeMap (sem chave). Só roda no navegador.
const STYLE = 'https://tiles.openfreemap.org/styles/liberty'
const RIO: [number, number] = [-43.1729, -22.9068]

export type MapPoint = { id: number | string; lat: number; lng: number; label?: string; href?: string; html?: string }

type Props = {
  points: MapPoint[]
  center?: { lat: number; lng: number } | null
  zoom?: number
  className?: string
  /** Mostra um círculo de "região aproximada" em vez de um pino exato. */
  approximate?: boolean
  onPick?: (lat: number, lng: number) => void
  onPointClick?: (p: MapPoint) => void
}

export function MapView({ points, center, zoom = 11, className, approximate, onPick, onPointClick }: Props) {
  const el = useRef<HTMLDivElement>(null)
  const map = useRef<MLMap | null>(null)
  const markers = useRef<Marker[]>([])
  const lib = useRef<typeof import('maplibre-gl') | null>(null)
  const onPickRef = useRef(onPick)
  const onPointClickRef = useRef(onPointClick)
  onPickRef.current = onPick
  onPointClickRef.current = onPointClick

  useEffect(() => {
    let cancelled = false
    import('maplibre-gl').then((ml) => {
      if (cancelled || !el.current) return
      lib.current = ml
      const m = new ml.Map({
        container: el.current,
        style: STYLE,
        center: center ? [center.lng, center.lat] : RIO,
        zoom,
        attributionControl: { compact: true },
      })
      m.addControl(new ml.NavigationControl({ showCompass: false }), 'top-right')
      m.on('click', (e) => onPickRef.current?.(e.lngLat.lat, e.lngLat.lng))
      map.current = m
      // marcadores são elementos HTML: não precisam esperar o estilo carregar
      // (o evento 'load' pode nunca disparar se um recurso do estilo falhar ou for bloqueado)
      draw()
    })
    return () => {
      cancelled = true
      map.current?.remove()
      map.current = null
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  function draw() {
    const m = map.current
    const ml = lib.current
    if (!m || !ml) return
    markers.current.forEach((mk) => mk.remove())
    markers.current = []
    for (const p of points) {
      const node = document.createElement('button')
      node.type = 'button'
      node.setAttribute('aria-label', p.label ?? 'Passeio')
      node.className = approximate
        ? 'size-16 rounded-full border-2 border-sky-500 bg-sky-400/25'
        : 'rounded-full bg-sky-600 px-2 py-1 text-xs font-semibold text-white shadow-md ring-2 ring-white'
      if (!approximate) node.textContent = p.label ?? '•'
      node.onclick = (ev) => {
        ev.stopPropagation()
        onPointClickRef.current?.(p)
      }
      const mk = new ml.Marker({ element: node }).setLngLat([p.lng, p.lat]).addTo(m)
      if (p.html) mk.setPopup(new ml.Popup({ offset: 16 }).setHTML(p.html))
      markers.current.push(mk)
    }
    if (center) {
      m.easeTo({ center: [center.lng, center.lat], zoom: Math.max(m.getZoom(), zoom) })
    } else if (points.length > 1) {
      const b = new ml.LngLatBounds()
      points.forEach((p) => b.extend([p.lng, p.lat]))
      m.fitBounds(b, { padding: 60, maxZoom: 13, duration: 0 })
    } else if (points.length === 1) {
      m.easeTo({ center: [points[0].lng, points[0].lat], zoom: Math.max(zoom, 12) })
    }
  }

  useEffect(() => {
    if (map.current) draw()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [points, center?.lat, center?.lng])

  return <div ref={el} className={className ?? 'h-80 w-full rounded-lg'} />
}
