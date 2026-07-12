"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { FileText, Shield, PenLine, Search, BarChart3, Code, Briefcase, ArrowRight, Zap, Play } from "lucide-react";
import { useChatStore } from "@/lib/store";
import { getWorkflows, type WorkflowDefinition } from "@/lib/api";

const FLAGSHIP: { name: string; title: string; outcome: string; chips: string[] }[] = [
  { name: "research_report", title: "Research → Report", outcome: "Research a topic, draft it, review, ship a Word doc.", chips: ["web_researcher", "content_marketer", "create_docx"] },
  { name: "content_approval", title: "Content → Approval → Publish", outcome: "Draft content, gate for human approval, then publish.", chips: ["content_marketer", "approval", "publish"] },
  { name: "contract_redline", title: "Contract → Redline → Legal", outcome: "Extract obligations, draft a redline, get legal approval, ship.", chips: ["legal_counsel", "approval", "create_docx"] },
];

const templates = [
  {
    category: "Documents",
    items: [
      { icon: FileText, title: "Analyze this document", prompt: "Analyze the attached document and give me key insights, summary, and action items.", hint: "Attach a PDF, Word doc, or image" },
      { icon: FileText, title: "Create a competitive battle card", prompt: "Research my competitor and create a structured battle card with strengths, weaknesses, and differentiation points.", hint: "Mention competitor name" },
      { icon: PenLine, title: "Write a blog post", prompt: "Write an engaging blog post targeted at developers and technical founders.", hint: "Specify your topic" },
    ],
  },
  {
    category: "Code & Security",
    items: [
      { icon: Shield, title: "Review this code for security issues", prompt: "Review this code for security vulnerabilities, OWASP top 10 issues, and suggest fixes with code examples.", hint: "Paste your code" },
      { icon: Code, title: "Explain this codebase", prompt: "Explain the architecture and design patterns in this codebase. Identify potential improvements.", hint: "Describe the project" },
    ],
  },
  {
    category: "Research & Strategy",
    items: [
      { icon: Search, title: "Research a market trend", prompt: "Research the latest developments and create a structured report with key findings, market data, and recommendations.", hint: "Name the trend or technology" },
      { icon: BarChart3, title: "Create a quarterly review", prompt: "Analyze the provided data and create a quarterly business review with key metrics, wins, and areas for improvement.", hint: "Attach your data" },
      { icon: Briefcase, title: "Draft a sales proposal", prompt: "Draft a professional sales proposal for Acme Corp that highlights our AI solutions and value proposition.", hint: "Customize with prospect details" },
    ],
  },
];

export default function TemplatesPage() {
  const router = useRouter();
  const setConversationId = useChatStore((s) => s.setConversationId);
  const [available, setAvailable] = useState<Set<string>>(new Set());

  useEffect(() => {
    getWorkflows()
      .then((ws: WorkflowDefinition[]) => setAvailable(new Set(ws.map((w) => w.name))))
      .catch(() => {});
  }, []);

  function useTemplate(prompt: string) {
    setConversationId(undefined);
    sessionStorage.setItem("autosteer_template_prompt", prompt);
    router.push("/chat");
  }

  function runOutcome(name: string) {
    setConversationId(undefined);
    sessionStorage.setItem("autosteer_template_prompt", `run ${name}`);
    router.push("/chat");
  }

  return (
    <div className="h-full overflow-y-auto">
      <div className="max-w-3xl mx-auto px-8 py-8 space-y-8">
        <div>
          <div className="flex items-center gap-2.5 mb-1">
            <Zap className="w-5 h-5 text-blue-600" />
            <h2 className="text-base font-semibold text-slate-800">Templates</h2>
          </div>
          <p className="text-sm text-slate-500">Click any template to start a conversation with a pre-built prompt.</p>
        </div>

        <div>
          <h2 className="text-base font-semibold text-slate-800 mb-1">Outcomes</h2>
          <p className="text-sm text-slate-500 mb-4">Launch a multi-step workflow and watch it run — agents, tools, approvals.</p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {FLAGSHIP.map((f) => (
              <div key={f.name} className="flex flex-col p-4 rounded-xl border border-slate-200 bg-white hover:border-blue-300 transition-colors">
                <div className="text-sm font-semibold text-slate-800 mb-1">{f.title}</div>
                <p className="text-xs text-slate-500 mb-3 flex-1">{f.outcome}</p>
                <div className="flex flex-wrap gap-1 mb-3">
                  {f.chips.map((c) => (
                    <span key={c} className="text-[10px] text-slate-600 bg-slate-100 border border-slate-200 rounded px-1.5 py-0.5">{c}</span>
                  ))}
                </div>
                <button
                  onClick={() => runOutcome(f.name)}
                  disabled={available.size > 0 && !available.has(f.name)}
                  className="flex items-center justify-center gap-1.5 text-xs font-medium bg-blue-600 text-white rounded-lg px-3 py-2 hover:bg-blue-500 disabled:opacity-40"
                >
                  <Play className="w-3.5 h-3.5" /> Run outcome
                </button>
              </div>
            ))}
          </div>
        </div>

        {templates.map((section) => (
          <section key={section.category} className="space-y-3">
            <h3 className="text-xs font-medium text-slate-400 uppercase tracking-wider">{section.category}</h3>
            <div className="grid gap-3">
              {section.items.map((t) => {
                const Icon = t.icon;
                return (
                  <button
                    key={t.title}
                    onClick={() => useTemplate(t.prompt)}
                    className="flex items-start gap-4 p-4 rounded-xl border border-slate-200 hover:border-blue-300 hover:bg-blue-50/50 transition-all text-left group"
                  >
                    <div className="w-9 h-9 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center shrink-0 group-hover:bg-blue-100 transition-colors">
                      <Icon className="w-4 h-4 text-blue-600" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium text-slate-800 group-hover:text-blue-700">{t.title}</div>
                      <div className="text-xs text-slate-500 mt-0.5 line-clamp-1">{t.prompt}</div>
                    </div>
                    <div className="flex items-center gap-1.5 text-xs text-slate-400 group-hover:text-blue-600 shrink-0 mt-1.5">
                      <span className="text-slate-300">{t.hint}</span>
                      <ArrowRight className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 transition-opacity" />
                    </div>
                  </button>
                );
              })}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}
