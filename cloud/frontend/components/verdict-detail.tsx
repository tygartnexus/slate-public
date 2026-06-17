"use client";

import { useMemo, useState } from "react";

import {
  formatConfidence,
  modeTitle,
  REVIEW_MODES,
  type ResponseQuality,
  type ReviewMode,
} from "@/lib/ai-response-quality";

interface PersonaFlag {
  category: string;
  severity: string;
  frame: string | null;
  description: string;
}

interface PersonaVerdict {
  name: string;
  publish_ready: boolean;
  summary: string;
  flags: PersonaFlag[];
  response_quality?: ResponseQuality | null;
}

interface PanelVerdict {
  publish_ready: boolean;
  per_persona: PersonaVerdict[];
  summary: string;
  response_quality?: ResponseQuality | null;
}

interface CoreVerdict {
  status: string;
  failures: { signal: string; frame: string; description: string }[];
  quality_scores_aggregated: Record<string, number>;
  response_quality?: ResponseQuality | null;
  frame_analyses?: { response_quality?: ResponseQuality | null }[];
}

interface VerdictPayload {
  status?: string;
  core?: CoreVerdict;
  panel?: PanelVerdict;
  thrawn?: PanelVerdict;
  response_quality?: ResponseQuality | null;
  failures?: { signal: string; frame: string; description: string }[];
  quality_scores_aggregated?: Record<string, number>;
  frame_analyses?: { response_quality?: ResponseQuality | null }[];
  [k: string]: unknown;
}

interface VerdictDetailData {
  id: string;
  shot_id: string;
  final_status: string;
  has_panel_review: boolean;
  submitted_at: string;
  payload: VerdictPayload;
}

