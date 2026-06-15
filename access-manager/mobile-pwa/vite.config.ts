import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';

export default defineConfig({
  base: '/mobile/',
  plugins: [vue()],
  server: {
    port: 5175,
    proxy: {
      '/api': 'http://backend:8000',
    },
  },
});
