import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/sessions': 'http://localhost:8000',
      '/profile': 'http://localhost:8000',
      '/history': 'http://localhost:8000',
      '/settings': 'http://localhost:8000',
      '/preferences': 'http://localhost:8000',
      '/data': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    },
  },
})
