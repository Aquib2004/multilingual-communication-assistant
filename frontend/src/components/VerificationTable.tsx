import { CopyButton, EscalationNotice, StatusBadge } from '@/components/RiskBadge';
import { EmptyState } from '@/components/LoadingState';
import type { VerificationReport } from '@/types';

interface VerificationTableProps {
  report: VerificationReport | null;
}

export function VerificationTable({ report }: VerificationTableProps) {
  /**
   * The fact map: every checked item, its source, its translation, and a verdict.
   *
   * Failures are sorted first. A green row must never be the first thing a
   * reviewer sees when something is actually wrong.
   */
  if (!report) {
    return (
      <EmptyState
        title="Nothing verified yet"
        description="Translate the message, then verify a translation to build the fact map."
      />
    );
  }

  const order: Record<string, number> = { FAIL: 0, WARNING: 1, REVIEW: 2, PASS: 3 };
  const checks = [...report.checks].sort(
    (a, b) => (order[a.status] ?? 9) - (order[b.status] ?? 9),
  );

  return (
    <div className="space-y-5" data-testid="verification-table">
      <div className="card">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-lg font-semibold text-slate-900">5. Verification</h2>
          <StatusBadge status={report.overall_status} />
        </div>

        <dl className="mt-3 grid grid-cols-2 gap-3 text-sm sm:grid-cols-5">
          <Stat label="Checked" value={report.summary.total ?? 0} />
          <Stat label="Passed" value={report.summary.passed ?? 0} />
          <Stat label="Warnings" value={report.summary.warnings ?? 0} />
          <Stat label="Failures" value={report.summary.failures ?? 0} />
          <Stat label="Need review" value={report.summary.review_required ?? 0} />
        </dl>

        {report.human_review_required ? (
          <p className="mt-3 text-sm font-medium text-amber-900">
            A fluent reviewer must confirm this translation before it is sent.
          </p>
        ) : null}

        <EscalationNotice
          level={report.risk.level}
          note={report.escalation_note}
          requirements={report.review_requirements}
        />
      </div>

      <div className="card">
        <h3 className="text-sm font-semibold text-slate-800">Fact map</h3>
        <div className="mt-2 overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-sm">
            <caption className="sr-only">
              Each protected item, its source, its translation, and the verdict
            </caption>
            <thead>
              <tr>
                <th scope="col" className="px-3 py-2 text-left font-medium text-slate-700">
                  Item
                </th>
                <th scope="col" className="px-3 py-2 text-left font-medium text-slate-700">
                  Source
                </th>
                <th scope="col" className="px-3 py-2 text-left font-medium text-slate-700">
                  Translation
                </th>
                <th scope="col" className="px-3 py-2 text-left font-medium text-slate-700">
                  Status
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {checks.map((check, index) => (
                <tr key={`${check.item_type}-${index}`} data-testid="fact-row">
                  <td className="px-3 py-2 text-slate-600">{check.item_type}</td>
                  <td className="px-3 py-2 font-medium text-slate-900">{check.source}</td>
                  <td className="px-3 py-2 text-slate-700">
                    {check.translated ?? <span className="text-slate-400">not found</span>}
                    {check.detail ? (
                      <p className="mt-1 text-xs text-slate-500">{check.detail}</p>
                    ) : null}
                  </td>
                  <td className="px-3 py-2">
                    <StatusBadge status={check.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {report.back_translation.length > 0 ? (
        <div className="card">
          <h3 className="text-sm font-semibold text-slate-800">
            6. Back-translation of the critical lines
          </h3>
          <ul className="mt-2 space-y-3 text-sm">
            {report.back_translation.map((pair, index) => (
              <li key={index} className="rounded-lg bg-slate-50 p-3">
                <StatusBadge status={pair.status} />
                <p className="mt-1 text-slate-700">
                  <span className="font-medium">Source:</span> {pair.source_sentence}
                </p>
                <p className="text-slate-700">
                  <span className="font-medium">Back-translated:</span>{' '}
                  {pair.back_translated ?? 'not produced'}
                </p>
                {pair.detail ? <p className="mt-1 text-slate-600">{pair.detail}</p> : null}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="card">
        <h3 className="text-sm font-semibold text-slate-800">Tone and terminology</h3>
        <p className="mt-1 text-sm text-slate-700">
          Overall tone: <span className="font-medium">{report.tone_assessment.tone}</span>
        </p>
        {report.tone_assessment.terminology_notes.length > 0 ? (
          <ul className="mt-2 list-disc pl-5 text-sm text-slate-700">
            {report.tone_assessment.terminology_notes.map((note) => (
              <li key={note}>{note}</li>
            ))}
          </ul>
        ) : null}
      </div>

      {report.issues.length > 0 ? (
        <div className="card">
          <h3 className="text-sm font-semibold text-slate-800">Issues to resolve</h3>
          <ul className="mt-2 space-y-2 text-sm">
            {report.issues.map((issue, index) => (
              <li key={`${issue.code}-${index}`} className="flex items-start gap-2">
                <StatusBadge
                  status={
                    issue.severity === 'error'
                      ? 'FAIL'
                      : issue.severity === 'warning'
                        ? 'WARNING'
                        : 'PASS'
                  }
                />
                <span className="text-slate-700">{issue.message}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="card">
        <h3 className="text-sm font-semibold text-slate-900">7. Final output</h3>
        <p className="mt-1 text-sm text-slate-600">
          Copy the final text only after a fluent reviewer has confirmed it. This tool does not
          certify translations.
        </p>
        <CopyButton
          className="mt-3"
          text={report.back_translation.map((p) => p.back_translated ?? '').join('\n')}
          label="Copy reviewed text"
        />
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  /** One number in the verification summary. */
  return (
    <div className="rounded-lg bg-slate-50 p-3 text-center">
      <dt className="text-xs text-slate-600">{label}</dt>
      <dd className="text-lg font-semibold text-slate-900">{value}</dd>
    </div>
  );
}

