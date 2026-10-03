import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { RewriteResult } from '@/components/RewriteResult';
import type { RewriteResponse } from '@/types';

const REWRITE: RewriteResponse = {
  message_id: 'm1',
  rewritten_message: 'Students should return the form by Friday, September 18.',
  changes: [
    {
      original: 'Students are expected to return',
      revised: 'Students should return',
      reason: "Named the actor and used a direct verb instead of 'are expected to'.",
    },
  ],
  open_questions: ['The source has no usable deadline. Add a real date.'],
  reading_level: {},
  pii_warnings: [],
  state: 'revised',
  provider: 'mock',
  model: 'mock-rule-engine-1.0',
};

function renderResult(overrides: Partial<Parameters<typeof RewriteResult>[0]> = {}) {
  const props = {
    rewrite: REWRITE,
    onApprove: vi.fn(),
    onReject: vi.fn(),
    onEdit: vi.fn(),
    isApproved: false,
    ...overrides,
  };
  render(<RewriteResult {...props} />);
  return props;
}

describe('RewriteResult', () => {
  it('shows an empty state before a rewrite has run', () => {
    renderResult({ rewrite: null });
    expect(screen.getByText('No revision yet')).toBeInTheDocument();
  });

  it('lists every change with its reason', () => {
    renderResult();
    expect(screen.getByTestId('change-summary')).toHaveTextContent(
      'Named the actor and used a direct verb',
    );
  });

  it('surfaces open questions that must be answered before translating', () => {
    renderResult();
    expect(screen.getByText(/no usable deadline/)).toBeInTheDocument();
  });

  it('offers the approval control when the source is not yet approved', () => {
    renderResult();
    expect(screen.getByTestId('approve-button')).toBeInTheDocument();
    expect(screen.queryByTestId('approved-badge')).not.toBeInTheDocument();
  });

  it('hides the approval control and shows the approved state once approved', () => {
    renderResult({ isApproved: true });
    expect(screen.queryByTestId('approve-button')).not.toBeInTheDocument();
    expect(screen.getByTestId('approved-badge')).toBeInTheDocument();
  });

  it('calls onApprove when the approve button is pressed', async () => {
    const props = renderResult();
    await userEvent.click(screen.getByTestId('approve-button'));
    expect(props.onApprove).toHaveBeenCalled();
  });

  it('warns about personal data that looks real', () => {
    renderResult({
      rewrite: {
        ...REWRITE,
        pii_warnings: [
          { category: 'email', excerpt: 'mramirez@real-school.org', severity: 'warning' },
        ],
      },
    });
    expect(screen.getByText('Possible personal data found')).toBeInTheDocument();
  });
});
