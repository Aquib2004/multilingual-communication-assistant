import { ContextFields } from '@/components/ContextFields';
import { LanguageSelector, LocaleSelector } from '@/components/LanguageSelector';
import { ErrorState, LoadingState } from '@/components/LoadingState';
import { MessageEditor } from '@/components/MessageEditor';
import { ProtectedItems } from '@/components/ProtectedItems';
import { RewriteResult } from '@/components/RewriteResult';
import { TranslationPanel } from '@/components/TranslationPanel';
import { RiskBadge } from '@/components/RiskBadge';
import { VerificationTable } from '@/components/VerificationTable';
import { useWorkspace } from '@/hooks/useWorkspace';
import { RISK_DESCRIPTIONS } from '@/lib/format';

const BUSY_LABELS: Record<string, string> = {
  rewriting: 'Improving your message…',
  approving: 'Recording your decision…',
  translating: 'Translating…',
  verifying: 'Verifying…',
};

/**
 * The Communication Workspace: the whole BRIDGE workflow in one screen.
 *
 * The order of the sections is the workflow. Translation is only offered after
 * approval, which mirrors the rule the backend enforces.
 */
export function Workspace() {
  const ws = useWorkspace();
  const { draft, setDraft, step, error, message, rewrite, translations, report } = ws;
  const busy = step !== 'idle';
  const riskLevel = message?.risk_level ?? draft.riskLevel;

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <header>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">
          Communication workspace
        </h1>
        <p className="mt-1 text-sm text-slate-600">{RISK_DESCRIPTIONS[riskLevel]}</p>
        <div className="mt-2">
          <RiskBadge level={riskLevel} />
        </div>
      </header>

      {error ? <ErrorState message={error} onDismiss={ws.clearError} /> : null}
      {busy ? <LoadingState label={BUSY_LABELS[step] ?? 'Working…'} /> : null}

      <section className="card">
        <h2 className="text-lg font-semibold text-slate-900">1. Message and context</h2>
        <p className="mt-1 text-sm text-slate-600">
          The translator works from this context, not from the message alone.
        </p>

        <div className="mt-4 space-y-4">
          <MessageEditor
            value={draft.sourceMessage}
            onChange={(value) => setDraft({ sourceMessage: value })}
            disabled={busy}
          />
          <ContextFields {...draft} onChange={setDraft} disabled={busy} />
          <div className="grid gap-4 sm:grid-cols-2">
            <LanguageSelector
              selected={draft.targetLanguages}
              onChange={(codes) => setDraft({ targetLanguages: codes })}
            />
            <LocaleSelector value={draft.locale} onChange={(tag) => setDraft({ locale: tag })} />
          </div>
        </div>

        <div className="mt-5 flex flex-wrap items-center gap-3">
          <button
            type="button"
            className="btn-primary"
            data-testid="improve-button"
            onClick={() => void ws.runRewrite()}
            disabled={busy}
          >
            Improve message
          </button>
          {ws.isApproved ? (
            <button
              type="button"
              className="btn-secondary"
              data-testid="translate-button"
              onClick={() => void ws.translate()}
              disabled={busy || !ws.canTranslate}
            >
              Translate into {draft.targetLanguages.length} languages
            </button>
          ) : (
            <p className="text-sm text-slate-500">
              Approve the improved message to enable translation.
            </p>
          )}
        </div>
      </section>

      <RewriteResult
        rewrite={rewrite}
        isApproved={ws.isApproved}
        busy={busy}
        onApprove={(reviewer) => void ws.approve(reviewer)}
        onReject={(notes) => void ws.reject(notes)}
        onEdit={(text) => setDraft({ sourceMessage: text })}
      />

      {ws.isApproved ? <ProtectedItems items={message?.protected_items ?? []} /> : null}

      {ws.canVerify || translations.length > 0 ? (
        <TranslationPanel
          translations={translations}
          verifyingId={null}
          onVerify={(id) => void ws.verify(id)}
        />
      ) : null}

      {report ? <VerificationTable report={report} /> : null}
    </div>
  );
}
