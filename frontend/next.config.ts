import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  allowedDevOrigins: ['127.0.0.1', 'localhost'],
  // Fija la raíz del workspace: sin esto Turbopack detecta mal la raíz
  // (por un package-lock.json suelto en C:\Users\yeyoa) y no resuelve node_modules.
  turbopack: {
    root: "C:\\Users\\yeyoa\\Desktop\\yeyo-os\\frontend",
  },
  // Desactivado en dev para evitar doble-mount de efectos con timers
  reactStrictMode: false,
  // Proxy: redirige /api/* al backend FastAPI en puerto 8000
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/api/:path*',
      },
      {
        source: '/health',
        destination: 'http://localhost:8000/health',
      },
    ];
  },
};

export default nextConfig;
