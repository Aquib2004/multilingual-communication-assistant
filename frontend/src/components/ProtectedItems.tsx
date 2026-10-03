import { EmptyState } from '@/components/LoadingState';
import type { ProtectedItem } from '@/types';

interface ProtectedItemsProps {
  items: ProtectedItem[];
}

/**
 * Lists the facts that must survive translation unchanged.
 *
 * These are the items the engine will hold still: the value is replaced with a
 * placeholder before the model sees it, restored afterwards, and then checked.
 */
export function ProtectedItems({ items }: ProtectedItemsProps) {
  if (items.length === 0) {
    return (
      <EmptyState
        title="No protected items yet"
        description="Protected items appear here once the improved message is approved."
      />
    );
  }

  const exact = items.filter((item) => item.must_match_exactly);
  const semantic = items.filter((item) => !item.must_match_exactly);

  return (
    <div className="card" data-testid="protected-items">
      <h2 className="text-lg font-semibold text-slate-900">
        3. Information that must not change ({items.length})
      </h2>
      <p className="mt-1 text-sm text-slate-600">
        Each value below is held still during translation and checked afterwards.
      </p>

      {exact.length > 0 ? <GroupedItems title="Reproduced exactly" items={exact} /> : null}
      {semantic.length > 0 ? (
        <GroupedItems title="Meaning checked, wording may change" items={semantic} />
      ) : null}
    </div>
  );
}

function GroupedItems({ title, items }: { title: string; items: ProtectedItem[] }) {
  /** A titled group of protected items, so the table stays readable. */
  return (
    <div className="mt-4">
      <h3 className="text-sm font-semibold text-slate-800">{title}</h3>
      <div className="mt-2 overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-200 text-sm">
          <thead>
            <tr>
              <th scope="col" className="px-3 py-2 text-left font-medium text-slate-700">
                Type
              </th>
              <th scope="col" className="px-3 py-2 text-left font-medium text-slate-700">
                Value
              </th>
              <th scope="col" className="px-3 py-2 text-left font-medium text-slate-700">
                Placeholder
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {items.map((item) => (
              <tr key={item.id}>
                <td className="px-3 py-2 text-slate-600">{item.item_type}</td>
                <td className="px-3 py-2 font-medium text-slate-900">
                  <code className="rounded bg-slate-100 px-1.5 py-0.5">{item.value}</code>
                </td>
                <td className="px-3 py-2 text-slate-500">
                  <code>{item.placeholder}</code>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
