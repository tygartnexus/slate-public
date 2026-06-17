export default function ComparePage() {
  return (
    <div>
      <h1 className="text-2xl font-semibold mb-4">Compare verdicts</h1>
      <div className="rounded-lg border border-zinc-800 bg-slate-surface p-10 text-zinc-400 text-center">
        <p>Side-by-side verdict diff coming in v0.2.</p>
        <p className="text-sm mt-2">
          Will compare quality scores, failures, and persona votes across two
          runs of the same shot to surface drift.
        </p>
      </div>
    </div>
  );
}
