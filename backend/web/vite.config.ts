import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

const API_BASE_URL = process.env.VITE_API_BASE_URL || '';
const BUILD_VERSION = process.env.VITE_BUILD_VERSION || 'dev';
const BUILD_TIME = process.env.VITE_BUILD_TIME || new Date().toISOString();

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  define: {
    __BUILD_VERSION__: JSON.stringify(BUILD_VERSION),
    __BUILD_TIME__: JSON.stringify(BUILD_TIME),
  },
  build: {
    outDir: '../app/static',
    emptyOutDir: true,
  },
  server: {
    port: 5173,
    proxy: API_BASE_URL
      ? undefined
      : {
          '/api': 'http://127.0.0.1:8000',
          '/static': 'http://127.0.0.1:8000',
        },
  },
});