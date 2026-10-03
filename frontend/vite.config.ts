import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'node:path';

// The API base URL is read at build time so the same bundle can be pointed at a
// local backend or a deployed one without editing source.
const API_BASE_URL = process.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    strictPort: true,
  },
  preview: {
    port: 3000,
    strictPort: true,
  },
  define: {
    __API_BASE_URL__: JSON.stringify(API_BASE_URL),
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    css: false,
  },
});
