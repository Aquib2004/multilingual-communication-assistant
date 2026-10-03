import { useEffect, useState } from 'react';

import { api } from '@/services/api';
import type { LanguageInfo } from '@/types';

interface LanguageSelectorProps {
  selected: string[];
  onChange: (codes: string[]) => void;
  /** The workflow requires at least two target languages. */
  minLanguages?: number;
  maxLanguages?: number;
}

export function LanguageSelector({
  selected,
  onChange,
  minLanguages = 2,
  maxLanguages = 3,
}: LanguageSelectorProps) {
  /**
   * Target-language selector.
   *
   * The minimum is enforced in the UI so the user cannot reach a request the
   * backend would reject, and the count is shown explicitly because the
   * workflow genuinely needs two or three languages.
   */
  const [languages, setLanguages] = useState<LanguageInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .getLanguages()
      .then((data) => {
        if (!cancelled) setLanguages(data.targets);
      })
      .catch(() => {
        if (!cancelled) setError('Could not load the language list.');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const toggle = (code: string) => {
    if (selected.includes(code)) {
      onChange(selected.filter((item) => item !== code));
      return;
    }
    if (selected.length >= maxLanguages) return;
    onChange([...selected, code]);
  };

  if (loading) return <p className="text-sm text-slate-600">Loading languages…</p>;
  if (error) return <p className="text-sm text-red-700">{error}</p>;

  const atMinimum = selected.length < minLanguages;

  return (
    <fieldset>
      <legend className="field-label">
        Target languages
        <span className="ml-2 font-normal text-slate-600">
          Choose {minLanguages} to {maxLanguages}
        </span>
      </legend>

      <div className="mt-2 flex flex-wrap gap-2">
        {languages.map((language) => {
          const isSelected = selected.includes(language.code);
          const atMax = !isSelected && selected.length >= maxLanguages;
          return (
            <label
              key={language.code}
              className={`inline-flex cursor-pointer items-center gap-2 rounded-lg px-3 py-2 text-sm ring-1 ring-inset ${
                isSelected
                  ? 'bg-blue-50 text-blue-900 ring-blue-600/30'
                  : 'bg-white text-slate-700 ring-slate-300'
              } ${atMax ? 'cursor-not-allowed opacity-50' : ''}`}
            >
              <input
                type="checkbox"
                className="h-4 w-4 rounded border-slate-300 text-blue-700"
                checked={isSelected}
                disabled={atMax}
                onChange={() => toggle(language.code)}
              />
              <span>
                {language.name}
                <span className="ml-1 text-xs text-slate-500">({language.english_name})</span>
              </span>
            </label>
          );
        })}
      </div>

      {atMinimum ? (
        <p role="alert" className="mt-2 text-sm text-amber-800">
          Select at least {minLanguages} target languages. English is the source language, so it
          cannot be a target.
        </p>
      ) : null}
    </fieldset>
  );
}

interface LocaleSelectorProps {
  value: string;
  onChange: (tag: string) => void;
  locales?: string[];
}

const LOCALE_LABELS: Record<string, string> = {
  'en-US': 'English (United States)',
  'es-US': 'Spanish (United States)',
  'es-MX': 'Spanish (Mexico)',
  'hi-IN': 'Hindi (India)',
  'ur-PK': 'Urdu (Pakistan)',
};

export function LocaleSelector({
  value,
  onChange,
  locales = Object.keys(LOCALE_LABELS),
}: LocaleSelectorProps) {
  /**
   * Locale selector. The locale decides date order and time format, so a
   * wrong choice here can make an ambiguous date pass unnoticed.
   */
  return (
    <div>
      <label className="field-label" htmlFor="locale-select">
        Locale
      </label>
      <select
        id="locale-select"
        className="field-input"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      >
        {locales.map((tag) => (
          <option key={tag} value={tag}>
            {LOCALE_LABELS[tag] ?? tag}
          </option>
        ))}
      </select>
      <p className="mt-1 text-xs text-slate-600">
        Used to interpret dates and times. The API also reports these.
      </p>
    </div>
  );
}
