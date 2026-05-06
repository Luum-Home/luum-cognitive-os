import { Header } from "@/components/header";
import { StatCard } from "@/components/stat-card";
import { getCosStatus, getPrimitiveSurfaceCoverageSummary } from "@/lib/cos-api";

export const dynamic = "force-dynamic";

export default async function DashboardPage() {
  const [status, primitiveCoverage] = await Promise.all([
    getCosStatus(),
    getPrimitiveSurfaceCoverageSummary(),
  ]);

  return (
    <div>
      <Header
        title="Dashboard"
        description="Cognitive OS overview"
      />
      <div className="mt-8 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Rules" value={status.rulesCount} />
        <StatCard label="Hooks" value={status.hooksCount} />
        <StatCard label="Skills" value={status.skillsCount} />
        <StatCard label="Phase" value={status.phase} />
        <StatCard label="Primitive Surfaces" value={primitiveCoverage.totalPrimitives} />
        <StatCard label="Surface Gaps" value={primitiveCoverage.gaps} />
      </div>
      <div className="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-card)] p-6">
          <h2 className="text-lg font-semibold">Project</h2>
          <dl className="mt-4 space-y-3 text-sm">
            <div className="flex justify-between">
              <dt className="text-[var(--color-text-muted)]">Name</dt>
              <dd>{status.projectName}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-[var(--color-text-muted)]">Phase</dt>
              <dd className="capitalize">{status.phase}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-[var(--color-text-muted)]">Active Sessions</dt>
              <dd>{status.activeSessions}</dd>
            </div>
          </dl>
        </div>
        <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-card)] p-6">
          <h2 className="text-lg font-semibold">System</h2>
          <dl className="mt-4 space-y-3 text-sm">
            <div className="flex justify-between">
              <dt className="text-[var(--color-text-muted)]">COS Version</dt>
              <dd>{status.cosVersion}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-[var(--color-text-muted)]">Packages</dt>
              <dd>{status.packagesCount}</dd>
            </div>
          </dl>
        </div>
        <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-card)] p-6">
          <h2 className="text-lg font-semibold">Primitive Surface Coverage</h2>
          <dl className="mt-4 space-y-3 text-sm">
            <div className="flex justify-between">
              <dt className="text-[var(--color-text-muted)]">Consumes report</dt>
              <dd>{primitiveCoverage.consumesReport ? "yes" : "no"}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-[var(--color-text-muted)]">Mode</dt>
              <dd>{primitiveCoverage.mode}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-[var(--color-text-muted)]">Unclassified gaps</dt>
              <dd>{primitiveCoverage.unclassifiedGaps}</dd>
            </div>
          </dl>
        </div>
      </div>
    </div>
  );
}
