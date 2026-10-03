import { NavLink, Route, Routes } from 'react-router-dom';

import { History } from '@/pages/History';
import { Home } from '@/pages/Home';
import { Workspace } from '@/pages/Workspace';

const NAV = [
  { to: '/', label: 'Home', end: true },
  { to: '/workspace', label: 'Workspace', end: false },
  { to: '/history', label: 'History', end: false },
] as const;

export default function App() {
  /**
   * The application shell: a skip link, the header, and the three routes.
   *
   * The skip link and visible focus rings exist because this tool is used by
   * people who are often keyboard-only.
   */
  return (
    <div className="min-h-screen">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-blue-700 focus:px-4 focus:py-2 focus:text-white"
      >
        Skip to main content
      </a>

      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-4 px-4 py-4">
          <div className="flex items-center gap-3">
            <span
              className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-blue-700 text-sm font-bold text-white"
              aria-hidden="true"
            >
              BR
            </span>
            <div>
              <p className="text-sm font-semibold text-slate-900">
                Multilingual Communication Assistant
              </p>
              <p className="text-xs text-slate-500">Reach every family in their language</p>
            </div>
          </div>

          <nav aria-label="Main">
            <ul className="flex gap-1">
              {NAV.map((item) => (
                <li key={item.to}>
                  <NavLink
                    to={item.to}
                    end={item.end}
                    className={({ isActive }) =>
                      `rounded-lg px-3 py-2 text-sm font-medium ${
                        isActive
                          ? 'bg-blue-50 text-blue-800'
                          : 'text-slate-700 hover:bg-slate-100'
                      }`
                    }
                  >
                    {item.label}
                  </NavLink>
                </li>
              ))}
            </ul>
          </nav>
        </div>
      </header>

      <main id="main" className="px-4 py-8">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/workspace" element={<Workspace />} />
          <Route path="/history" element={<History />} />
          <Route
            path="*"
            element={
              <div className="card">
                <h1 className="text-lg font-semibold text-slate-900">Page not found</h1>
                <p className="mt-1 text-sm text-slate-600">
                  That page does not exist. Use the navigation above to continue.
                </p>
              </div>
            }
          />
        </Routes>
      </main>

      <footer className="border-t border-slate-200 bg-white">
        <div className="mx-auto max-w-5xl px-4 py-6 text-xs text-slate-500">
          <p>
            This tool never certifies a translation. High-consequence content (safety, health,
            legal rights, discipline, disability services, emergencies) must go through your
            organisation&rsquo;s approved professional translation or interpretation process.
          </p>
          <p className="mt-2">
            Use fictional or de-identified content only. No real names, phone numbers, or student
            IDs.
          </p>
        </div>
      </footer>
    </div>
  );
}
