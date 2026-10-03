import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiError, api } from '@/services/api';

/**
 * The API client is the only place that talks to the backend, so its error
 * handling is worth testing directly: a component that shows the wrong message
 * is a privacy or accuracy problem, not a cosmetic one.
 */
describe('api client', () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    fetchMock.mockReset();
    global.fetch = fetchMock as unknown as typeof fetch;
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  function jsonResponse(body: unknown, status = 200): Response {
    return {
      ok: status >= 200 && status < 300,
      status,
      text: () => Promise.resolve(JSON.stringify(body)),
    } as unknown as Response;
  }

  it('returns the parsed body on success', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ status: 'ok', ai_provider: 'mock' }));

    const health = await api.getHealth();

    expect(health.status).toBe('ok');
    expect(health.ai_provider).toBe('mock');
  });

  it('sends JSON bodies with the correct content type', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ id: 'm1' }, 201));

    await api.createMessage({ source_message: 'Hello families.' });

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect((init.headers as Record<string, string>)['Content-Type']).toBe('application/json');
    expect(JSON.parse(init.body as string)).toEqual({ source_message: 'Hello families.' });
  });

  it('surfaces the backend error code and message', async () => {
    fetchMock.mockResolvedValue(
      jsonResponse(
        {
          error: {
            code: 'SOURCE_NOT_APPROVED',
            message: 'The source message must be approved before translation.',
          },
          request_id: 'abc123',
        },
        409,
      ),
    );

    await expect(api.createTranslations({ message_id: 'm1', target_languages: ['es'] })).rejects.toThrow(
      ApiError,
    );

    try {
      await api.createTranslations({ message_id: 'm1', target_languages: ['es'] });
    } catch (error) {
      const apiError = error as ApiError;
      expect(apiError.code).toBe('SOURCE_NOT_APPROVED');
      expect(apiError.status).toBe(409);
      expect(apiError.requestId).toBe('abc123');
    }
  });

  it('reports a network failure as retryable', async () => {
    fetchMock.mockRejectedValue(new TypeError('Failed to fetch'));

    try {
      await api.getHealth();
      expect.unreachable('the request should have thrown');
    } catch (error) {
      const apiError = error as ApiError;
      expect(apiError.code).toBe('NETWORK_ERROR');
      expect(apiError.isRetryable).toBe(true);
      expect(apiError.userMessage).toMatch(/Could not reach the server/);
    }
  });

  it('treats server errors as retryable and validation errors as not', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse({ error: { code: 'X', message: 'x' } }, 500));
    try {
      await api.getHealth();
    } catch (error) {
      expect((error as ApiError).isRetryable).toBe(true);
    }

    fetchMock.mockResolvedValueOnce(
      jsonResponse({ error: { code: 'VALIDATION_ERROR', message: 'bad' } }, 422),
    );
    try {
      await api.getHealth();
    } catch (error) {
      expect((error as ApiError).isRetryable).toBe(false);
    }
  });

  it('falls back to a generic message when the error body is not JSON', async () => {
    fetchMock.mockResolvedValue({
      ok: false,
      status: 500,
      text: () => Promise.resolve('<html>gateway error</html>'),
    } as unknown as Response);

    try {
      await api.getHealth();
      expect.unreachable('the request should have thrown');
    } catch (error) {
      const apiError = error as ApiError;
      expect(apiError.code).toBe('UNKNOWN_ERROR');
      expect(apiError.message).toMatch(/status 500/);
    }
  });

  it('returns undefined for a 204 response', async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      status: 204,
      text: () => Promise.resolve(''),
    } as unknown as Response);

    await expect(api.deleteMessage('m1')).resolves.toBeUndefined();
  });
});
