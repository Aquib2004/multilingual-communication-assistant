import { useState } from 'react';

import { CopyButton } from '@/components/RiskBadge';
import { EmptyState } from '@/components/LoadingState';
import type { RewriteResponse } from '@/types';

interface RewriteResultProps {
  rewrite: RewriteResponse | null;
  onApprove: (reviewer?: string) => void;
  onReject: (notes: string) => void;
  onEdit: (text: string) => void;
  isApproved: boolean;
  busy?: boolean;
}

/**
 * Shows the plain-language revision and the human approval controls.
 *
 * This is the approval gate in the UI. The approve button is the only route to
 * translation, which is why it is presented as a decision rather than a step.
 */
export function RewriteResult({
  rewrite,
  onApprove,
  onReject,
  onEdit,
  isApproved,
  busy = false,
}: RewriteResultProps) {
  if (!rewrite) {
    return (
      <EmptyState
        title="No revision yet"
        description="Write your message and choose Improve message to see a clearer version."
      />
    );
  }

  const pii = rewrite.pii_warnings ?? [];

  return (
    <div className="card" data-testid="rewrite-result">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-lg font-semibold text-slate-900">2. Review the clearer version</h2>
        {isApproved ? (
          <span
            className="badge bg-green-50 text-green-800 ring-green-600/20"
            data-testid="approved-badge"
          >
            <span aria-hidden="true">✓</span> Approved for translation
          </span>
        ) : null}
      </div>

      {pii.length > 0 ? (
        <div
          role="alert"
          className="mt-4 rounded-lg bg-amber-50 p-3 text-sm text-amber-900 ring-1 ring-inset ring-amber-600/20"
        >
          <p className="font-medium">Possible personal data found</p>
          <ul className="mt-1 list-disc pl-5">
            {pii.map((finding) => (
              <li key={`${finding.category}-${finding.excerpt}`}>
                {finding.category}: {finding.excerpt}
              </li>
            ))}
          </ul>
          <p className="mt-1">Replace these with placeholders such as [PHONE] or [FAMILY NAME].</p>
        </div>
      ) : null}

      <label className="field-label mt-4" htmlFor="revised-message">
        Improved message
      </label>
      <textarea
        id="revised-message"
        data-testid="revised-message"
        className="field-input min-h-[8rem]"
        defaultValue={rewrite.rewritten_message}
        onBlur={(event) => {
          if (event.target.value !== rewrite.rewritten_message) {
            onEdit(event.target.value);
          }
        }}
        disabled={isApproved}
      />
      <p className="mt-1 text-xs text-slate-600">
        You can edit this directly. Blur the box to keep your changes.
      </p>

      {rewrite.changes.length > 0 ? (
        <div className="mt-5">
          <h3 className="text-sm font-semibold text-slate-800">
            What changed, and why ({rewrite.changes.length})
          </h3>
          <ul className="mt-2 space-y-3" data-testid="change-summary">
            {rewrite.changes.map((change, index) => (
              <li key={`${index}-${change.original}`} className="rounded-lg bg-slate-50 p-3 text-sm">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="rounded bg-red-100 px-1.5 py-0.5 text-red-800 line-through">
                    {change.original}
                  </span>
                  <span aria-hidden="true" className="text-slate-500">
                    →
                  </span>
                  <span className="rounded bg-green-100 px-1.5 py-0.5 text-green-800">
                    {change.revised}
                  </span>
                </div>
                <p className="mt-1 text-slate-700">{change.reason}</p>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {rewrite.open_questions.length > 0 ? (
        <div className="mt-5 rounded-lg bg-amber-50 p-3 ring-1 ring-inset ring-amber-600/20">
          <h3 className="text-sm font-semibold text-amber-900">
            Answer these before translating ({rewrite.open_questions.length})
          </h3>
          <ul className="mt-1 list-disc space-y-1 pl-5 text-sm text-amber-900">
            {rewrite.open_questions.map((question) => (
              <li key={question}>{question}</li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="mt-5 flex flex-wrap items-center gap-3">
        <CopyButton text={rewrite.rewritten_message} label="Copy improved message" />
        {isApproved ? (
          <p className="text-sm text-slate-600">Approved. You can now translate this message.</p>
        ) : (
          <ApprovalControls onApprove={onApprove} onReject={onReject} busy={busy} />
        )}
      </div>
    </div>
  );
}

interface ApprovalControlsProps {
  onApprove: (reviewer?: string) => void;
  onReject: (notes: string) => void;
  busy?: boolean;
}

function ApprovalControls({ onApprove, onReject, busy }: ApprovalControlsProps) {
  /** The approve and send-back controls, with an optional reviewer field. */
  const [reviewer, setReviewer] = useState('');
  const [notes, setNotes] = useState('');

  return (
    <div className="flex flex-wrap items-end gap-3">
      <div>
        <label className="field-label text-xs" htmlFor="reviewer">
          Reviewer (optional)
        </label>
        <input
          id="reviewer"
          data-testid="reviewer-input"
          className="field-input w-40"
          value={reviewer}
          onChange={(event) => setReviewer(event.target.value)}
          placeholder="Initials"
        />
      </div>

      <button
        type="button"
        className="btn-primary"
        data-testid="approve-button"
        disabled={busy}
        onClick={() => onApprove(reviewer || undefined)}
      >
        Approve and continue
      </button>

      <details className="text-sm">
        <summary className="cursor-pointer text-slate-700">Send back for changes</summary>
        <div className="mt-2">
          <label className="field-label text-xs" htmlFor="feedback">
            What should change?
          </label>
          <textarea
            id="feedback"
            data-testid="feedback-input"
            className="field-input min-h-[5rem] w-72"
            value={notes}
            onChange={(event) => setNotes(event.target.value)}
            placeholder="Use the family-facing term 'family night' instead."
          />
          <button
            type="button"
            className="btn-secondary mt-2"
            disabled={busy || notes.trim().length < 3}
            onClick={() => {
              onReject(notes);
              setNotes('');
            }}
          >
            Send back
          </button>
        </div>
      </details>
    </div>
  );
}
