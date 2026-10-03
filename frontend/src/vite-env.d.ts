/**
 * Declares the build-time constants the app relies on.
 *
 * Vite replaces `__API_BASE_URL__` at build time; the fallback keeps type
 * checking and unit tests working outside a Vite build.
 */
declare const __API_BASE_URL__: string;

declare module '*.css';
