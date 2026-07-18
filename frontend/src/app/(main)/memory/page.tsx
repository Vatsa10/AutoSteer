"use client";

import { useMemo, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Brain, Sparkles, Loader2, Link2, Search } from "lucide-react";
import { getMemory, getMemoryInsights, runMemoryDream } from "@/lib/api";
import { useToastStore } from "@/lib/store";

const IMPORTANCE_COLOR: Record<number, string> = {
  5: "bg-red-50 text-red-700 border-red-200",
  4: "bg-orange-50 text-orange-700 border-orange-200",
  3: "bg-blue-50 text-blue-700 border-blue-200",
  2: "bg-slate-50 text-slate-600 border-slate-200",
  1: "bg-slate-50 text-slate-400 border-slate-200",
};

export default function MemoryBrainPage() {
  const addToast = useToastStore((s) => s.addToast);
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");

  const insightsQuery = useQuery({ queryKey: ["memory-insights"], queryFn: getMemoryInsights });
  const memoryQuery = useQuery({ queryKey: ["memory"], queryFn: getMemory });

  const dream = useMutation({
    mutationFn: runMemoryDream,
    onSuccess: (r) => {
      addToast(
        r.insights_created > 0
          ? `Dreamed up ${r.insights_created} new insight(s) from ${r.consolidated} facts.`
          : r.reason || "Nothing new to consolidate.",
        r.insights_created > 0 ? "success" : "info",
      );
      queryClient.invalidateQueries({ queryKey: ["memory-insights"] });
    },
    onError: (e: Error) => addToast(e.message, "error"),
  });

  const facts = memoryQuery.data?.facts ?? [];
  const insightsData = insightsQuery.data?.insights;

  const filteredInsights = useMemo(() => {
    const insights = insightsData ?? [];
    const q = search.trim().toLowerCase();
    if (!q) return insights;
    return insights.filter(
      (i) =>
        i.title.toLowerCase().includes(q) ||
        i.body.toLowerCase().includes(q) ||
        i.topics.some((t) => t.toLowerCase().includes(q)),
    );
  }, [insightsData, search]);

  return (
    <div className="h-full overflow-y-auto">
      <div className="max-w-4xl mx-auto px-6 py-8 space-y-8">
        {/* Header */}
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-11 h-11 rounded-2xl bg-blue-50 border border-blue-200 flex items-center justify-center">
              <Brain className="w-6 h-6 text-blue-600" />
            </div>
            <div>
              <h1 className="text-xl font-semibold text-slate-900">Memory</h1>
              <p className="text-sm text-slate-500">
                A living knowledge catalog. Facts are distilled into connected insights while you&apos;re away.
              </p>
            </div>
          </div>
          <button
            onClick={() => dream.mutate()}
            disabled={dream.isPending}
            className="shrink-0 inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-sm font-medium rounded-xl px-4 py-2.5 transition-colors"
          >
            {dream.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
            {dream.isPending ? "Dreaming…" : "Dream now"}
          </button>
        </div>

        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search insights & topics…"
            className="w-full bg-white border border-slate-300 rounded-xl pl-9 pr-4 py-2.5 text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-300"
          />
        </div>

        {/* Insights (knowledge catalog) */}
        <section className="space-y-3">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Insights ({filteredInsights.length})
          </h2>
          {insightsQuery.isLoading ? (
            <div className="flex justify-center py-10"><Loader2 className="w-5 h-5 text-blue-600 animate-spin" /></div>
          ) : filteredInsights.length === 0 ? (
            <div className="text-center py-12 border border-dashed border-slate-200 rounded-2xl">
              <Brain className="w-8 h-8 text-slate-300 mx-auto mb-3" />
              <p className="text-sm text-slate-500">No insights yet.</p>
              <p className="text-xs text-slate-400 mt-1">Chat a bit, then hit &quot;Dream now&quot; to consolidate what was learned.</p>
            </div>
          ) : (
            filteredInsights.map((i) => (
              <div key={i.id} className="bg-white border border-slate-200 rounded-2xl px-5 py-4 hover:border-blue-300 transition-colors">
                <div className="flex items-start justify-between gap-3">
                  <h3 className="text-sm font-semibold text-slate-900">{i.title}</h3>
                  <span className={`shrink-0 text-[10px] px-2 py-0.5 rounded-full border ${IMPORTANCE_COLOR[i.importance] ?? IMPORTANCE_COLOR[3]}`}>
                    P{i.importance}
                  </span>
                </div>
                <p className="text-sm text-slate-600 mt-1.5 leading-relaxed">{i.body}</p>
                {(i.topics.length > 0 || i.connections.length > 0) && (
                  <div className="flex flex-wrap items-center gap-1.5 mt-3">
                    {i.topics.map((t) => (
                      <span key={t} className="text-[10px] px-1.5 py-0.5 rounded-md bg-slate-100 text-slate-600 border border-slate-200">{t}</span>
                    ))}
                    {i.connections.map((c) => (
                      <span key={c} className="inline-flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded-md bg-blue-50 text-blue-600 border border-blue-200">
                        <Link2 className="w-2.5 h-2.5" />{c}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))
          )}
        </section>

        {/* Raw facts */}
        <section className="space-y-3">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Raw facts ({facts.length})
          </h2>
          {facts.length === 0 ? (
            <p className="text-sm text-slate-400">No facts captured yet.</p>
          ) : (
            <div className="grid gap-1.5">
              {facts.map((f) => (
                <div key={f.id} className="flex items-baseline gap-2 text-sm bg-white border border-slate-200 rounded-lg px-3 py-2">
                  <span className="text-[10px] uppercase tracking-wider text-slate-400 shrink-0">{f.fact_type}</span>
                  <span className="font-medium text-slate-700">{f.key}</span>
                  <span className="text-slate-500 truncate">{f.value}</span>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
