import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// En desarrollo, /api y /fotos se redirigen a la API Flask (ui/api).
const api = 'http://127.0.0.1:5000'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': api,
      '/fotos': api,
    },
  },
})
