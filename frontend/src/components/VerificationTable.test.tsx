import { render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { VerificationTable } from '@/components/VerificationTable';
import type { VerificationReport } from '@/types';

const REPORT: VerificationReport = {
  id: 'r1',
  message_id: 'm1',
  translation_id: 't1',
  target_language: 'es',
  overall_status: 'FAIL',
  human_review_required: true,
  summary: { total: 3, passed: 1, warnings: 0, failures: 1, review_required: 1 },
  checks: [
    {
      item_type: 'time',
      source: '8:30 a.m.',
      translated: '8:00',
      status: 'FAIL',
      detail: 'The translation states 8:00, which is not the same time as 8:30 a.m.',
    },
    {
      item_type: 'date',
      source: 'September 8',
      translated: '8 de septiembre',
      status: 'PASS',
      detail: 'The same calendar date is present.',
    },
    {
      item_type: 'action',
      source: 'Please bring',
      translated: 'Por favor traiga',
      status: 'REVIEW',
      detail: 'A fluent reviewer must confirm the meaning was preserved.',
    },
  ],
  back_translation: [
    {
      source_sentence: 'Please bring the form on September 8.',
      back_translated: 'Please bring the form on September 8.',
      status: 'PASS',
      detail: 'The action and deadline came back unchanged.',
    },
  ],
  tone_assessment: {
    tone: 'welcoming',
    mechanical_phrases: [],
    cultural_awkwardness: [],
    terminology_notes: ["'conference': confirm the local sense."],
    status: 'REVIEW',
  },
  issues: [
    {
      severity: 'error',
      code: 'FACT_MISMATCH',
      message: 'time: the translation states 8:00, which is not 8:30 a.m.',
    },
  ],
  risk: { level: 'routine', declared_by_user: null, evidence: [], review_requirements: [] },
  escalation_note: null,
  review_requirements: [],
  provider: 'mock',
  model: 'mock-rule-engine-1.0',
  verified_at: '2026-01-01T00:00:00Z',
  created_at: '2026-01-01T00:00:00Z',
};

describe('VerificationTable', () => {
  it('shows an empty state before anything is verified', () => {
    render(<VerificationTable report={null} />);
    expect(screen.getByText('Nothing verified yet')).toBeInTheDocument();
  });

  it('renders the overall status and the summary counts', () => {
    render(<VerificationTable report={REPORT} />);

    expect(screen.getByTestId('verification-table')).toBeInTheDocument();
    // The overall status badge sits in the report header.
    const header = screen.getByRole('heading', { name: '5. Verification' }).closest('.card');
    expect(header).not.toBeNull();
    expect(within(header as HTMLElement).getByText('Fail')).toBeInTheDocument();
    expect(screen.getByText('Checked')).toBeInTheDocument();
  });

  it('lists the failing check first so a green row cannot hide a red one', () => {
    render(<VerificationTable report={REPORT} />);

    const rows = screen.getAllByTestId('fact-row');
    expect(rows[0]).toHaveTextContent('time');
    expect(rows[0]).toHaveTextContent('Fail');
  });

  it('shows the back-translation of the critical lines', () => {
    render(<VerificationTable report={REPORT} />);
    expect(screen.getByText(/Back-translation of the critical lines/)).toBeInTheDocument();
  });

  it('always states that a human must confirm before sending', () => {
    render(<VerificationTable report={REPORT} />);
    expect(screen.getByText(/A fluent reviewer must confirm this translation/)).toBeInTheDocument();
  });

  it('shows the escalation notice for high-risk content', () => {
    const high: VerificationReport = {
      ...REPORT,
      risk: { ...REPORT.risk, level: 'high' },
      escalation_note:
        'Professional human translation or interpretation is recommended for this high-consequence message.',
    };
    render(<VerificationTable report={high} />);

    const notice = screen.getByTestId('escalation-notice');
    expect(notice).toHaveTextContent('Professional review required');
    expect(notice).toHaveTextContent(/never certifies a translation/);
  });
});
