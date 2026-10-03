/* ESLint configuration (legacy format, for ESLint 8).
 *
 * Uses the @typescript-eslint parser and plugin that are already declared in
 * package.json, rather than the newer flat-config umbrella package, so the tool
 * installs and runs with the pinned ESLint major version.
 */
module.exports = {
  root: true,
  env: { browser: true, es2020: true },
  ignorePatterns: ['dist', 'node_modules', 'coverage', '*.config.js', '*.config.cjs'],
  parser: '@typescript-eslint/parser',
  parserOptions: {
    ecmaVersion: 'latest',
    sourceType: 'module',
    ecmaFeatures: { jsx: true },
    // Type-aware rules such as no-floating-promises need this. TypeScript
    // itself is checked separately with `tsc --noEmit`, so this only feeds
    // ESLint the compiler's view of the program.
    project: './tsconfig.json',
    tsconfigRootDir: __dirname,
  },
  plugins: ['@typescript-eslint', 'react-hooks', 'react-refresh'],
  extends: [
    'eslint:recommended',
    'plugin:@typescript-eslint/recommended',
    'prettier',
  ],
  settings: {
    react: { version: 'detect' },
  },
  rules: {
    'react-hooks/rules-of-hooks': 'error',
    'react-hooks/exhaustive-deps': 'warn',
    'react-refresh/only-export-components': ['warn', { allowConstantExport: true }],
    // An unhandled promise hides real failures.
    '@typescript-eslint/no-floating-promises': 'error',
    '@typescript-eslint/no-explicit-any': 'error',
    '@typescript-eslint/no-unused-vars': [
      'error',
      { argsIgnorePattern: '^_', varsIgnorePattern: '^_' },
    ],
    eqeqeq: ['error', 'always'],
    'no-console': ['warn', { allow: ['warn', 'error'] }],
  },
  overrides: [
    {
      files: ['**/*.test.ts', '**/*.test.tsx', 'src/test/**/*.ts'],
      env: { node: true },
      rules: {
        '@typescript-eslint/no-explicit-any': 'off',
        '@typescript-eslint/no-non-null-assertion': 'off',
      },
    },
  ],
};