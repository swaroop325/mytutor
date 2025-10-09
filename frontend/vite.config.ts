import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      'dcv': path.resolve(__dirname, 'public/dcv-sdk/dcvjs-umd/dcv.js'),
    },
  },
  optimizeDeps: {
    exclude: ['dcv'],
  },
  server: {
    allowedHosts: [
      'mytutor.myintern.org',
      'localhost',
      '127.0.0.1'
    ],
    host: true, // allow network access
    port: 5173
  }
})
