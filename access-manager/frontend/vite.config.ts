import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';

const apiTarget = process.env.VITE_DEV_API_TARGET ?? process.env.API_PROXY_TARGET ?? 'http://127.0.0.1:8080';
const allowedHosts = [
  'control-acceso-qr.com.mx',
  'www.control-acceso-qr.com.mx',
  'control-acceso-qr.mx',
  'www.control-acceso-qr.mx',
  'control-acceso-qr.com',
  'www.control-acceso-qr.com',
];

export default defineConfig({
  plugins: [vue()],
  server: {
    allowedHosts,
    port: 5173,
    proxy: {
      '/api': {
        target: apiTarget,
        changeOrigin: true,
      },
    },
  },
  preview: {
    allowedHosts,
  },
});
