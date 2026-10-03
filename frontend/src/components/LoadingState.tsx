interface LoadingStateProps {
  label?: string;
  className?: string;
}

export function LoadingState({ label = 'Working…', className = '' }: LoadingStateProps) {
  /**
   * The busy indicator. It carries a role and an accessible label so assistive
   * technology announces that work is in progress.
   */
  return (
    <div
      role="status"
      aria-live="polite"
      data-testid="loading-state"
      className={`flex items-center gap-3 text-sm text-slate-700 ${className}`}
    >
      <span
        className="h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-blue-700"
        aria-hidden="true"
      />
      <span>{label}</span>
    </div>
  );
}

interface ErrorStateProps {
  message: string;
  onRetry?: () => void;
  onDismiss?: () => void;
  retryLabel?: string;
}

export function ErrorState({
  message,
  onRetry,
  onDismiss,
  retryLabel = 'Try again',
}: ErrorStateProps) {
  /**
   * The error panel. Errors are never swallowed silently: the user always sees
   * what went wrong, and can retry when retrying could help.
   */
  return (
    <div
      role="alert"
      data-testid="error-state"
      className="rounded-lg bg-red-50 p-4 text-sm text-red-900 ring-1 ring-inset ring-red-600/20"
    >
      <div className="flex items-start gap-3">
        <span className="mt-0.5 text-lg" aria-hidden="true">
          ✕
        </span>
        <div className="min-w-0 flex-1">
          <p>{message}</p>
          {onRetry || onDismiss ? (
            <div className="mt-3 flex gap-2">
              {onRetry ? (
                <button type="button" className="btn-primary" onClick={onRetry}>
                  {retryLabel}
                </button>
              ) : null}
              {onDismiss ? (
                <button type="button" className="btn-secondary" onClick={onDismiss}>
                  Dismiss
                </button>
              ) : null}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}

interface EmptyStateProps {
  title: string;
  description?: string;
  action?: React.ReactNode;
}

export function EmptyState({ title, description, action }: EmptyStateProps) {
  /** Shown when a panel has nothing to display yet. */
  return (
    <div
      data-testid="empty-state"
      className="rounded-lg border border-dashed border-slate-300 p-8 text-center"
    >
      <p className="text-sm font-medium text-slate-800">{title}</p>
      {description ? <p className="mt-1 text-sm text-slate-600">{description}</p> : null}
      {action ? <div className="mt-4 flex justify-center">{action}</div> : null}
    </div>
  );
}
