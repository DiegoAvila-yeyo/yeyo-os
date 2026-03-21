## ═══════════════════════════════════════
## MICRO-FASE 3.8 — Theme System
## Tipo: VSCODE | Prompts: 1 | Complejidad: Simple
## ═══════════════════════════════════════

### PROMPT 3.8-1 [VSCODE] — Sistema de tema dark con estética neural/cyberpunk

```
Estamos construyendo YeyoOS, un OS AI-nativo con interfaz Neural Hub. Esta es la micro-fase 3.8 de Capa 3 (Cuerpo): crear el sistema de temas con estética neural/cyberpunk.

CONTEXTO:
- Micro-fases 3.0-3.7 completadas: Canvas, nodos, chat, MiniChat, file drop
- Dark theme es el único tema (por ahora)
- Paleta: fondos oscuros, acentos neón (azul, púrpura, verde)
- Fonts: Inter para UI, JetBrains Mono para código
- CSS variables para facilitar cambios futuros
- Tailwind config extendido con colores YeyoOS

Abre el directorio ~/yeyo-os/frontend en VS Code.

CREAR:

1. Crear estructura:
   mkdir -p src/lib/theme
   mkdir -p __tests__/lib/theme

2. Crear archivo src/lib/theme/index.ts:

   Ruta: ~/yeyo-os/frontend/src/lib/theme/index.ts
   Contenido:

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

3. Crear archivo __tests__/lib/theme/theme.test.ts:

   Ruta: ~/yeyo-os/frontend/__tests__/lib/theme/theme.test.ts
   Contenido:

   /**
    * Tests para Theme System — Micro-fase 3.8
    */

   import {
     colors,
     fonts,
     animation,
     spacing,
     borderRadius,
     shadows,
     getCSSVariables,
     tailwindExtend,
   } from '@/lib/theme/index';

   describe('Theme System', () => {
     describe('colors', () => {
       it('tiene colores de fondo oscuros', () => {
         expect(colors.background.primary).toBe('#0a0a0f');
         expect(colors.background.secondary).toBe('#0d0d14');
       });

       it('tiene acentos neón', () => {
         expect(colors.accent.blue).toBe('#1e90ff');
         expect(colors.accent.purple).toBe('#9b59b6');
         expect(colors.accent.green).toBe('#2ecc71');
       });

       it('tiene colores de estado', () => {
         expect(colors.status.info).toBeDefined();
         expect(colors.status.success).toBeDefined();
         expect(colors.status.warning).toBeDefined();
         expect(colors.status.error).toBeDefined();
       });

       it('tiene colores de glow con alpha', () => {
         expect(colors.glow.blue).toContain('rgba');
         expect(colors.glow.purple).toContain('rgba');
       });

       it('tiene colores de texto legibles', () => {
         expect(colors.text.primary).toBeDefined();
         expect(colors.text.secondary).toBeDefined();
         expect(colors.text.disabled).toBeDefined();
       });
     });

     describe('fonts', () => {
       it('usa Inter para UI', () => {
         expect(fonts.ui).toContain('Inter');
       });

       it('usa JetBrains Mono para código', () => {
         expect(fonts.code).toContain('JetBrains Mono');
       });

       it('tiene fallbacks para ambas fuentes', () => {
         expect(fonts.ui).toContain('sans-serif');
         expect(fonts.code).toContain('monospace');
       });
     });

     describe('animation', () => {
       it('tiene duraciones progresivas', () => {
         expect(animation.duration.fast).toBeLessThan(animation.duration.normal);
         expect(animation.duration.normal).toBeLessThan(animation.duration.slow);
       });

       it('tiene easing spring para rebote', () => {
         expect(animation.easing.spring).toContain('cubic-bezier');
       });

       it('normal es ~300ms', () => {
         expect(animation.duration.normal).toBe(300);
       });
     });

     describe('getCSSVariables', () => {
       it('retorna variables CSS con prefijo --yeyo', () => {
         const vars = getCSSVariables();
         Object.keys(vars).forEach((key) => {
           expect(key).toMatch(/^--yeyo-/);
         });
       });

       it('incluye colores de fondo', () => {
         const vars = getCSSVariables();
         expect(vars['--yeyo-bg-primary']).toBe('#0a0a0f');
       });

       it('incluye fuentes', () => {
         const vars = getCSSVariables();
         expect(vars['--yeyo-font-ui']).toContain('Inter');
         expect(vars['--yeyo-font-code']).toContain('JetBrains Mono');
       });
     });

     describe('tailwindExtend', () => {
       it('tiene colores yeyo para Tailwind', () => {
         expect(tailwindExtend.colors.yeyo).toBeDefined();
         expect(tailwindExtend.colors.yeyo.bg).toBeDefined();
         expect(tailwindExtend.colors.yeyo.accent).toBeDefined();
       });

       it('tiene font families', () => {
         expect(tailwindExtend.fontFamily.ui).toBeDefined();
         expect(tailwindExtend.fontFamily.code).toBeDefined();
       });

       it('tiene animaciones personalizadas', () => {
         expect(tailwindExtend.animation['slide-in-right']).toBeDefined();
         expect(tailwindExtend.animation['fade-in']).toBeDefined();
       });

       it('tiene keyframes', () => {
         expect(tailwindExtend.keyframes.slideInRight).toBeDefined();
         expect(tailwindExtend.keyframes.fadeIn).toBeDefined();
       });
     });

     describe('spacing', () => {
       it('tiene escalas de espaciado', () => {
         expect(spacing.xs).toBe('4px');
         expect(spacing.md).toBe('16px');
         expect(spacing.xl).toBe('32px');
       });
     });

     describe('borderRadius', () => {
       it('tiene escalas de border radius', () => {
         expect(borderRadius.sm).toBe('4px');
         expect(borderRadius.lg).toBe('12px');
         expect(borderRadius.full).toBe('9999px');
       });
     });

     describe('shadows', () => {
       it('tiene sombras predefinidas', () => {
         expect(shadows.sm).toContain('rgba');
         expect(shadows.md).toContain('rgba');
         expect(shadows.lg).toContain('rgba');
       });

       it('glow genera sombra con color dado', () => {
         const result = shadows.glow('rgba(30, 144, 255, 0.4)');
         expect(result).toContain('20px');
         expect(result).toContain('rgba(30, 144, 255, 0.4)');
       });
     });
   });

4. Ejecutar tests:
   cd ~/yeyo-os/frontend
   npx jest __tests__/lib/theme/theme.test.ts --no-cache

VERIFICAR:
- [ ] Archivo src/lib/theme/index.ts existe
- [ ] Paleta dark con fondos #0a0a0f, acentos neón
- [ ] Fonts: Inter + JetBrains Mono con fallbacks
- [ ] getCSSVariables retorna variables con prefijo --yeyo
- [ ] tailwindExtend tiene colores, fonts, animaciones
- [ ] Animation durations y easings definidos
- [ ] TODOS los tests pasan

SI FALLA:
- Import: verificar que el path es correcto
- TypeScript as const: necesario para tipos literales

NO HACER:
- No crear tema claro (solo dark mode por ahora)
- No modificar tailwind.config.js aún (eso se hace al integrar)
- No agregar context/provider React (solo constantes puras)

GATE: Theme system tiene paleta completa, fonts, animaciones, CSS variables, extensión Tailwind, todos los tests pasan.
```
