import { CopyButton } from '@/components/RiskBadge';
import { EmptyState } from '@/components/LoadingState';
import type { Translation } from '@/types';

interface TranslationPanelProps {
  translations: Translation[];
  onVerify: (translationId: string) => void;
  verifyingId?: string | null;
}

export function TranslationPanel({
  translations,
  onVerify,
  verifyingId = null,
}: TranslationPanelProps) {
  /**
   * The translations, with the uncertainties the model reported.
   *
   * Uncertainties are shown rather than hidden: a glossary or model that is
   * unsure about a term should say so where the reviewer will see it.
   */
  if (translations.length === 0) {
    return (
      <EmptyState
        title="No translations yet"
        description="Approve the improved message, then translate it into your target languages."
      />
    );
  }

  return (
    <div className="space-y-4" data-testid="translation-panel">
      <h2 className="text-lg font-semibold text-slate-900">4. Translations</h2>

      {translations.map((translation) => (
        <article key={translation.id} className="card" data-testid="translation-card">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="text-base font-semibold text-slate-900">
              {translation.language_name}
              {translation.locale ? (
                <span className="ml-2 text-sm font-normal text-slate-500">
                  {translation.locale}
                </span>
              ) : null}
            </h3>
            <span className="text-xs text-slate-500">
              {translation.provider} · {translation.model}
            </span>
          </div>

          <p
            className="mt-3 whitespace-pre-wrap text-slate-900"
            dir={translation.target_language === 'ur' ? 'rtl' : 'ltr'}
            lang={translation.target_language}
          >
            {translation.translated_message}
          </p>

          {translation.uncertainties.length > 0 ? (
            <div className="mt-3 rounded-md bg-amber-50 p-3 text-sm text-amber-900 ring-1 ring-inset ring-amber-600/20">
              <p className="font-medium">The assistant flagged these</p>
              <ul className="mt-1 list-disc pl-5">
                {translation.uncertainties.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          ) : null}

          {translation.terminology_notes.length > 0 ? (
            <div className="mt-3 text-sm text-slate-700">
              <p className="font-medium text-slate-800">Terminology to confirm</p>
              <ul className="mt-1 list-disc pl-5">
                {translation.terminology_notes.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          ) : null}

          <div className="mt-4 flex flex-wrap items-center gap-3">
            <CopyButton text={translation.translated_message} label="Copy translation" />
            <button
              type="button"
              className="btn-primary"
              data-testid={`verify-${translation.target_language}`}
              disabled={verifyingId === translation.id}
              onClick={() => onVerify(translation.id)}
            >
              {verifyingId === translation.id ? 'Verifying…' : 'Verify this translation'}
            </button>
          </div>
        </article>
      ))}
    </div>
  );
}