export function VerdictDetail({ verdict }: { verdict: VerdictDetailData }) {
  const [mode, setMode] = useState<ReviewMode>("accuracy");
  const payload = verdict.payload;
  const core = payload.core ?? (payload.status ? (payload as CoreVerdict) : null);
  const panel = payload.panel ?? payload.thrawn ?? null;
  const responseQuality = useMemo(
    () => selectResponseQuality(payload, core, panel),
    [payload, core, panel],
  );

  return (
    <div>
      <header className="mb-8">
        <div className="font-mono text-2xl text-zinc-100">{verdict.shot_id}</div>
        <div className="text-sm text-zinc-500 mt-1">
          {new Date(verdict.submitted_at).toLocaleString()}
        </div>
        <div className="mt-3 inline-block px-3 py-1 rounded-md border border-zinc-700 text-sm font-medium">
          {verdict.final_status}
        </div>
      </header>

      <section className="mb-8">
        <div className="flex flex-wrap gap-2">
          {REVIEW_MODES.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => setMode(item.id)}
              className={
                mode === item.id
                  ? "rounded-md bg-slate-accent px-3 py-2 text-sm font-medium text-slate-bg"
                  : "rounded-md border border-zinc-800 px-3 py-2 text-sm text-zinc-300 hover:border-zinc-600"
              }
            >
              {item.label}
            </button>
          ))}
        </div>
      </section>

      <QualityPanel mode={mode} report={responseQuality} />

      {core && (
        <section className="mb-8">
          <h2 className="text-lg font-semibold mb-3">Core</h2>
          <div className="grid md:grid-cols-2 gap-6">
            <div className="rounded-md border border-zinc-800 bg-slate-surface p-4">
              <div className="text-sm text-zinc-400 mb-2">Quality scores</div>
              <dl className="space-y-1 text-sm">
                {Object.entries(core.quality_scores_aggregated ?? {}).map(([k, v]) => (
                  <div key={k} className="flex justify-between gap-4">
                    <dt className="text-zinc-500">{k.replace("_quality", "")}</dt>
                    <dd className="font-mono">{v.toFixed(2)}</dd>
                  </div>
                ))}
              </dl>
            </div>
            <div className="rounded-md border border-zinc-800 bg-slate-surface p-4">
              <div className="text-sm text-zinc-400 mb-2">
                Failures ({core.failures?.length ?? 0})
              </div>
              {(core.failures ?? []).length === 0 ? (
                <div className="text-sm text-emerald-400">No failures.</div>
              ) : (
                <ul className="space-y-2 text-sm">
                  {core.failures.slice(0, 5).map((f, i) => (
                    <li key={i} className="text-zinc-300">
                      <span className="text-red-400 font-mono">{f.signal}</span>{" "}
                      - {f.frame}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </section>
      )}

      {panel && (
        <section>
          <h2 className="text-lg font-semibold mb-3">Panel personas</h2>
          <div className="grid md:grid-cols-2 gap-4">
            {panel.per_persona.map((p) => (
              <div
                key={p.name}
                className="rounded-md border border-zinc-800 bg-slate-surface p-4"
              >
                <div className="flex justify-between items-center gap-4 mb-2">
                  <div className="font-medium capitalize">
                    {p.name.replace("_", " ")}
                  </div>
                  <div
                    className={
                      p.publish_ready
                        ? "text-emerald-400 text-xs"
                        : "text-red-400 text-xs"
                    }
                  >
                    {p.publish_ready ? "PASS" : "BLOCK"}
                  </div>
                </div>
                <div className="text-sm text-zinc-400 mb-3">{p.summary}</div>
                {p.flags.length > 0 && (
                  <ul className="space-y-1 text-xs">
                    {p.flags.slice(0, 3).map((f, i) => (
                      <li key={i} className="text-zinc-300">
                        <span className="text-amber-400 font-mono">
                          [{f.severity}]
                        </span>{" "}
                        {f.description}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

function selectResponseQuality(
  payload: VerdictPayload,
  core: CoreVerdict | null,
  panel: PanelVerdict | null,
): ResponseQuality | null {
  return (
    payload.response_quality ??
    panel?.response_quality ??
    core?.response_quality ??
    core?.frame_analyses?.find((item) => item.response_quality)?.response_quality ??
    null
  );
}

function QualityPanel({
  mode,
  report,
}: {
  mode: ReviewMode;
  report: ResponseQuality | null;
}) {
  if (!report) {
    return (
      <section className="mb-8 rounded-md border border-amber-500/40 bg-amber-500/5 p-4">
        <h2 className="text-lg font-semibold mb-2">Evidence status</h2>
        <p className="text-sm text-amber-200">
          No response-quality contract was included in this verdict.
        </p>
      </section>
    );
  }

  return (
    <section className="mb-8 rounded-md border border-zinc-800 bg-slate-surface p-4">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <h2 className="text-lg font-semibold">{modeTitle(mode)}</h2>
        <div className="font-mono text-sm text-slate-accent">
          confidence {formatConfidence(report.confidence_score)}
        </div>
      </div>
      {mode === "standard" && (
        <div className="grid md:grid-cols-2 gap-4">
          <TextBlock title="Recommendation" value={report.recommendation} />
          <SectionList title="Facts" items={report.facts} />
          <SectionList title="Assumptions" items={report.assumptions} />
          <SectionList title="Unknowns" items={report.unknowns} />
        </div>
      )}
      {mode === "accuracy" && (
        <div className="grid md:grid-cols-2 gap-4">
          <SectionList title="Facts" items={report.facts} />
          <SectionList title="Assumptions" items={report.assumptions} />
          <SectionList title="Unknowns" items={report.unknowns} />
          <SectionList title="Evidence" items={report.evidence} />
          <TextBlock title="Recommendation" value={report.recommendation} />
          <SectionList
            title="Would change"
            items={report.what_would_change_recommendation}
          />
        </div>
      )}
      {mode === "red_team" && (
        <div className="grid md:grid-cols-2 gap-4">
          <SectionList title="Risks" items={report.risks} />
          <SectionList title="Counterarguments" items={report.counterarguments} />
          <SectionList title="Unknowns" items={report.unknowns} />
          <SectionList
            title="Would change"
            items={report.what_would_change_recommendation}
          />
        </div>
      )}
      {mode === "ceo" && (
        <div className="grid md:grid-cols-2 gap-4">
          <TextBlock title="Recommendation" value={report.recommendation} />
          <SectionList title="Tradeoffs" items={report.tradeoffs} />
          <SectionList title="Facts" items={report.facts} />
          <SectionList title="Risks" items={report.risks} />
        </div>
      )}
      {mode === "technical" && (
        <div className="grid md:grid-cols-2 gap-4">
          <SectionList title="Facts" items={report.facts} />
          <SectionList title="Evidence" items={report.evidence} />
          <SectionList title="Unknowns" items={report.unknowns} />
          <SectionList title="Risks" items={report.risks} />
        </div>
      )}
      {mode === "legal" && (
        <div className="grid md:grid-cols-2 gap-4">
          <TextBlock title="Caveat" value="Not legal advice." />
          <SectionList title="Risks" items={report.risks} />
          <SectionList title="Unknowns" items={report.unknowns} />
          <SectionList title="Evidence" items={report.evidence} />
        </div>
      )}
    </section>
  );
}

function SectionList({ title, items }: { title: string; items?: string[] }) {
  const values = items?.filter(Boolean) ?? [];
  return (
    <div>
      <h3 className="text-sm font-medium text-zinc-300 mb-2">{title}</h3>
      {values.length === 0 ? (
        <p className="text-sm text-zinc-500">Not provided.</p>
      ) : (
        <ul className="space-y-1 text-sm text-zinc-400">
          {values.map((item, index) => (
            <li key={`${title}-${index}`}>{item}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

function TextBlock({ title, value }: { title: string; value?: string }) {
  return (
    <div>
      <h3 className="text-sm font-medium text-zinc-300 mb-2">{title}</h3>
      <p className="text-sm text-zinc-400">{value || "Not provided."}</p>
    </div>
  );
}
