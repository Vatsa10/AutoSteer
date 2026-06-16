"use client";

import { useState, useEffect } from "react";
import { ArrowRight, Upload, Search, FileText, Check } from "lucide-react";

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
    description: "AutoSteer can read PDFs, Word docs, and images. Upload something and ask a question about it.",
    action: "Upload & ask",
    actionHint: "Click the paperclip icon in the chat to attach a file",
  },
  {
    icon: FileText,
    question: "Try a multi-agent task",
    description: "Ask AutoSteer to research something and create a document. It will use multiple agents to get it done.",
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

  useEffect(() => {
    const seen = localStorage.getItem("autosteer_onboarded");
    if (seen) setDone(true);
  }, []);

  if (done) return null;

  function finish() {
    localStorage.setItem("autosteer_onboarded", "true");
    const about = role.trim()
      ? `The user described their work as: ${role.trim()}`
      : "";
    if (about) {
      const existing = localStorage.getItem("autosteer_preferences");
      const prefs = existing ? JSON.parse(existing) : {};
      prefs.about = about;
      localStorage.setItem("autosteer_preferences", JSON.stringify(prefs));
    }
    setDone(true);
    onComplete({ role: role.trim(), about });
  }

  const s = STEPS[step];
  const Icon = s.icon;

  return (
    <div className="flex-1 flex items-center justify-center p-6">
      <div className="max-w-lg w-full text-center space-y-6">
        {/* Progress */}
        <div className="flex items-center justify-center gap-1.5">
          {STEPS.map((_, i) => (
            <div
              key={i}
              className={`h-1 rounded-full transition-all duration-300 ${
                i <= step ? "bg-blue-600 w-8" : "bg-slate-200 w-4"
              }`}
            />
          ))}
        </div>

        {/* Step content */}
        <div className="space-y-4">
          <div className="w-12 h-12 rounded-xl bg-blue-50 border border-blue-200 flex items-center justify-center mx-auto">
            <Icon className="w-6 h-6 text-blue-600" />
          </div>
          <h2 className="text-lg font-semibold text-slate-800">{s.question}</h2>

          {step === 0 && (
            <div className="space-y-3">
              <textarea
                value={role}
                onChange={(e) => setRole(e.target.value)}
                placeholder={s.placeholder}
                rows={2}
                className="w-full bg-white border border-slate-300 rounded-xl px-4 py-3 text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:border-blue-400 resize-none"
                autoFocus
              />
              <p className="text-xs text-slate-400">{s.hint}</p>
            </div>
          )}

          {step === 1 && (
            <div className="space-y-3">
              <p className="text-sm text-slate-600">{s.description}</p>
              <div className="inline-flex items-center gap-2 px-4 py-2.5 bg-blue-50 border border-blue-200 rounded-lg text-sm text-blue-700">
                <Upload className="w-4 h-4" />
                {s.actionHint}
              </div>
            </div>
          )}

          {step === 2 && (
            <div className="space-y-2">
              <p className="text-sm text-slate-600">{s.description}</p>
              <div className="grid gap-2">
                {s.suggestions?.map((sg, i) => (
                  <button
                    key={i}
                    onClick={() => {
                      const input = document.querySelector<HTMLInputElement>('input[type="text"]');
                      if (input) {
                        input.value = sg;
                        input.dispatchEvent(new Event("input", { bubbles: true }));
                      }
                      finish();
                    }}
                    className="text-left text-sm text-slate-600 hover:text-blue-700 bg-slate-50 hover:bg-blue-50 border border-slate-200 hover:border-blue-200 rounded-lg px-4 py-2.5 transition-all"
                  >
                    {sg}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="flex items-center justify-center gap-3">
          {step > 0 && (
            <button
              onClick={() => setStep(step - 1)}
              className="text-sm text-slate-500 hover:text-slate-700 px-4 py-2"
            >
              Back
            </button>
          )}
          {step < 2 ? (
            <button
              onClick={() => setStep(step + 1)}
              className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white rounded-xl px-5 py-2.5 text-sm font-medium transition-colors"
            >
              Next
              <ArrowRight className="w-4 h-4" />
            </button>
          ) : (
            <button
              onClick={finish}
              className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white rounded-xl px-5 py-2.5 text-sm font-medium transition-colors"
            >
              <Check className="w-4 h-4" />
              Get started
            </button>
          )}
        </div>

        <button onClick={() => setDone(true)} className="text-xs text-slate-400 hover:text-slate-600">
          Skip onboarding
        </button>
      </div>
    </div>
  );
}
