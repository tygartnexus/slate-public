import Link from "next/link";

import {
  getVerdict,
  listVerdicts,
  type VerdictDetail,
  type VerdictSummary,
} from "@/lib/api";
import { getDashboardAuth } from "@/lib/auth";

interface PageProps {
  searchParams: Promise<{ left?: string; right?: string }>;
}

interface Failure {
  signal?: string;
  frame?: string;
  description?: string;
}

interface ResponseQuality {
  facts?: string[];
  assumptions?: string[];
  unknowns?: string[];
  confidence_score?: number;
  evidence?: string[];
  risks?: string[];
  counterarguments?: string[];
  recommendation?: string;
  tradeoffs?: string[];
  what_would_change_recommendation?: string[];
}

interface PanelPayload {
  publish_ready?: boolean;
  per_persona?: { name?: string; publish_ready?: boolean; flags?: unknown[] }[];
  fused_critical_flags?: unknown[];
  fused_high_flags?: unknown[];
  response_quality?: ResponseQuality | null;
}

export default async function ComparePage({ searchParams }: PageProps) {
  const params = await searchParams;
  const { token } = await getDashboardAuth();
  const verdicts = token ? await listVerdicts(token) : [];

  const leftId = params.left ?? verdicts[0]?.id;
  const rightId =
    params.right ?? verdicts.find((verdict) => verdict.id !== leftId)?.id;

  const [left, right] =
    token && leftId && rightId
      ? await Promise.all([getVerdict(token, leftId), getVerdict(token, rightId)])
      : [null, null];

  if (verdicts.length < 2 || !left || !right) {
    return (
      <div>
        <h1 className="mb-4 text-2xl font-semibold">Compare verdicts</h1>
        <div className="rounded-lg border border-zinc-800 bg-slate-surface p-10 text-center text-zinc-400">
          <p className="mb-2">Upload at least two verdicts to compare runs.</p>
          <p className="text-sm">
            The comparison view evaluates status, failures, quality-score drift,
            response-quality sections, and Panel coverage between two saved
            verdicts.
          </p>
        </div>
      </div>
    );
  }

  const leftSummary = summarizeVerdict(left);
  const rightSummary = summarizeVerdict(right);
  const qualityKeys = Array.from(
    new Set([
      ...Object.keys(leftSummary.qualityScores),
      ...Object.keys(rightSummary.qualityScores),
    ]),
  ).sort();

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Compare verdicts</h1>
          <p className="mt-2 text-sm text-zinc-500">
            Side-by-side status, failure, quality, response-quality, and Panel
            drift for two uploaded Slate runs.
          </p>
        </div>
        <Link href="/dashboard" className="text-sm text-slate-accent">
          Back to verdicts
        </Link>
      </div>

      <section className="mb-8 grid gap-4 md:grid-cols-2">
        <VerdictPicker
          label="Left run"
          side="left"
          selectedId={left.id}
          otherId={right.id}
          verdicts={verdicts}
        />
        <VerdictPicker
          label="Right run"
          side="right"
          selectedId={right.id}
          otherId={left.id}
          verdicts={verdicts}
        />
      </section>

      <section className="mb-8 grid gap-4 md:grid-cols-2">
        <SummaryPanel title="Left" verdict={left} summary={leftSummary} />
        <SummaryPanel title="Right" verdict={right} summary={rightSummary} />
      </section>

      <section className="mb-8 rounded-md border border-zinc-800 bg-slate-surface p-4">
        <h2 className="mb-3 text-lg font-semibold">Failure delta</h2>
        <div className="grid gap-4 md:grid-cols-2">
          <FailureList title={left.shot_id} failures={leftSummary.failures} />
          <FailureList title={right.shot_id} failures={rightSummary.failures} />
        </div>
      </section>

      <section className="mb-8 rounded-md border border-zinc-800 bg-slate-surface p-4">
        <h2 className="mb-3 text-lg font-semibold">Quality score delta</h2>
        {qualityKeys.length === 0 ? (
          <p className="text-sm text-zinc-500">No quality scores were reported.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="text-zinc-500">
                <tr>
                  <th className="py-2 pr-4 font-medium">Metric</th>
                  <th className="py-2 pr-4 font-medium">Left</th>
                  <th className="py-2 pr-4 font-medium">Right</th>
                  <th className="py-2 font-medium">Delta</th>
                </tr>
              </thead>
              <tbody>
                {qualityKeys.map((key) => {
                  const leftValue = leftSummary.qualityScores[key];
                  const rightValue = rightSummary.qualityScores[key];
                  const delta =
                    typeof leftValue === "number" && typeof rightValue === "number"
                      ? rightValue - leftValue
                      : null;
                  return (
                    <tr key={key} className="border-t border-zinc-800">
                      <td className="py-2 pr-4 text-zinc-300">{key}</td>
                      <td className="py-2 pr-4 font-mono text-zinc-400">
                        {formatNumber(leftValue)}
                      </td>
                      <td className="py-2 pr-4 font-mono text-zinc-400">
                        {formatNumber(rightValue)}
                      </td>
                      <td className="py-2 font-mono text-zinc-300">
                        {delta === null ? "n/a" : formatSigned(delta)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="mb-8 rounded-md border border-zinc-800 bg-slate-surface p-4">
        <h2 className="mb-3 text-lg font-semibold">Response quality</h2>
        <div className="grid gap-4 md:grid-cols-2">
          <ResponseQualitySummary report={leftSummary.responseQuality} />
          <ResponseQualitySummary report={rightSummary.responseQuality} />
        </div>
      </section>

      <section className="rounded-md border border-zinc-800 bg-slate-surface p-4">
        <h2 className="mb-3 text-lg font-semibold">Panel coverage</h2>
        <div className="grid gap-4 md:grid-cols-2">
          <PanelSummary panel={leftSummary.panel} />
          <PanelSummary panel={rightSummary.panel} />
        </div>
      </section>
    </div>
  );
}

function VerdictPicker({
  label,
  side,
  selectedId,
  otherId,
  verdicts,
}: {
  label: string;
  side: "left" | "right";
  selectedId: string;
  otherId: string;
  verdicts: VerdictSummary[];
}) {
  return (
    <div className="rounded-md border border-zinc-800 bg-slate-surface p-4">
      <h2 className="mb-3 text-sm font-medium text-zinc-300">{label}</h2>
      <div className="space-y-2">
        {verdicts.map((verdict) => {
          const query =
            side === "left"
              ? { left: verdict.id, right: otherId }
              : { left: otherId, right: verdict.id };
          const isSelected = verdict.id === selectedId;
          return (
            <Link
              key={`${side}-${verdict.id}`}
              href={{ pathname: "/dashboard/compare", query }}
              className={
                isSelected
                  ? "block rounded border border-slate-accent bg-slate-accent/10 px-3 py-2 text-sm text-zinc-100"
                  : "block rounded border border-zinc-800 px-3 py-2 text-sm text-zinc-400 hover:border-zinc-700"
              }
            >
              <span className="font-mono">{verdict.shot_id}</span>
              <span className="ml-2 text-xs text-zinc-500">
                {verdict.final_status}
              </span>
            </Link>
          );
        })}
      </div>
    </div>
  );
}

function SummaryPanel({
  title,
  verdict,
  summary,
}: {
  title: string;
  verdict: VerdictDetail;
  summary: ReturnType<typeof summarizeVerdict>;
}) {
  return (
    <div className="rounded-md border border-zinc-800 bg-slate-surface p-4">
      <div className="mb-2 text-xs uppercase tracking-wide text-zinc-500">
        {title}
      </div>
      <div className="font-mono text-lg text-zinc-100">{verdict.shot_id}</div>
      <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
        <div>
          <dt className="text-zinc-500">Status</dt>
          <dd className="font-mono text-zinc-200">{verdict.final_status}</dd>
        </div>
        <div>
          <dt className="text-zinc-500">Failures</dt>
          <dd className="font-mono text-zinc-200">{summary.failures.length}</dd>
        </div>
        <div>
          <dt className="text-zinc-500">Panel</dt>
          <dd className="font-mono text-zinc-200">
            {summary.panel ? "present" : "none"}
          </dd>
        </div>
        <div>
          <dt className="text-zinc-500">Confidence</dt>
          <dd className="font-mono text-zinc-200">
            {formatConfidence(summary.responseQuality?.confidence_score)}
          </dd>
        </div>
      </dl>
    </div>
  );
}

function FailureList({ title, failures }: { title: string; failures: Failure[] }) {
  return (
    <div>
      <h3 className="mb-2 font-mono text-sm text-zinc-300">{title}</h3>
      {failures.length === 0 ? (
        <p className="text-sm text-emerald-400">No failures.</p>
      ) : (
        <ul className="space-y-2 text-sm">
          {failures.slice(0, 8).map((failure, index) => (
            <li key={`${failure.signal}-${index}`} className="text-zinc-400">
              <span className="font-mono text-red-400">
                {failure.signal ?? "unknown"}
              </span>{" "}
              - {failure.frame ?? "unknown frame"}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function ResponseQualitySummary({ report }: { report: ResponseQuality | null }) {
  if (!report) {
    return <p className="text-sm text-amber-300">No response-quality report.</p>;
  }

  return (
    <dl className="space-y-3 text-sm">
      <div>
        <dt className="text-zinc-500">Confidence</dt>
        <dd className="font-mono text-zinc-200">
          {formatConfidence(report.confidence_score)}
        </dd>
      </div>
      <div>
        <dt className="text-zinc-500">Recommendation</dt>
        <dd className="text-zinc-300">{report.recommendation ?? "Not provided."}</dd>
      </div>
      <div>
        <dt className="text-zinc-500">Unknowns</dt>
        <dd className="text-zinc-300">{report.unknowns?.length ?? 0}</dd>
      </div>
      <div>
        <dt className="text-zinc-500">Risks</dt>
        <dd className="text-zinc-300">{report.risks?.length ?? 0}</dd>
      </div>
    </dl>
  );
}

function PanelSummary({ panel }: { panel: PanelPayload | null }) {
  if (!panel) {
    return <p className="text-sm text-zinc-500">No Panel review in this run.</p>;
  }

  const personas = panel.per_persona ?? [];
  const blocked = personas.filter((persona) => persona.publish_ready === false);

  return (
    <dl className="space-y-3 text-sm">
      <div>
        <dt className="text-zinc-500">Publish ready</dt>
        <dd className="font-mono text-zinc-200">
          {panel.publish_ready ? "yes" : "no"}
        </dd>
      </div>
      <div>
        <dt className="text-zinc-500">Personas</dt>
        <dd className="text-zinc-300">
          {personas.length} total, {blocked.length} blocking
        </dd>
      </div>
      <div>
        <dt className="text-zinc-500">Critical / high flags</dt>
        <dd className="font-mono text-zinc-200">
          {panel.fused_critical_flags?.length ?? 0} /{" "}
          {panel.fused_high_flags?.length ?? 0}
        </dd>
      </div>
    </dl>
  );
}

function summarizeVerdict(verdict: VerdictDetail) {
  const payload = verdict.payload;
  const core = isRecord(payload.core) ? payload.core : payload;
  const panel = isRecord(payload.panel)
    ? (payload.panel as PanelPayload)
    : isRecord(payload.thrawn)
      ? (payload.thrawn as PanelPayload)
      : null;

  return {
    failures: asFailures(core.failures),
    qualityScores: asQualityScores(core.quality_scores_aggregated),
    responseQuality: selectResponseQuality(payload, core, panel),
    panel,
  };
}

function selectResponseQuality(
  payload: Record<string, unknown>,
  core: Record<string, unknown>,
  panel: PanelPayload | null,
): ResponseQuality | null {
  if (isResponseQuality(payload.response_quality)) return payload.response_quality;
  if (panel && isResponseQuality(panel.response_quality)) return panel.response_quality;
  if (isResponseQuality(core.response_quality)) return core.response_quality;
  return null;
}

function asFailures(value: unknown): Failure[] {
  if (!Array.isArray(value)) return [];
  return value.filter(isRecord).map((failure) => ({
    signal: typeof failure.signal === "string" ? failure.signal : undefined,
    frame: typeof failure.frame === "string" ? failure.frame : undefined,
    description:
      typeof failure.description === "string" ? failure.description : undefined,
  }));
}

function asQualityScores(value: unknown): Record<string, number> {
  if (!isRecord(value)) return {};
  return Object.fromEntries(
    Object.entries(value).filter((entry): entry is [string, number] => {
      const [, score] = entry;
      return typeof score === "number";
    }),
  );
}

function isResponseQuality(value: unknown): value is ResponseQuality {
  return isRecord(value);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function formatNumber(value: number | undefined): string {
  return typeof value === "number" ? value.toFixed(2) : "n/a";
}

function formatSigned(value: number): string {
  const formatted = value.toFixed(2);
  return value > 0 ? `+${formatted}` : formatted;
}

function formatConfidence(value: number | undefined): string {
  return typeof value === "number" ? `${Math.round(value * 100)}%` : "n/a";
}
