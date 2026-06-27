"use client";

import { useState, useEffect, useCallback } from "react";
import { Search, Plus, Trash2, Check, X, FileText, Upload, Brain, Clock, Loader2, Download, UploadCloud, Activity } from "lucide-react";
import { useToastStore } from "@/lib/store";

interface MemoryFact {
  id: string;
  fact_type: string;
  key: string;
  value: string;
}

interface MemoryDocument {
  filename: string;
  preview: string;
  char_count: number;
}

export default function MemoryPage() {
  const addToast = useToastStore((s) => s.addToast);
  const [facts, setFacts] = useState<MemoryFact[]>([]);
  const [documents, setDocuments] = useState<MemoryDocument[]>([]);
  const [summary, setSummary] = useState("");
  const [search, setSearch] = useState("");
  const [editingFact, setEditingFact] = useState<string | null>(null);
  const [editValue, setEditValue] = useState("");
  const [newFactKey, setNewFactKey] = useState("");
  const [newFactValue, setNewFactValue] = useState("");
  const [addingFact, setAddingFact] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Load from localStorage for now (backend API later)
    const stored = localStorage.getItem("AutoSteer_memory");
    if (stored) {
      try {
        const m = JSON.parse(stored);
        setFacts(m.facts || []);
        setDocuments(m.documents || []);
        setSummary(m.summary || "");
      } catch {}
    }
    setLoading(false);
  }, []);

  const persist = useCallback((f: MemoryFact[], d: MemoryDocument[], s: string) => {
    localStorage.setItem("AutoSteer_memory", JSON.stringify({ facts: f, documents: d, summary: s }));
    setFacts(f);
    setDocuments(d);
    setSummary(s);
  }, []);

  function addFact() {
    if (!newFactKey.trim() || !newFactValue.trim()) return;
    const fact: MemoryFact = {
      id: Math.random().toString(36).slice(2, 10),
      fact_type: "preference",
      key: newFactKey.trim(),
      value: newFactValue.trim(),
    };
    const updated = [...facts, fact];
    persist(updated, documents, summary);
    setNewFactKey("");
    setNewFactValue("");
    setAddingFact(false);
    addToast("Fact added", "success");
  }

  function updateFact(id: string) {
    const updated = facts.map((f) => (f.id === id ? { ...f, value: editValue } : f));
    persist(updated, documents, summary);
    setEditingFact(null);
    addToast("Fact updated", "success");
  }

  function deleteFact(id: string) {
    const updated = facts.filter((f) => f.id !== id);
    persist(updated, documents, summary);
    addToast("Fact removed", "info");
  }

  async function handleDocUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    const reader = new FileReader();
    reader.onload = () => {
      const text = (reader.result as string).slice(0, 500);
      const doc: MemoryDocument = {
        filename: file.name, preview: text, char_count: file.size,
      };
      persist(facts, [...documents, doc], summary);
      setUploading(false);
      addToast("Document added to context", "success");
    };
    reader.readAsText(file);
    if (e.target) e.target.value = "";
  }

  function removeDocument(index: number) {
    const updated = documents.filter((_, i) => i !== index);
    persist(facts, updated, summary);
    addToast("Document removed", "info");
  }

  const filtered = search.trim()
    ? facts.filter((f) => f.key.toLowerCase().includes(search.toLowerCase()) || f.value.toLowerCase().includes(search.toLowerCase()))
    : facts;

  if (loading) {
    return <div className="flex items-center justify-center h-full"><Loader2 className="w-5 h-5 text-blue-600 animate-spin" /></div>;
  }

  return (
    <div className="max-w-2xl px-8 py-8 space-y-10">
      <div>
        <h2 className="text-base font-semibold text-slate-800 mb-1">Memory & Context</h2>
        <p className="text-sm text-slate-500">What AutoSteer remembers about you and your conversations.</p>
      </div>

      {/* Memory Health */}
      <section className="grid grid-cols-3 gap-3">
        {[
          { label: "Facts stored", value: facts.length, icon: Brain, color: "blue" },
          { label: "Documents", value: documents.length, icon: FileText, color: "amber" },
          { label: "Health score", value: facts.length > 5 ? "Good" : facts.length > 0 ? "Building" : "New", icon: Activity, color: facts.length > 5 ? "green" : facts.length > 0 ? "amber" : "slate" },
        ].map((stat) => {
          const Icon = stat.icon;
          const colors: Record<string, string> = { blue: "bg-blue-50 border-blue-200 text-blue-700", amber: "bg-amber-50 border-amber-200 text-amber-700", green: "bg-green-50 border-green-200 text-green-700", slate: "bg-slate-50 border-slate-200 text-slate-500" };
          return (
            <div key={stat.label} className={`p-4 rounded-xl border ${colors[stat.color]}`}>
              <div className="flex items-center gap-2 mb-1">
                <Icon className="w-3.5 h-3.5" />
                <span className="text-[11px] font-medium uppercase tracking-wider opacity-70">{stat.label}</span>
              </div>
              <div className="text-xl font-bold">{stat.value}</div>
            </div>
          );
        })}
      </section>

      {/* Export / Import */}
      <section className="flex items-center gap-3">
        <button
          onClick={() => {
            const data = JSON.stringify({ facts, documents, summary, exported_at: new Date().toISOString() }, null, 2);
            const blob = new Blob([data], { type: "application/json" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a"); a.href = url; a.download = "AutoSteer-memory.json"; a.click();
            URL.revokeObjectURL(url);
            addToast("Memory exported", "success");
          }}
          className="flex items-center gap-2 text-xs font-medium px-4 py-2 rounded-lg border border-slate-200 text-slate-600 hover:border-blue-300 hover:text-blue-700 hover:bg-blue-50 transition-colors"
        >
          <Download className="w-3.5 h-3.5" /> Export memory
        </button>
        <label className="flex items-center gap-2 text-xs font-medium px-4 py-2 rounded-lg border border-slate-200 text-slate-600 hover:border-blue-300 hover:text-blue-700 hover:bg-blue-50 transition-colors cursor-pointer">
          <UploadCloud className="w-3.5 h-3.5" /> Import memory
          <input
            type="file" accept=".json" className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0]; if (!file) return;
              const reader = new FileReader();
              reader.onload = () => {
                try {
                  const imported = JSON.parse(reader.result as string);
                  if (imported.facts && imported.documents) {
                    localStorage.setItem("AutoSteer_memory", JSON.stringify({ facts: imported.facts, documents: imported.documents, summary: imported.summary || "" }));
                    setFacts(imported.facts);
                    setDocuments(imported.documents);
                    setSummary(imported.summary || "");
                    addToast("Memory imported successfully", "success");
                  }
                } catch { addToast("Invalid memory file", "error"); }
              };
              reader.readAsText(file);
              if (e.target) e.target.value = "";
            }}
          />
        </label>
      </section>

      {/* Conversation Summary */}
      <section className="p-5 rounded-xl bg-amber-50/60 border border-amber-200/60">
        <div className="flex items-center gap-2 mb-3">
          <Clock className="w-4 h-4 text-amber-600" />
          <h3 className="text-sm font-semibold text-slate-800">Conversation Summary</h3>
        </div>
        {summary ? (
          <p className="text-sm text-slate-600 leading-relaxed">{summary}</p>
        ) : (
          <p className="text-sm text-slate-400 italic">No conversations yet. Start chatting to build your memory.</p>
        )}
      </section>

      {/* Facts */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold text-slate-800">Facts</h3>
            <p className="text-xs text-slate-400 mt-0.5">Extracted preferences, decisions, and knowledge.</p>
          </div>
          <button onClick={() => setAddingFact(true)} className="flex items-center gap-1.5 text-xs font-medium text-blue-600 hover:text-blue-700 transition-colors">
            <Plus className="w-3.5 h-3.5" /> Add fact
          </button>
        </div>

        {facts.length > 5 && (
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400" />
            <input
              type="text" value={search} onChange={(e) => setSearch(e.target.value)}
              placeholder="Search facts…"
              className="w-full bg-white border border-slate-200 rounded-lg pl-9 pr-3 py-2 text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:border-blue-400"
            />
          </div>
        )}

        {addingFact && (
          <div className="p-3 rounded-lg border border-blue-200 bg-blue-50/50 space-y-2">
            <input type="text" value={newFactKey} onChange={(e) => setNewFactKey(e.target.value)} placeholder="Key (e.g. 'Uses TypeScript')" className="w-full bg-white border border-slate-200 rounded-md px-3 py-1.5 text-sm focus:outline-none focus:border-blue-400" autoFocus />
            <input type="text" value={newFactValue} onChange={(e) => setNewFactValue(e.target.value)} placeholder="Value (e.g. 'Prefers strict mode')" className="w-full bg-white border border-slate-200 rounded-md px-3 py-1.5 text-sm focus:outline-none focus:border-blue-400" />
            <div className="flex gap-2 justify-end">
              <button onClick={() => setAddingFact(false)} className="text-xs text-slate-500 hover:text-slate-700 px-2 py-1">Cancel</button>
              <button onClick={addFact} className="text-xs bg-blue-600 text-white rounded-md px-3 py-1 hover:bg-blue-500">Add</button>
            </div>
          </div>
        )}

        <div className="space-y-1.5">
          {filtered.length === 0 && !addingFact && (
            <p className="text-sm text-slate-400 py-4 text-center">
              {search ? "No facts match your search." : "No facts yet. Facts are extracted from your conversations automatically."}
            </p>
          )}
          {filtered.map((fact) => (
            <div key={fact.id} className="group flex items-start gap-3 px-3 py-2.5 rounded-lg border border-transparent hover:border-slate-200 hover:bg-slate-50 transition-colors">
              <span className="text-[10px] font-medium uppercase text-slate-400 bg-slate-100 rounded px-1.5 py-0.5 mt-0.5 shrink-0">{fact.fact_type}</span>
              <div className="flex-1 min-w-0">
                {editingFact === fact.id ? (
                  <div className="flex gap-2">
                    <input type="text" value={editValue} onChange={(e) => setEditValue(e.target.value)} className="flex-1 bg-white border border-blue-300 rounded-md px-2 py-1 text-sm focus:outline-none focus:border-blue-500" autoFocus />
                    <button onClick={() => updateFact(fact.id)} className="p-1 text-green-600 hover:bg-green-50 rounded"><Check className="w-3.5 h-3.5" /></button>
                    <button onClick={() => setEditingFact(null)} className="p-1 text-slate-400 hover:bg-slate-100 rounded"><X className="w-3.5 h-3.5" /></button>
                  </div>
                ) : (
                  <div className="flex items-start gap-2">
                    <div className="flex-1 min-w-0">
                      <span className="text-sm font-medium text-slate-700">{fact.key}</span>
                      <span className="text-sm text-slate-500 ml-1.5">{fact.value}</span>
                    </div>
                    <div className="flex gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
                      <button onClick={() => { setEditingFact(fact.id); setEditValue(fact.value); }} className="p-1 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors"><Brain className="w-3 h-3" /></button>
                      <button onClick={() => deleteFact(fact.id)} className="p-1 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors"><Trash2 className="w-3 h-3" /></button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Documents */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold text-slate-800">Documents in Context</h3>
            <p className="text-xs text-slate-400 mt-0.5">Uploaded files persist in your conversation context.</p>
          </div>
          <label className="flex items-center gap-1.5 text-xs font-medium text-blue-600 hover:text-blue-700 cursor-pointer transition-colors">
            <Upload className="w-3.5 h-3.5" />
            {uploading ? "Uploading…" : "Upload document"}
            <input type="file" onChange={handleDocUpload} className="hidden" accept=".pdf,.docx,.txt,.md,.csv,.json,.png,.jpg" />
          </label>
        </div>

        {documents.length === 0 && (
          <div className="flex flex-col items-center gap-2 py-8 text-center border-2 border-dashed border-slate-200 rounded-xl">
            <FileText className="w-6 h-6 text-slate-300" />
            <p className="text-sm text-slate-400">No documents uploaded.</p>
            <p className="text-xs text-slate-400">Upload PDFs, Word docs, or text files to add context.</p>
          </div>
        )}

        <div className="space-y-2">
          {documents.map((doc, i) => (
            <div key={i} className="flex items-start gap-3 px-3 py-2.5 rounded-lg border border-slate-200 hover:bg-slate-50 transition-colors group">
              <FileText className="w-4 h-4 text-blue-500 mt-0.5 shrink-0" />
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-slate-700 truncate">{doc.filename}</div>
                <div className="text-xs text-slate-400">{(doc.char_count / 1024).toFixed(1)} KB · {doc.preview.slice(0, 80)}…</div>
              </div>
              <button onClick={() => removeDocument(i)} className="p-1 text-slate-300 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-all shrink-0"><Trash2 className="w-3.5 h-3.5" /></button>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
