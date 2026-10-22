import { useSyncExternalStore } from 'react'
import { Moon, Sun } from 'lucide-react'
import { Button } from '@/components/ui/button'

// O tema é aplicado antes da pintura por um script no <head> (root.tsx); aqui só alterna e salva.
const listeners = new Set<() => void>()
const subscribe = (cb: () => void) => {
  listeners.add(cb)
  return () => listeners.delete(cb)
}
const isDark = () => document.documentElement.classList.contains('dark')

export function ThemeToggle() {
  // no servidor (e na hidratação) é sempre "claro"; depois reflete a classe real do <html>
  const dark = useSyncExternalStore(subscribe, isDark, () => false)
  function toggle() {
    const next = !isDark()
    document.documentElement.classList.toggle('dark', next)
    try {
      localStorage.setItem('tur.theme', next ? 'dark' : 'light')
    } catch {
      /* sem persistência */
    }
    listeners.forEach((l) => l())
  }
  return (
    <Button type="button" variant="ghost" size="icon" onClick={toggle} aria-label={dark ? 'Tema claro' : 'Tema escuro'}>
      {dark ? <Sun /> : <Moon />}
    </Button>
  )
}
