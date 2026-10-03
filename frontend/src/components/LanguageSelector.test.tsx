import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { LanguageSelector } from '@/components/LanguageSelector';
import { api } from '@/services/api';

vi.mock('@/services/api', async () => {
  const actual = await vi.importActual<typeof import('@/services/api')>('@/services/api');
  return {
    ...actual,
    api: {
      getLanguages: vi.fn(),
      getExamples: vi.fn(),
    },
  };
});

const mockedApi = vi.mocked(api);

describe('LanguageSelector', () => {
  beforeEach(() => {
    mockedApi.getLanguages.mockResolvedValue({
      source: {
        code: 'en',
        name: 'English',
        english_name: 'English',
        script: 'Latin',
        direction: 'ltr',
        reading_level_hint: '',
        term_support: 'full',
      },
      targets: [
        {
          code: 'es',
          name: 'Español',
          english_name: 'Spanish',
          script: 'Latin',
          direction: 'ltr',
          reading_level_hint: '',
          term_support: 'full',
        },
        {
          code: 'hi',
          name: 'हिन्दी',
          english_name: 'Hindi',
          script: 'Devanagari',
          direction: 'ltr',
          reading_level_hint: '',
          term_support: 'full',
        },
        {
          code: 'ur',
          name: 'اردو',
          english_name: 'Urdu',
          script: 'Arabic',
          direction: 'rtl',
          reading_level_hint: '',
          term_support: 'partial',
        },
      ],
      locales: ['en-US'],
    });
  });

  it('renders every registered target language', async () => {
    render(<LanguageSelector selected={['es']} onChange={vi.fn()} />);

    expect(await screen.findByText('Español')).toBeInTheDocument();
    expect(screen.getByText(/Hindi/)).toBeInTheDocument();
    expect(screen.getByText(/Urdu/)).toBeInTheDocument();
  });

  it('warns when fewer than the minimum number of languages is chosen', async () => {
    render(<LanguageSelector selected={['es']} onChange={vi.fn()} minLanguages={2} />);

    expect(await screen.findByText(/Select at least 2 target languages/)).toBeInTheDocument();
  });

  it('does not warn once the minimum is met', async () => {
    render(<LanguageSelector selected={['es', 'hi']} onChange={vi.fn()} minLanguages={2} />);

    await screen.findByText('Español');
    expect(screen.queryByText(/Select at least 2 target languages/)).not.toBeInTheDocument();
  });

  it('adds a language when its checkbox is toggled', async () => {
    const onChange = vi.fn();
    render(<LanguageSelector selected={['es']} onChange={onChange} />);

    const hindi = await screen.findByText(/Hindi/);
    await userEvent.click(hindi);

    expect(onChange).toHaveBeenCalledWith(['es', 'hi']);
  });

  it('removes a language when its checkbox is toggled off', async () => {
    const onChange = vi.fn();
    render(<LanguageSelector selected={['es', 'hi']} onChange={onChange} />);

    const spanish = await screen.findByText('Español');
    await userEvent.click(spanish);

    expect(onChange).toHaveBeenCalledWith(['hi']);
  });

  it('shows an error when the language list cannot be loaded', async () => {
    mockedApi.getLanguages.mockRejectedValueOnce(new Error('offline'));
    render(<LanguageSelector selected={[]} onChange={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText('Could not load the language list.')).toBeInTheDocument();
    });
  });
});
