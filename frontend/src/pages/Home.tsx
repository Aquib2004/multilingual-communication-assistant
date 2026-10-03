import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import { api } from '@/services/api';
import type { ExampleMessage, HealthResponse } from '@/types';

const BRIDGE = [
  ['B', 'Begin with purpose', 'Name the audience, purpose, action, deadline, and contact path.'],
  ['R', 'Rewrite plainly', 'Short sentences, concrete verbs, explicit deadlines.'],
  ['I', 'Identify protected items', 'Dates, names, URLs, and numbers that must not change.'],
  ['D', 'Draft with context', 'Language, locale, tone, and reading level.'],
  ['G', 'Gauge meaning', 'Fact map, back-translation, tone and terminology review.'],
  ['E', 'Escalate when needed', 'The greater the consequence, the more thorough the review.'],
] as const;

/**
 * The landing page: what this is, whether it is reachable, and a way to start.
 *
 * The status comes from the real API, so a contributor can see whether the
 * backend is up before beginning work.
 */
export function Home() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [unreachable, setUnreachable] = useState(false);
  const [examples, setExamples] = useState<ExampleMessage[]>([]);

  useEffect(() => {
    let cancelled = false;
    api
      .getHealth()
      .then((data) => {
        if (!cancelled) setHealth(data);
      })
      .catch(() => {
        if (!cancelled) setUnreachable(true);
      });
    api
      .getExamples()
      .then((data) => {
        if (!cancelled) setExamples(data.items.slice(0, 3));
      })
      .catch(() => {
        /* Examples are optional on the landing page. */
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="mx-auto max-w-4xl space-y-8">
      <section className="card">
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">
          Reach every family in their language
        </h1>
        <p className="mt-2 text-slate-700">
          Turn a routine message into a clear, welcoming source, translate it into two or three
          languages, and <strong>verify</strong> that the dates, deadlines, actions, and contact
          paths survived. This is a verification-first pipeline, not a text translator.
        </p>
        <p className="mt-3 rounded-lg bg-purple-50 p-3 text-sm text-purple-900 ring-1 ring-inset ring-purple-600/20">
          This tool never certifies a translation. For safety, health, legal rights, discipline,
          disability services, or emergencies, use your organisation&rsquo;s approved professional
          translation or interpretation process.
        </p>
        <div className="mt-5 flex flex-wrap gap-3">
          <Link to="/workspace" className="btn-primary">
            Open the workspace
          </Link>
          <Link to="/history" className="btn-secondary">
            Past messages
          </Link>
        </div>
      </section>

      <section aria-label="Service status">
        <h2 className="text-lg font-semibold text-slate-900">Service status</h2>
        {unreachable ? (
          <p
            role="alert"
            className="mt-2 rounded-lg bg-red-50 p-4 text-sm text-red-900 ring-1 ring-inset ring-red-600/20"
          >
            The backend is not reachable. Start it with{' '}
            <code className="rounded bg-red-100 px-1">uvicorn app.main:app --reload</code> from the{' '}
            <code className="rounded bg-red-100 px-1">backend</code> directory.
          </p>
        ) : health ? (
          <dl className="mt-2 grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
            {(
              [
                ['Status', health.status],
                ['AI provider', health.ai_provider],
                ['Database', health.database],
                ['Version', health.version],
              ] as const
            ).map(([label, value]) => (
              <div key={label} className="card">
                <dt className="text-xs text-slate-600">{label}</dt>
                <dd className="font-semibold text-slate-900">{value}</dd>
              </div>
            ))}
          </dl>
        ) : (
          <p className="mt-2 text-sm text-slate-600">Checking…</p>
        )}
      </section>

      <section aria-label="The BRIDGE workflow">
        <h2 className="text-lg font-semibold text-slate-900">The BRIDGE workflow</h2>
        <ol className="mt-2 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {BRIDGE.map(([letter, title, detail]) => (
            <li key={letter} className="card">
              <span className="inline-flex h-7 w-7 items-center justify-center rounded-full bg-blue-100 text-sm font-bold text-blue-800">
                {letter}
              </span>
              <h3 className="mt-2 text-sm font-semibold text-slate-900">{title}</h3>
              <p className="mt-1 text-sm text-slate-600">{detail}</p>
            </li>
          ))}
        </ol>
      </section>

      {examples.length > 0 ? (
        <section aria-label="Example messages">
          <h2 className="text-lg font-semibold text-slate-900">Try an example</h2>
          <p className="mt-1 text-sm text-slate-600">
            Every bundled example is fictional and de-identified.
          </p>
          <ul className="mt-2 space-y-2">
            {examples.map((example) => (
              <li key={example.id} className="card">
                <h3 className="text-sm font-semibold text-slate-900">{example.title}</h3>
                <p className="mt-1 text-sm text-slate-600">{example.source_message}</p>
                <Link
                  to="/workspace"
                  className="mt-2 inline-block text-sm font-medium text-blue-700 hover:underline"
                >
                  Open in workspace
                </Link>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  );
}
