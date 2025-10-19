/**
 * Jest Configuration
 * Week 4 Day 27: System Integration Testing and Documentation
 */

const nextJest = require('next/jest');

const createJestConfig = nextJest({
  // Enable ES6 modules
  transform: {
    '^.+\\.(js|jsx|ts|tsx)$': ['babel-jest', { presets: ['next/babel'] }],
  },

  // Test environment setup
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],

  // Test file patterns
  testMatch: [
    '<rootDir>/src/**/__tests__/**/*.{js,jsx,ts,tsx}',
    '<rootDir>/src/**/*.{test,spec}.{js,jsx,ts,tsx}',
  ],

  // Module name mapping
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/src/$1',
    '^@components/(.*)$': '<rootDir>/src/components/$1',
    '^@pages/(.*)$': '<rootDir>/src/pages/$1',
    '^@lib/(.*)$': '<rootDir>/src/lib/$1',
  },

  // Path aliases for CSS modules
  moduleNameMapper: {
    '^.+\\.module\\.css$': 'identity-proxy',
    '^.+\\.scss$': 'identity-proxy',
  },

  // Mock file extensions
  moduleFileExtensions: ['ts', 'tsx', 'js', 'jsx', 'json', 'node'],

  // Test environment
  testEnvironment: 'jsdom',

  // Global mocks
  globalSetup: '<rootDir>/jest.globalSetup.js',
  globalTeardown: '<rootDir>/jest.globalTeardown.js',

  // Coverage configuration
  collectCoverage: true,
  coverageDirectory: 'coverage',
  coverageReporters: ['text', 'lcov', 'html'],
  coverageThreshold: {
    global: {
      branches: 70,
      functions: 70,
      lines: 70,
      statements: 70,
    },
    // Lower threshold for complex components
    '<rootDir>/src/components': {
      branches: 60,
      functions: 60,
      lines: 60,
      statements: 60,
    },
    // Higher threshold for utility functions
    '<rootDir>/src/lib': {
      branches: 80,
      functions: 80,
      lines: 80,
      statements: 80,
    },
  },
  collectCoverageFrom: [
    'src/**/*.{js,jsx,ts,tsx}',
    '!src/**/*.d.ts',
    '!src/**/index.ts',
  ],

  // Ignore patterns
  testPathIgnorePatterns: [
    '<rootDir>/.next/',
    '<rootDir>/node_modules/',
    '<rootDir>/coverage/',
  ],

  // Verbose output
  verbose: true,

  // Test timeout
  testTimeout: 10000,

  // Parallel execution
  maxWorkers: 4,

  // Module paths
  modulePaths: ['<rootDir>/node_modules'],

  // Setup files
  setupFilesAfterEnv: ['<rootDir>/tests/setupTests.js'],

  // Clear mocks
  clearMocks: true,
  restoreMocks: true,

  // Error handling
  errorOnDeprecated: true,

  // Reporter
  reporters: [
    'default',
    [
      'jest-junit',
      {
        outputDirectory: 'test-results',
        outputName: 'junit.xml',
      },
    ],
  ],
});

module.exports = createJestConfig;