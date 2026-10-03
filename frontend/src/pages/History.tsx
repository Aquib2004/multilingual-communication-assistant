import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import { EmptyState, ErrorState, LoadingState } from '@/components/LoadingState';
import { RiskBadge } from '@/components/RiskBadge';
import { ApiError, api } from '@/services/api';
import { STATE_LABELS, currentStage, statusStyle } from '@/lib/format';
import type { Message } from '@/types';

/** Previously created workspaces, newest first. */
export function History() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.listMessages(50, 0);
      setMessages(data.items);
    } catch (err) {
      setError(err instanceof ApiError ? err.userMessage : 'Could not load saved messages.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Past messages</h1>
          <p className="mt-1 text-sm text-slate-600">
            Every workspace is stored locally. Delete one to remove it.
          </p>
        </div>
        <button type="button" className="btn-secondary" onClick={() => void load()}>
          Refresh
        </button>
      </header>

      {error ? <ErrorState message={error} onRetry={() => void load()} /> : null}
      {loading ? <LoadingState label="Loading saved messages…" /> : null}

      {!loading && !error && messages.length === 0 ? (
        <EmptyState
          title="No saved messages yet"
          description="Start one in the workspace and it will appear here."
          action={
            <Link to="/workspace" className="btn-primary">
              Open the workspace
            </Link>
          }
        />
      ) : null}

      {messages.length > 0 ? (
        <ul className="space-y-3" data-testid="history-list">
          {messages.map((message) => (
            <li key={message.id} className="card">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <RiskBadge level={message.risk_level} />
                <span className="text-xs text-slate-500">
                  {new Date(message.created_at).toLocaleString()}
                </span>
              </div>

              <p className="mt-2 line-clamp-3 text-sm text-slate-800">{message.source_message}</p>

              <div className="mt-3 flex flex-wrap items-center gap-2 text-sm">
                <span className="text-slate-600">{STATE_LABELS[message.state]}</span>
                <span
                  className={`text-xs ${
                    statusStyle(message.state === 'escalated' ? 'ESCALATED' : 'PASS').textClass
                  }`}
                >
                  Step{' '}
                  {currentStage(message.state, message.translations.length) + 1} of 7
                </span>
                {message.translations.length > 0 ? (
                  <span className="text-xs text-slate-500">
                    {message.translations.length} translation
                    {message.translations.length === 1 ? '' : 's'}
                  </span>
                ) : null}
              </div>

              <details className="mt-2 text-sm">
                <summary className="cursor-pointer text-slate-600">Full record</summary>
                <pre className="mt-2 max-h-64 overflow-auto whitespace-pre-wrap rounded-lg bg-slate-50 p-3 text-xs text-slate-800">
                  {JSON.stringify(
                    {
                      id: message.id,
                      state: message.state,
                      source: message.source_message,
                      approved: message.approved_message,
                      protected_items: message.protected_items.map((item) => ({
                        type: item.item_type,
                        value: item.value,
                      })),
                      translations: message.translations.map((t) => ({
                        language: t.target_language,
                        text: t.translated_message,
                      })),
                    },
                    null,
                    2,
                  )}
                </pre>
              </details>

              <button
                type="button"
                className="btn-danger mt-3 text-sm"
                onClick={() => void api.deleteMessage(message.id).then(load)}
              >
                Delete
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
