/** @type {import('jest').Config} */
const config = {
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['@testing-library/jest-dom'],
  moduleNameMapper: {
    '\\.vert$': '<rootDir>/__mocks__/shader.ts',
    '\\.frag$': '<rootDir>/__mocks__/shader.ts',
    '^pixi\\.js$': '<rootDir>/__mocks__/pixi.js.ts',
    '^@/(.*)$': '<rootDir>/src/$1',
    '\\.css$': '<rootDir>/__mocks__/styleMock.ts',
    '^react-markdown$': '<rootDir>/__mocks__/react-markdown.tsx',
    '^remark-gfm$': '<rootDir>/__mocks__/remark-gfm.ts',
    '^wavesurfer\\.js$': '<rootDir>/__mocks__/wavesurfer-js.ts',
  },
  transform: {
    '^.+\\.(ts|tsx)$': ['ts-jest', { tsconfig: { jsx: 'react-jsx' } }],
  },
  testMatch: ['**/__tests__/**/*.test.(ts|tsx)'],
  collectCoverageFrom: ['src/**/*.{ts,tsx}', '!src/**/*.d.ts'],
};
module.exports = config;
