import { defineConfig } from 'vite';

export default defineConfig({
  root: 'web',
  envDir: '..',
  publicDir: 'public',
  build: { outDir: 'dist', emptyOutDir: true },
  server: {
    host: '127.0.0.1',
    port: 5173,
    proxy: { '/interview': 'http://127.0.0.1:8000' },
  },
});
