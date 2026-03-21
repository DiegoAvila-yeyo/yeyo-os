import type { Config } from 'jest';

const config: Config = {
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['<rootDir>/jest.setup.ts'],
  moduleNameMapper: {
    // Shader files FIRST (before @/ catch-all)
    '\\.vert$': '<rootDir>/__mocks__/shader.ts',
    '\\.frag$': '<rootDir>/__mocks__/shader.ts',
    // Mock PixiJS (WebGL not available in jsdom)
    '^pixi\\.js$': '<rootDir>/__mocks__/pixi.js.ts',
    // Path aliases
    '^@/(.*)$': '<rootDir>/src/$1',
  },
  transform: {
    '^.+\\.(ts|tsx)$': ['ts-jest', {
      tsconfig: {
        jsx: 'react-jsx',
      },
    }],
  },
  testMatch: ['**/__tests__/**/*.test.(ts|tsx)'],
  collectCoverageFrom: ['src/**/*.{ts,tsx}', '!src/**/*.d.ts'],
};

export default config;
