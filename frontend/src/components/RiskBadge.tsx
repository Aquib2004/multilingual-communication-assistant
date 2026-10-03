import { useState } from 'react';

import { copyToClipboard, statusStyle } from '@/lib/format';
import type { VerificationStatus } from '@/types';

const RISK_STYLES = {
  routine: { label: 'Routine', badge: 'bg-slate-100 text-slate-800 ring-slate-500/20', icon: '·' },
  moderate: {
    label: 'Moderate consequence',
    badge: 'bg-amber-50 text-amber-800 ring-amber-600/20',
    icon: '!',
  },
  high: {
    label: 'High consequence',
    badge: 'bg-red-50 text-red-800 ring-red-600/20',
    icon: '⚠',
  },
} as const;

export type RiskLevelValue = keyof typeof RISK_STYLES;

interface RiskBadgeProps {
  level: RiskLevelValue;
  className?: string;
}

export function RiskBadge({ level, className = '' }: RiskBadgeProps) {
  /** Shows the consequence tier. The word carries the meaning; colour supports it. */
  const style = RISK_STYLES[level];
  return (
    <span className={`badge ${style.badge} ${className}`} data-testid="risk-badge">
      <span aria-hidden="true">{style.icon}</span>
      {style.label}
    </span>
  );
}

interface StatusBadgeProps {
  status: VerificationStatus | string;
  className?: string;
}

export function StatusBadge({ status, className = '' }: StatusBadgeProps) {
  /** Shows a verification status with an icon and a word, never colour alone. */
  const style = statusStyle(status);
  return (
    <span className={`badge ${style.badgeClass} ${className}`} data-testid="status-badge">
      <span aria-hidden="true">{style.icon}</span>
      {style.label}
    </span>
  );
}

interface EscalationNoticeProps {
  level: RiskLevelValue;
  note?: string | null;
  requirements?: string[];
}

export function EscalationNotice({ level, note, requirements = [] }: EscalationNoticeProps) {
  /**
   * The escalation banner.
   *
   * For high-consequence content this states plainly that professional human
   * translation is recommended and that the tool never certifies a translation.
   */
  if (level !== 'high' && requirements.length === 0) return null;
  const isHigh = level === 'high';

  return (
    <div
      role="alert"
      data-testid="escalation-notice"
      className={`rounded-lg p-4 ring-1 ring-inset ${
        isHigh
          ? 'bg-purple-50 text-purple-900 ring-purple-600/20'
          : 'bg-amber-50 text-amber-900 ring-amber-600/20'
      }`}
    >
      <div className="flex items-start gap-3">
        <span className="mt-0.5 text-lg" aria-hidden="true">
          {isHigh ? '⚠' : '!'}
        </span>
        <div className="min-w-0 flex-1">
          <h3 className="text-sm font-semibold">
            {isHigh ? 'Professional review required' : 'Extra care recommended'}
          </h3>
          {note ? <p className="mt-1 text-sm">{note}</p> : null}
          {requirements.length > 0 ? (
            <ul className="mt-2 list-disc space-y-1 pl-5 text-sm">
              {requirements.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          ) : null}
          {isHigh ? (
            <p className="mt-2 text-sm font-medium">
              This tool never certifies a translation. Do not send AI output alone for this content.
            </p>
          ) : null}
        </div>
      </div>
    </div>
  );
}

interface CopyButtonProps {
  text: string;
  label?: string;
  className?: string;
}

export function CopyButton({ text, label = 'Copy', className = '' }: CopyButtonProps) {
  /** Copies text to the clipboard and reports the outcome in a live region. */
  const [state, setState] = useState<'idle' | 'copied' | 'failed'>('idle');

  const handleCopy = async () => {
    const ok = await copyToClipboard(text);
    setState(ok ? 'copied' : 'failed');
    setTimeout(() => setState('idle'), 2000);
  };

  return (
    <div className={`inline-flex items-center gap-2 ${className}`}>
      <button type="button" className="btn-secondary" onClick={() => void handleCopy()}>
        {label}
      </button>
      <span role="status" aria-live="polite" className="text-xs text-slate-600">
        {state === 'copied' ? 'Copied' : state === 'failed' ? 'Copy failed' : ''}
      </span>
    </div>
  );
}
