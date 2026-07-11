"use client";

import { useState, useEffect, useRef } from "react";
import { ArrowRight, Upload, Search, FileText, Check, Loader2 } from "lucide-react";
import { uploadFile } from "@/lib/api";
import { useToastStore } from "@/lib/store";

interface Props {
  onComplete: (preferences: { role: string; about: string }) => void;
}

const STEPS = [
  {
    icon: Search,
    question: "What kind of work do you do?",
    placeholder: "I'm a product manager at a SaaS startup...",
    hint: "This helps AutoSteer pick the right agents and tone for your work.",
  },
  {
    icon: Upload,
    question: "Try uploading a document",
    description: "AutoSteer can read PDFs, Word docs, and images. Upload a file now.",
  },
  {
    icon: FileText,
    question: "Try a multi-agent task",
    description: "AutoSteer uses multiple agents in parallel for complex tasks.",
    suggestions: [
      "Research quantum computing trends and create a report",
      "Analyze my competitor's website and draft a battle card",
      "Find the latest papers on transformer architectures and summarize them",
    ],
  },
];

export function Onboarding({ onComplete }: Props) {
  const [step, setStep] = useState(0);
  const [role, setRole] = useState("");
  const [done, setDone] = useState(false);
  const [uploadedFile, setUploadedFile] = useState<{ name: string; id: string } | null>(null);
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const addToast = useToastStore((s) => s.addToast);

  useEffect(() => {
    if (localStorage.getItem("autosteer_onboarded")) setDone(true);
  }, []);

  if (done) return null;

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const result = await uploadFile(file);
      setUploadedFile({ name: file.name, id: result.file_id });
      addToast("File uploaded. You can ask about it in chat.", "success");
    } catch {
      addToast("Upload failed. Try again in chat.", "error");
    }
    setUploading(false);
  }

  const [processing, setProcessing] = useState(false);

  async function finish() {
    if (processing) return;
    const text = role.trim();
    setProcessing(true);

    let about = text;
    if (text) {
      try {
        const res = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/auth/onboard`,
          { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ role_text: text }) }
        );
        const data = await res.json();
        if (data.ok && data.about) about = data.about;
      } catch {}
      // Fallback: store raw text if LLM call fails
      let prefs: Record<string, string> = {};
      try { const existing = localStorage.getItem("autosteer_preferences"); prefs = existing ? JSON.parse(existing) : {}; } catch { prefs = {}; }
      prefs.about = about;
      localStorage.setItem("autosteer_preferences", JSON.stringify(prefs));
    }

    localStorage.setItem("autosteer_onboarded", "true");
    setDone(true);
    setProcessing(false);
    onComplete({ role: text, about });
  }

  const s = STEPS[step];
  const Icon = s.icon;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
      <div className="bg-white rounded-2xl shadow-xl border border-slate-200 max-w-lg w-full p-8 relative">
        {/* Progress */}
        <div className="flex items-center justify-center gap-1.5 mb-8">
          {STEPS.map((_, i) => (
            <div
              key={i}
              className={`h-1 rounded-full transition-all duration-300 ${
                i <= step ? "bg-blue-600 w-8" : "bg-slate-200 w-4"
              }`}
            />
          ))}
        </div>

        <div className="text-center space-y-5">
          <div className="w-14 h-14 rounded-2xl bg-blue-50 border border-blue-200 flex items-center justify-center mx-auto">
            <Icon className="w-7 h-7 text-blue-600" />
          </div>
          <h2 className="text-xl font-semibold text-slate-800">{s.question}</h2>

          {/* Step 0: Role */}
          {step === 0 && (
            <div className="space-y-3">
              <textarea
                value={role}
                onChange={(e) => setRole(e.target.value)}
                placeholder={s.placeholder}
                rows={3}
                className="w-full bg-white border border-slate-300 rounded-xl px-4 py-3 text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-200 resize-none"
                autoFocus
              />
              <p className="text-xs text-slate-400">{s.hint}</p>
            </div>
          )}

          {/* Step 1: Upload */}
          {step === 1 && (
            <div className="space-y-4">
              <p className="text-sm text-slate-600">{s.description}</p>
              <input
                ref={fileRef}
                type="file"
                onChange={handleUpload}
                className="hidden"
                accept=".pdf,.docx,.txt,.md,.csv,.json,.png,.jpg,.jpeg"
              />
              {uploadedFile ? (
                <div className="flex items-center gap-3 p-4 bg-green-50 border border-green-200 rounded-xl">
                  <div className="w-10 h-10 rounded-lg bg-green-100 flex items-center justify-center">
                    <Check className="w-5 h-5 text-green-600" />
                  </div>
                  <div className="text-left">
                    <p className="text-sm font-medium text-green-800">{uploadedFile.name}</p>
                    <p className="text-xs text-green-600">Uploaded successfully</p>
                  </div>
                </div>
              ) : (
                <button
                  onClick={() => fileRef.current?.click()}
                  disabled={uploading}
                  className="w-full flex items-center justify-center gap-2 p-6 border-2 border-dashed border-slate-300 hover:border-blue-400 rounded-xl text-sm text-slate-500 hover:text-blue-600 transition-colors disabled:opacity-50"
                >
                  {uploading ? (
                    <Loader2 className="w-5 h-5 animate-spin" />
                  ) : (
                    <Upload className="w-5 h-5" />
                  )}
                  {uploading ? "Uploading..." : "Click to upload a file"}
                </button>
              )}
              <p className="text-xs text-slate-400">Supports PDF, Word, images, text files</p>
              <button onClick={() => setStep(2)} className="text-xs text-slate-400 hover:text-slate-600 mt-2">Skip upload</button>
            </div>
          )}

          {/* Step 2: Suggestions */}
          {step === 2 && (
            <div className="space-y-2">
              <p className="text-sm text-slate-600 mb-3">{s.description}</p>
              {s.suggestions?.map((sg, i) => (
                <button
                  key={i}
                  onClick={() => {
                    sessionStorage.setItem("autosteer_template_prompt", sg);
                    finish();
                  }}
                  className="w-full text-left text-sm text-slate-600 hover:text-blue-700 bg-slate-50 hover:bg-blue-50 border border-slate-200 hover:border-blue-200 rounded-lg px-4 py-3 transition-all"
                >
                  {sg}
                </button>
              ))}
              <button onClick={finish} className="text-xs text-slate-400 hover:text-slate-600 mt-2 block w-full text-center">Skip for now</button>
            </div>
          )}
        </div>

        {/* Nav */}
        <div className="flex items-center justify-center gap-3 mt-8">
          {step > 0 && (
            <button onClick={() => setStep(step - 1)} className="text-sm text-slate-500 hover:text-slate-700 px-4 py-2">
              Back
            </button>
          )}
          {step < 2 ? (
            <button
              onClick={() => setStep(step + 1)}
              className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white rounded-xl px-6 py-2.5 text-sm font-medium transition-colors"
            >
              Next
              <ArrowRight className="w-4 h-4" />
            </button>
          ) : (
            <button
              onClick={finish}
              disabled={processing}
              className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white rounded-xl px-6 py-2.5 text-sm font-medium transition-colors disabled:opacity-50"
            >
              {processing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
              {processing ? "Processing..." : "Get started"}
            </button>
          )}
        </div>

      </div>
    </div>
  );
}
