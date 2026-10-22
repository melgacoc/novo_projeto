import path from "path"
import { defineConfig } from "vite"
import { reactRouter } from "@react-router/dev/vite"
import tailwindcss from "@tailwindcss/vite"

// base do Rio Manager (alias @/ e plugin do Tailwind); o plugin do React (SPA) foi
// trocado pelo do React Router em modo framework (SSR nas páginas públicas)
export default defineConfig({
  plugins: [tailwindcss(), reactRouter()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  ssr: {
    // maplibre só roda no navegador; nunca entra no bundle do servidor
    external: ["maplibre-gl"],
  },
})
