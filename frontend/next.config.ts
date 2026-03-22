import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  allowedDevOrigins: ['127.0.0.1', 'localhost'],
  // Desactivado en dev para evitar doble-mount de efectos con timers
  reactStrictMode: false,
};

export default nextConfig;
