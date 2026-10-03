/** Presentation helpers shared across components. */

import type { MessageState, RiskLevel, VerificationStatus } from '@/types';

export interface StatusStyle {
  label: string;
  /** Icon glyph. Status is never conveyed by colour alone. */
  icon: string;
  textClass: string;
  badgeClass: string;
}

const STATUS_STYLES: Record<VerificationStatus, StatusStyle> = {
  PASS: {
    label: 'Pass',
    icon: '✓',
    textClass: 'text-status-pass',
    badgeClass: 'bg-green-50 text-green-800 ring-green-600/20',
  },
  WARNING: {
    label: 'Warning',
    icon: '!',
    textClass: 'text-status-warning',
    badgeClass: 'bg-amber-50 text-amber-800 ring-amber-600/20',
  },
  FAIL: {
    label: 'Fail',
    icon: '✕',
    textClass: 'text-status-fail',
    badgeClass: 'bg-red-50 text-red-800 ring-red-600/20',
  },
  REVIEW: {
    label: 'Review required',
    icon: '?',
    textClass: 'text-status-review',
    badgeClass: 'bg-blue-50 text-blue-800 ring-blue-600/20',
  },
  ESCALATED: {
    label: 'Escalated',
    icon: '⚠',
    textClass: 'text-status-escalated',
    badgeClass: 'bg-purple-50 text-purple-800 ring-purple-600/20',
  },
};

const FALLBACK_STYLE: StatusStyle = {
  label: 'Unknown',
  icon: '·',
  textClass: 'text-slate-600',
  badgeClass: 'bg-slate-100 text-slate-800 ring-slate-500/20',
};

export function statusStyle(status: string): StatusStyle {
  /** Look up the visual treatment for a verification status. */
  return STATUS_STYLES[status as VerificationStatus] ?? FALLBACK_STYLE;
}

export const RISK_LABELS: Record<RiskLevel, string> = {
  routine: 'Routine',
  moderate: 'Moderate consequence',
  high: 'High consequence',
};

export const RISK_DESCRIPTIONS: Record<RiskLevel, string> = {
  routine: 'A welcome note, event reminder, or classroom update.',
  moderate: 'Permission, schedule change, or participation instructions.',
  high: 'Safety, health, legal rights, discipline, or disability services.',
};

export const STATE_LABELS: Record<MessageState, string> = {
  draft: 'Draft',
  revised: 'Awaiting your approval',
  approved: 'Approved for translation',
  translated: 'Translated',
  verified: 'Verified',
  escalated: 'Escalated to professional review',
};

/** Ordered BRIDGE stages, used to render the pipeline stepper. */
export const PIPELINE_STAGES = [
  { key: 'source', label: 'Source' },
  { key: 'rewrite', label: 'Plain language' },
  { key: 'approve', label: 'Your approval' },
  { key: 'protected', label: 'Protected items' },
  { key: 'translate', label: 'Translation' },
  { key: 'verify', label: 'Verification' },
  { key: 'risk', label: 'Risk and escalation' },
] as const;

export type PipelineStageKey = (typeof PIPELINE_STAGES)[number]['key'];

/**
 * How far through the pipeline the workspace is.
 *
 * The approval stage is deliberately its own step: the UI must make it obvious
 * that translation is blocked until it is passed.
 *
 * @param state The workspace state.
 * @param translationCount How many translations exist. Zero means translation
 *   has not run yet, even if the message is already approved.
 */
export function currentStage(state: MessageState, translationCount: number): number {
  switch (state) {
    case 'draft':
      return 0;
    case 'revised':
      return 1;
    case 'approved':
      return 3;
    case 'translated':
      return translationCount > 0 ? 4 : 3;
    case 'verified':
      return 5;
    case 'escalated':
      return 6;
    default:
      return 0;
  }
}

/** Copy text to the clipboard, reporting whether it worked. */
export async function copyToClipboard(text: string): Promise<boolean> {
  try {
    if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch {
    // Fall through: the caller shows a failure message.
  }
  return false;
}
