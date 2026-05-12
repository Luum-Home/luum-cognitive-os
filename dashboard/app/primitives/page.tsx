import { Header } from "@/components/header";
import {
  getPrimitiveProjectionFidelitySummary,
  getPrimitiveServiceHeadlessSmokeSummary,
  getPortableAiConsumerSmokeSummary,
  getOpenCodePrimitiveAdapterSmokeSummary,
  getPrimitiveSurfaceCoverageSummary,
  getPrimitiveProjectionDrilldown,
  getPrimitiveRuntimeEvidenceSummary,
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
  const [coverage, fidelity, openCode, consumer, headless, projectionRows, runtimeEvidence] = await Promise.all([
    getPrimitiveSurfaceCoverageSummary(),
    getPrimitiveProjectionFidelitySummary(),
    getOpenCodePrimitiveAdapterSmokeSummary(),
    getPortableAiConsumerSmokeSummary(),
    getPrimitiveServiceHeadlessSmokeSummary(),
    getPrimitiveProjectionDrilldown(),
    getPrimitiveRuntimeEvidenceSummary(),
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



      <div className="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-card)] p-6">
          <h2 className="text-lg font-semibold">Runtime Session Drilldown</h2>
          <p className="mt-2 text-sm text-[var(--color-text-muted)]">Ledger + itinerary rows grouped by session, content-free.</p>
          <dl className="mt-4 text-sm">
            <KeyValue label="Intervention rows" value={runtimeEvidence.interventionRows} />
            <KeyValue label="Itinerary rows" value={runtimeEvidence.itineraryRows} />
            <KeyValue label="Observed primitives" value={runtimeEvidence.interventionPrimitives} />
          </dl>
          <div className="mt-4 space-y-3 text-sm">
            {runtimeEvidence.sessions.length === 0 ? <p>No runtime sessions found.</p> : runtimeEvidence.sessions.map((row) => (
              <div key={row.sessionId} className="rounded border border-[var(--color-border)] p-3">
                <div className="font-medium">{row.sessionId}</div>
                <div className="text-[var(--color-text-muted)]">interventions={row.interventions} itinerary={row.itineraryEvents}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-card)] p-6">
          <h2 className="text-lg font-semibold">Promotion Gaps</h2>
          <p className="mt-2 text-sm text-[var(--color-text-muted)]">Qué falta para promover: harnesses no alineados o pendientes de runtime smoke por contrato.</p>
          <div className="mt-4 space-y-3 text-sm">
            {projectionRows.filter((row) => row.pendingReasons.length > 0).slice(0, 12).map((row) => (
              <div key={row.contractId} className="rounded border border-[var(--color-border)] p-3">
                <div className="font-medium">{row.contractId}</div>
                <div className="text-[var(--color-text-muted)]">{row.pendingReasons.join(", ")}</div>
                <code className="text-xs">{row.contractPath}</code>
              </div>
            ))}
            {projectionRows.every((row) => row.pendingReasons.length === 0) ? <p>No promotion gaps in the latest projection report.</p> : null}
          </div>
        </div>
      </div>

      <div className="mt-8 rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-card)] p-6">
        <h2 className="text-lg font-semibold">Evidence Links</h2>
        <p className="mt-2 text-sm text-[var(--color-text-muted)]">Release operators can jump from this dashboard to the signed reports and contracts that prove registry-backed vs lifecycle-derived primitive state.</p>
        <ul className="mt-4 list-disc space-y-2 pl-5 text-sm">
          <li><code>{fidelity.reportPath}</code></li>
          <li><code>{openCode.reportPath}</code></li>
          <li><code>docs/06-Daily/reports/portable-ai-consumer-smoke-latest.json</code></li>
          <li><code>docs/06-Daily/reports/portable-ai-real-consumer-smoke-latest.json</code></li>
          <li><code>docs/06-Daily/reports/primitive-service-headless-smoke-latest.json</code></li>
          <li><code>manifests/primitive-contracts.yaml</code></li>
          {runtimeEvidence.reportPaths.map((path) => <li key={path}><code>{path}</code></li>)}
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
