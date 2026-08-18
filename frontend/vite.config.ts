import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const isDev = mode === 'development'

  return {
    plugins: [react()],
    server: {
      port: 5173,
      proxy: isDev
        ? {
            '/api': {
              target: 'http://localhost:8001',
              changeOrigin: true,
            },
          }
        : undefined,
    },
  }
})
