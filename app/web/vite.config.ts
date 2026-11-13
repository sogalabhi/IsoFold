import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// dev: `npm run dev` on :5173, forwarding /api to the Python server started by ../run.sh
export default defineConfig({
  plugins: [react()],
  server: { proxy: { '/api': 'http://127.0.0.1:8765' } },
})
