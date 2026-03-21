/**
 * YeyoOS — Theme System
 * Micro-fase 3.8 — Capa 3: Cuerpo
 *
 * Sistema de tema dark con estética neural/cyberpunk.
 * CSS variables + constantes TypeScript.
 */

export const colors = {
  background: {
    primary: '#0a0a0f',
    secondary: '#0d0d14',
    tertiary: '#12121a',
    surface: '#1a1a2e',
  },
  accent: {
    blue: '#1e90ff',
    blueLight: '#00bfff',
    purple: '#9b59b6',
    purpleLight: '#bb86fc',
    green: '#2ecc71',
    greenLight: '#00e676',
    orange: '#ffa500',
    red: '#ff4444',
    redLight: '#ff6b6b',
  },
  text: {
    primary: '#e0e0e8',
    secondary: '#a0a0b0',
    tertiary: '#666680',
    disabled: '#44445a',
    inverse: '#0a0a0f',
  },
  border: {
    subtle: '#1a1a2e',
    default: '#333355',
    strong: '#4a4a70',
    accent: '#1e90ff',
  },
  status: {
    info: '#1e90ff',
    success: '#2ecc71',
    warning: '#ffa500',
    error: '#ff4444',
  },
  glow: {
    blue: 'rgba(30, 144, 255, 0.4)',
    purple: 'rgba(155, 89, 182, 0.4)',
    green: 'rgba(46, 204, 113, 0.4)',
    red: 'rgba(255, 68, 68, 0.4)',
  },
} as const;

export const fonts = {
  ui: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
  code: '"JetBrains Mono", "Fira Code", "Cascadia Code", "SF Mono", Consolas, monospace',
} as const;

export const animation = {
  duration: {
    instant: 50,
    fast: 150,
    normal: 300,
    slow: 500,
    glacial: 1000,
  },
  easing: {
    default: 'cubic-bezier(0.4, 0, 0.2, 1)',
    spring: 'cubic-bezier(0.34, 1.56, 0.64, 1)',
    easeIn: 'cubic-bezier(0.4, 0, 1, 1)',
    easeOut: 'cubic-bezier(0, 0, 0.2, 1)',
    bounce: 'cubic-bezier(0.68, -0.55, 0.27, 1.55)',
  },
} as const;

export const spacing = {
  xs: '4px',
  sm: '8px',
  md: '16px',
  lg: '24px',
  xl: '32px',
  xxl: '48px',
} as const;

export const borderRadius = {
  sm: '4px',
  md: '8px',
  lg: '12px',
  xl: '16px',
  full: '9999px',
} as const;

export const shadows = {
  sm: '0 1px 3px rgba(0, 0, 0, 0.3)',
  md: '0 4px 12px rgba(0, 0, 0, 0.4)',
  lg: '0 8px 24px rgba(0, 0, 0, 0.5)',
  glow: (color: string) => `0 0 20px ${color}, 0 0 40px ${color}`,
} as const;

export function getCSSVariables(): Record<string, string> {
  return {
    '--yeyo-bg-primary': colors.background.primary,
    '--yeyo-bg-secondary': colors.background.secondary,
    '--yeyo-bg-tertiary': colors.background.tertiary,
    '--yeyo-bg-surface': colors.background.surface,
    '--yeyo-accent-blue': colors.accent.blue,
    '--yeyo-accent-purple': colors.accent.purple,
    '--yeyo-accent-green': colors.accent.green,
    '--yeyo-accent-orange': colors.accent.orange,
    '--yeyo-accent-red': colors.accent.red,
    '--yeyo-text-primary': colors.text.primary,
    '--yeyo-text-secondary': colors.text.secondary,
    '--yeyo-text-tertiary': colors.text.tertiary,
    '--yeyo-border-subtle': colors.border.subtle,
    '--yeyo-border-default': colors.border.default,
    '--yeyo-font-ui': fonts.ui,
    '--yeyo-font-code': fonts.code,
  };
}

export const tailwindExtend = {
  colors: {
    yeyo: {
      bg: colors.background,
      accent: colors.accent,
      text: colors.text,
      border: colors.border,
      status: colors.status,
    },
  },
  fontFamily: {
    ui: [fonts.ui],
    code: [fonts.code],
  },
  animation: {
    'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
    'pulse-fast': 'pulse 0.8s cubic-bezier(0.4, 0, 0.6, 1) infinite',
    'slide-in-right': 'slideInRight 0.3s ease-out',
    'fade-in': 'fadeIn 0.2s ease-out',
  },
  keyframes: {
    slideInRight: {
      from: { transform: 'translateX(100%)' },
      to: { transform: 'translateX(0)' },
    },
    fadeIn: {
      from: { opacity: '0' },
      to: { opacity: '1' },
    },
  },
} as const;
