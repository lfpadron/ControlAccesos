import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';

const allowedHosts = [
  'control-acceso-qr.com.mx',
  'www.control-acceso-qr.com.mx',
  'control-acceso-qr.mx',
  'www.control-acceso-qr.mx',
  'control-acceso-qr.com',
  'www.control-acceso-qr.com',
];

export default defineConfig({
  base: '/mobile/',
  plugins: [vue()],
  server: {
    allowedHosts,
    port: 5175,
    proxy: {
      '/api': 'http://backend:8000',
    },
  },
  preview: {
    allowedHosts,
  },
});
