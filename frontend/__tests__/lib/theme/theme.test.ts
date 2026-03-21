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

    it('tiene acentos neon', () => {
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

    it('tiene colores de borde', () => {
      expect(colors.border.subtle).toBeDefined();
      expect(colors.border.default).toBeDefined();
      expect(colors.border.accent).toBeDefined();
    });
  });

  describe('fonts', () => {
    it('usa Inter para UI', () => {
      expect(fonts.ui).toContain('Inter');
    });

    it('usa JetBrains Mono para codigo', () => {
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

    it('instant es el mas rapido', () => {
      expect(animation.duration.instant).toBeLessThan(animation.duration.fast);
    });

    it('glacial es el mas lento', () => {
      expect(animation.duration.glacial).toBeGreaterThan(animation.duration.slow);
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

    it('incluye acentos', () => {
      const vars = getCSSVariables();
      expect(vars['--yeyo-accent-blue']).toBe('#1e90ff');
    });

    it('incluye colores de texto', () => {
      const vars = getCSSVariables();
      expect(vars['--yeyo-text-primary']).toBeDefined();
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

    it('slideInRight va de 100% a 0', () => {
      expect(tailwindExtend.keyframes.slideInRight.from.transform).toBe('translateX(100%)');
      expect(tailwindExtend.keyframes.slideInRight.to.transform).toBe('translateX(0)');
    });
  });

  describe('spacing', () => {
    it('tiene escalas de espaciado', () => {
      expect(spacing.xs).toBe('4px');
      expect(spacing.md).toBe('16px');
      expect(spacing.xl).toBe('32px');
    });

    it('escalas siguen orden creciente', () => {
      const sizes = [spacing.xs, spacing.sm, spacing.md, spacing.lg, spacing.xl, spacing.xxl];
      const nums = sizes.map((s) => parseInt(s));
      for (let i = 1; i < nums.length; i++) {
        expect(nums[i]).toBeGreaterThan(nums[i - 1]);
      }
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

    it('glow tiene doble sombra (near + far)', () => {
      const result = shadows.glow('#fff');
      const parts = result.split(',');
      expect(parts.length).toBeGreaterThanOrEqual(2);
    });
  });
});
