/**
 * The single point of communication with the backend.
 *
 * Every component goes through this module. No component calls `fetch`
 * directly, so error handling, timeouts, and the error envelope are handled in
 * exactly one place.
 */

import type {
  ApiErrorBody,
  EscalationResponse,
  ExamplesResponse,
  HealthResponse,
  LanguagesResponse,
  Message,
  MessageListResponse,
  RewriteResponse,
  RiskLevelsResponse,
  TranslationBatchResponse,
  VerificationReport,
} from '@/types';

const BASE_URL: string =
  typeof __API_BASE_URL__ !== 'undefined' ? __API_BASE_URL__ : 'http://localhost:8000/api';

const DEFAULT_TIMEOUT_MS = 60_000;

/** An error carrying the backend's stable code and a message safe to display. */
export class ApiError extends Error {
  readonly code: string;
  readonly status: number;
  readonly requestId?: string;

  constructor(message: string, code: string, status: number, requestId?: string) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.status = status;
    if (requestId) this.requestId = requestId;
  }

  /** True when retrying the same request could plausibly succeed. */
  get isRetryable(): boolean {
    return this.status === 0 || this.status === 429 || this.status >= 500;
  }

  /** A message suitable for showing directly to an end user. */
  get userMessage(): string {
    if (this.code === 'NETWORK_ERROR') {
      return 'Could not reach the server. Check that the backend is running, then try again.';
    }
    if (this.code === 'TIMEOUT') {
      return 'The server took too long to respond. Please try again.';
    }
    return this.message;
  }
}

interface RequestOptions {
  method?: 'GET' | 'POST' | 'DELETE';
  body?: unknown;
  signal?: AbortSignal;
  timeoutMs?: number;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, signal, timeoutMs = DEFAULT_TIMEOUT_MS } = options;

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  if (signal) {
    signal.addEventListener('abort', () => controller.abort());
  }

  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      method,
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new ApiError('The request timed out.', 'TIMEOUT', 0);
    }
    throw new ApiError('Network request failed.', 'NETWORK_ERROR', 0);
  } finally {
    clearTimeout(timer);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const text = await response.text();
  let payload: unknown = null;
  if (text) {
    try {
      payload = JSON.parse(text);
    } catch {
      payload = null;
    }
  }

  if (!response.ok) {
    const body = payload as ApiErrorBody | null;
    throw new ApiError(
      body?.error?.message ?? `Request failed with status ${response.status}.`,
      body?.error?.code ?? 'UNKNOWN_ERROR',
      response.status,
      body?.request_id,
    );
  }

  return payload as T;
}

// --- The API surface --------------------------------------------------------

export interface CreateMessagePayload {
  source_message: string;
  audience?: string;
  purpose?: string;
  action?: string;
  deadline?: string;
  contact_path?: string;
  tone?: string;
  risk_level?: string;
  target_languages?: string[];
  locale?: string;
}

export const api = {
  // --- Reference data ------------------------------------------------------
  getHealth: () => request<HealthResponse>('/health'),
  getLanguages: () => request<LanguagesResponse>('/languages'),
  getRiskLevels: () => request<RiskLevelsResponse>('/risk-levels'),
  getExamples: () => request<ExamplesResponse>('/examples'),

  // --- Messages (the Communication Workspace) ------------------------------
  createMessage: (payload: CreateMessagePayload) =>
    request<Message>('/messages', { method: 'POST', body: payload }),

  listMessages: (limit = 20, offset = 0) =>
    request<MessageListResponse>(`/messages?limit=${limit}&offset=${offset}`),

  getMessage: (id: string) => request<Message>(`/messages/${id}`),

  /**
   * Rewrite in plain language. Runs either against a saved workspace or as a
   * one-off. This never translates: the result must be approved first.
   */
  rewriteMessage: (payload: { message_id?: string; source_message?: string }) =>
    request<RewriteResponse>('/messages/rewrite', { method: 'POST', body: payload }),

  /** The approval gate. Nothing can be translated until this succeeds. */
  approveMessage: (id: string, payload: { approved: boolean; reviewer?: string; notes?: string }) =>
    request<Message>(`/messages/${id}/approve`, { method: 'POST', body: payload }),

  rejectMessage: (id: string, notes: string) =>
    request<Message>(`/messages/${id}/reject`, { method: 'POST', body: { notes } }),

  getProtectedItems: (id: string) => request<Message['protected_items']>(`/messages/${id}/protected-items`),

  deleteMessage: (id: string) => request<void>(`/messages/${id}`, { method: 'DELETE' }),

  // --- Translations --------------------------------------------------------
  /**
   * Translate an approved message. The backend answers 409 SOURCE_NOT_APPROVED
   * if the workspace has not been approved, and the UI surfaces that message.
   */
  createTranslations: (payload: {
    message_id: string;
    target_languages: string[];
    locale?: string;
    tone?: string;
    reading_level?: string;
  }) => request<TranslationBatchResponse>('/translations', { method: 'POST', body: payload }),

  // --- Verification --------------------------------------------------------
  verifyTranslation: (translationId: string) =>
    request<VerificationReport>('/verification', {
      method: 'POST',
      body: { translation_id: translationId },
    }),

  checkEscalation: (payload: { text: string; declared_risk_level?: string | null }) =>
    request<EscalationResponse>('/escalation/check', { method: 'POST', body: payload }),

  getExamplesList: () => request<ExamplesResponse>('/examples'),
};

export { BASE_URL };

