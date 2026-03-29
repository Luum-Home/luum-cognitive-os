import { Header } from "@/components/header";
import { getRules } from "@/lib/cos-api";

export const dynamic = "force-dynamic";

export default async function RulesPage() {
  const rules = await getRules();

  return (
    <div>
      <Header
        title="Rules"
        description={`${rules.length} rules loaded`}
      />
      <div className="mt-8">
        <div className="rounded-lg border border-[var(--color-border)] overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--color-border)] bg-[var(--color-bg-card)]">
                <th className="px-4 py-3 text-left font-medium text-[var(--color-text-muted)]">
                  Rule
                </th>
                <th className="px-4 py-3 text-left font-medium text-[var(--color-text-muted)]">
                  Source
                </th>
              </tr>
            </thead>
            <tbody>
              {rules.map((rule) => (
                <tr
                  key={rule.name}
                  className="border-b border-[var(--color-border)] hover:bg-[var(--color-bg-card)] transition-colors"
                >
                  <td className="px-4 py-3 font-medium">{rule.name}</td>
                  <td className="px-4 py-3 text-[var(--color-text-muted)] font-mono text-xs">
                    {rule.path}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
