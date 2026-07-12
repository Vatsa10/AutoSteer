"use client";

import { useState } from "react";
import type { ToolTrace, SourceTrace, StepTrace } from "@/lib/store";

const statusColor = (s: string) =>
  s === "error" || s === "blocked" ? "text-red-600 border-red-200" : "text-slate-700 border-slate-200";

export function ChatTrace({
  tools = [],
  sources = [],
  steps = [],
}: {
  tools?: ToolTrace[];
  sources?: SourceTrace[];
  steps?: StepTrace[];
}) {
  const [open, setOpen] = useState(false);
  const [snippet, setSnippet] = useState<string | null>(null);
  const count = tools.length + sources.length + steps.length;
  if (count === 0) return null;

  return (
    <div className="mt-2 border border-slate-200 rounded-lg bg-white">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-3 py-1.5 text-[10px] uppercase tracking-wide text-slate-500 hover:bg-slate-50 rounded-lg"
      >
        <span>
          Trace &middot; {tools.length} tools &middot; {sources.length} sources &middot; {steps.length} steps
        </span>
        <span>{open ? "–" : "+"}</span>
      </button>
      {open && (
        <div className="border-t border-slate-200 p-3 space-y-3">
          {steps.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {steps.map((s) => (
                <span
                  key={s.id}
                  className={`text-[10px] border rounded-full px-1.5 py-0.5 ${statusColor(s.status)}`}
                >
                  {s.id} &middot; {s.status}
                </span>
              ))}
            </div>
          )}
          {tools.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {tools.map((t, i) => (
                <span
                  key={i}
                  className={`text-[10px] border rounded-full px-1.5 py-0.5 ${statusColor(t.status)}`}
                >
                  {t.name} {t.status === "ok" ? "✓" : "✕"} {t.duration_ms}ms
                </span>
              ))}
            </div>
          )}
          {sources.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {sources.map((s, i) => (
                <button
                  key={i}
                  onClick={() => setSnippet(s.snippet)}
                  className="text-[10px] border border-slate-200 rounded-full px-1.5 py-0.5 hover:bg-slate-900 hover:text-white transition-colors"
                >
                  {s.filename} &middot; chunk {s.chunk_index} &middot; {s.score.toFixed(2)}
                </button>
              ))}
            </div>
          )}
          {snippet && (
            <div className="border border-slate-200 rounded-lg p-2 text-[10px] leading-relaxed whitespace-pre-wrap text-slate-600">
              {snippet}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
