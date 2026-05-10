import { Header } from "@/components/header";
import {
  getPrimitiveProjectionFidelitySummary,
  getPrimitiveServiceHeadlessSmokeSummary,
  getPortableAiConsumerSmokeSummary,
  getOpenCodePrimitiveAdapterSmokeSummary,
  getPrimitiveSurfaceCoverageSummary,
} from "@/lib/cos-api";

export const dynamic = "force-dynamic";

function KeyValue({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex justify-between gap-4 border-b border-[var(--color-border)] py-2 last:border-0">
      <dt className="text-[var(--color-text-muted)]">{label}</dt>
      <dd className="text-right font-medium">{value}</dd>
    </div>
  );
}

function JsonTable({ title, values }: { title: string; values: Record<string, number> }) {
  const entries = Object.entries(values).sort(([a], [b]) => a.localeCompare(b));
  return (
    <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-card)] p-6">
      <h2 className="text-lg font-semibold">{title}</h2>
      <dl className="mt-4 text-sm">
        {entries.length === 0 ? (
          <KeyValue label="No data" value="0" />
        ) : (
          entries.map(([key, value]) => <KeyValue key={key} label={key} value={value} />)
        )}
      </dl>
    </div>
  );
}

export default async function PrimitivesPage() {
  const [coverage, fidelity, openCode, consumer, headless] = await Promise.all([
    getPrimitiveSurfaceCoverageSummary(),
    getPrimitiveProjectionFidelitySummary(),
    getOpenCodePrimitiveAdapterSmokeSummary(),
    getPortableAiConsumerSmokeSummary(),
    getPrimitiveServiceHeadlessSmokeSummary(),
  ]);

  return (
    <div>
      <Header
        title="Primitive Runtime"
        description="Observable primitive contracts, IDE projection fidelity, .ai consumer overlay, and headless/runtime smoke evidence."
      />

      <div className="mt-8 grid grid-cols-1 gap-6 sm:grid-cols-2 xl:grid-cols-4">
        <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-card)] p-6">
          <h2 className="text-lg font-semibold">Registry + Projection</h2>
          <dl className="mt-4 text-sm">
            <KeyValue label="Contracts" value={fidelity.contracts} />
            <KeyValue label="Projection rows" value={fidelity.projectionRows} />
            <KeyValue label="Aligned" value={fidelity.aligned} />
            <KeyValue label="Gaps" value={fidelity.gaps} />
            <KeyValue label="Pending runtime smoke" value={fidelity.pendingRuntimeSmoke} />
            <KeyValue label="Pending contracts" value={fidelity.pendingContracts.length} />
          </dl>
        </div>

        <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-card)] p-6">
          <h2 className="text-lg font-semibold">Surface Coverage</h2>
          <dl className="mt-4 text-sm">
            <KeyValue label="Primitives" value={coverage.totalPrimitives} />
            <KeyValue label="Gaps" value={coverage.gaps} />
            <KeyValue label="Unclassified" value={coverage.unclassifiedGaps} />
            <KeyValue label="Mode" value={coverage.mode} />
          </dl>
        </div>

        <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-card)] p-6">
          <h2 className="text-lg font-semibold">OpenCode Runtime Smoke</h2>
          <dl className="mt-4 text-sm">
            <KeyValue label="Status" value={openCode.status} />
            <KeyValue label="Version" value={openCode.version || "unavailable"} />
            <KeyValue label="Supported primitives" value={openCode.supportedPrimitives} />
            <KeyValue label="Ledger rows" value={openCode.ledgerRows} />
            <KeyValue label="Events" value={openCode.events.join(", ") || "none"} />
          </dl>
        </div>

        <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-card)] p-6">
          <h2 className="text-lg font-semibold">Consumer + Headless</h2>
          <dl className="mt-4 text-sm">
            <KeyValue label=".ai smoke" value={consumer.status} />
            <KeyValue label="Overlay files" value={consumer.overlayFiles} />
            <KeyValue label="Registry-backed" value={consumer.registryBacked} />
            <KeyValue label="Lifecycle-derived" value={consumer.lifecycleDerived} />
            <KeyValue label="Headless smoke" value={headless.status} />
            <KeyValue label="Headless ledger rows" value={headless.ledgerRows} />
          </dl>
        </div>
      </div>

      <div className="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-2">
        <JsonTable title="Surfaces by Kind" values={coverage.surfacesByKind} />
        <JsonTable title="Projected or Wired by Surface" values={coverage.surfaceProjectedOrWired} />
        <JsonTable title="Harness Projection Rows" values={fidelity.harnessStatus} />
        <JsonTable title="Projection Status Filters" values={fidelity.fidelityStatus} />
      </div>

      <div className="mt-8 rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-card)] p-6">
        <h2 className="text-lg font-semibold">Evidence Links</h2>
        <p className="mt-2 text-sm text-[var(--color-text-muted)]">Release operators can jump from this dashboard to the signed reports and contracts that prove registry-backed vs lifecycle-derived primitive state.</p>
        <ul className="mt-4 list-disc space-y-2 pl-5 text-sm">
          <li><code>{fidelity.reportPath}</code></li>
          <li><code>{openCode.reportPath}</code></li>
          <li><code>docs/reports/portable-ai-consumer-smoke-latest.json</code></li>
          <li><code>docs/reports/primitive-service-headless-smoke-latest.json</code></li>
          <li><code>manifests/primitive-contracts.yaml</code></li>
        </ul>
        {fidelity.pendingContracts.length > 0 ? (
          <p className="mt-4 text-sm text-[var(--color-text-muted)]">Pending contracts: {fidelity.pendingContracts.join(", ")}</p>
        ) : (
          <p className="mt-4 text-sm font-medium">No pending primitive projection contracts in the latest report.</p>
        )}
      </div>
    </div>
  );
}
