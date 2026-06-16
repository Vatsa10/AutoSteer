"use client";

import { ArrowRight, Network, Brain, FileText, Search, Shield, Bot, Terminal, Download, ArrowUpRight } from "lucide-react";
import { ClerkProvider, SignInButton, SignUpButton, Show, useUser } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

function RedirectIfSignedIn() {
  const { isSignedIn } = useUser();
  const router = useRouter();
  useEffect(() => { if (isSignedIn) router.push("/chat"); }, [isSignedIn, router]);
  return null;
}

const agents = [
  "AI Research Scientist", "Content Marketer", "Security Engineer", "Product Manager",
  "Web Researcher", "Account Executive", "Legal Counsel", "CEO Agent",
  "ML Engineer", "Backend Engineer", "Data Scientist", "Product Designer",
];

function LandingContent() {
  return (
    <Show when="signed-out">
    <div className="min-h-screen bg-zinc-950 text-zinc-100 selection:bg-blue-500/30">

      {/* Nav */}
      <nav className="sticky top-0 z-50 border-b border-zinc-800/60 bg-zinc-950/80 backdrop-blur-xl">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <span className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg bg-blue-600/20 border border-blue-500/30 flex items-center justify-center">
              <Network className="w-3.5 h-3.5 text-blue-400" />
            </div>
            <span className="text-sm font-semibold tracking-tight">AutoSteer</span>
          </span>
          <div className="flex items-center gap-3">
            <SignInButton mode="modal">
              <button className="text-sm text-zinc-400 hover:text-zinc-200 transition-colors">Sign in</button>
            </SignInButton>
            <SignUpButton mode="modal">
              <button className="text-sm bg-blue-600 hover:bg-blue-500 text-white rounded-lg px-4 py-2 transition-colors font-medium">
                Get started
              </button>
            </SignUpButton>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_60%_at_50%_0%,_var(--tw-gradient-stops))] from-blue-950/40 via-zinc-950 to-zinc-950" />
        <div className="relative max-w-6xl mx-auto px-6 pt-28 pb-36">
          <div className="max-w-2xl">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-blue-500/15 bg-blue-500/5 text-blue-400 text-xs mb-8">
              <Terminal className="w-3 h-3" />
              43 agents. 12 departments. One interface.
            </div>
            <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold tracking-tighter leading-[1.08] mb-6">
              Every AI task,
              <br />
              <span className="text-blue-400">one conversation.</span>
            </h1>
            <p className="text-base text-zinc-400 max-w-lg leading-relaxed mb-10">
              Upload a document, ask for analysis, generate a report. The orchestrator picks the right agents, runs them in parallel, and returns one coherent answer. No tabs. No prompt engineering.
            </p>
            <div className="flex items-center gap-4">
              <SignUpButton mode="modal">
                <button className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white rounded-xl px-6 py-3 text-sm font-medium transition-all duration-150">
                  Start building
                  <ArrowRight className="w-4 h-4" />
                </button>
              </SignUpButton>
              <a href="https://github.com/vatsa/autosteer" target="_blank" rel="noopener" className="flex items-center gap-1.5 text-sm text-zinc-500 hover:text-zinc-300 transition-colors">
                GitHub
                <ArrowUpRight className="w-3 h-3" />
              </a>
            </div>
          </div>
        </div>
      </section>

      {/* Agent marquee */}
      <section className="border-y border-zinc-800/40 bg-zinc-900/50 overflow-hidden py-4">
        <div className="flex gap-6 animate-[scroll_30s_linear_infinite]">
          {[...agents, ...agents].map((name, i) => (
            <span key={i} className="shrink-0 flex items-center gap-2 text-sm text-zinc-400">
              <div className="w-1.5 h-1.5 rounded-full bg-blue-500/60" />
              {name}
            </span>
          ))}
        </div>
      </section>

      {/* Feature pair: Decomposition + Agents (image-text split) */}
      <section className="max-w-6xl mx-auto px-6 py-32">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
          <div>
            <div className="w-10 h-10 rounded-xl bg-blue-600/10 border border-blue-500/20 flex items-center justify-center mb-6">
              <Brain className="w-5 h-5 text-blue-400" />
            </div>
            <h2 className="text-2xl font-bold tracking-tight mb-4">One request becomes many tasks. Agents execute in parallel. You get one answer.</h2>
            <p className="text-zinc-400 leading-relaxed text-sm">
              Complex queries are decomposed by an LLM planner into subtasks with dependencies. Sub-agents run concurrently where possible. Web researcher finds sources while content marketer drafts while security engineer reviews. All you see is the finished result.
            </p>
          </div>
          <div className="bg-zinc-900 border border-zinc-800/60 rounded-2xl overflow-hidden aspect-[4/3]">
            <div className="h-full flex items-center justify-center bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-blue-950/30 via-zinc-900 to-zinc-900 p-8">
              <div className="space-y-3 w-full max-w-xs">
                {["Classifying intent", "Routing to department", "Agent selected", "Processing"].map((stage, i) => (
                  <div key={stage} className="flex items-center gap-3 text-sm">
                    <div className={`w-2 h-2 rounded-full ${i < 3 ? "bg-blue-500" : "bg-blue-500 animate-pulse"}`} />
                    <span className={i < 3 ? "text-zinc-300" : "text-blue-400"}>{stage}</span>
                    {i < 3 && <span className="text-zinc-600 text-xs ml-auto">&radic;</span>}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Feature pair: Documents + Memory (reversed split) */}
      <section className="border-t border-zinc-800/40">
        <div className="max-w-6xl mx-auto px-6 py-32">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
            <div className="order-2 lg:order-1 bg-zinc-900 border border-zinc-800/60 rounded-2xl overflow-hidden aspect-[4/3]">
              <div className="h-full flex items-center justify-center bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-amber-950/20 via-zinc-900 to-zinc-900 p-8">
                <div className="space-y-4 w-full max-w-xs">
                  <div className="flex items-center gap-2 text-sm text-amber-400"><FileText className="w-4 h-4" /> resume.pdf</div>
                  <div className="space-y-1.5">
                    {["Vatsa Joshi", "AI/ML Engineer", "Bengaluru", "4 internships", "6 projects"].map((line, i) => (
                      <div key={i} className="h-2 rounded bg-zinc-800" style={{ width: `${85 - i * 10}%` }} />
                    ))}
                  </div>
                  <div className="text-xs text-zinc-600 mt-2">Extracted 4.2KB text via PyPDF2</div>
                </div>
              </div>
            </div>
            <div className="order-1 lg:order-2">
              <div className="w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center mb-6">
                <Search className="w-5 h-5 text-amber-400" />
              </div>
              <h2 className="text-2xl font-bold tracking-tight mb-4">Upload anything. It remembers. It gets better.</h2>
              <p className="text-zinc-400 leading-relaxed text-sm">
                PDFs, Word docs, images. Extracted text becomes part of the conversation context. Documents persist across turns via SharedState. Facts extracted automatically. Four-tier memory keeps context without bloating costs.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Tool grid: bento-style */}
      <section className="border-t border-zinc-800/40">
        <div className="max-w-6xl mx-auto px-6 py-32">
          <div className="max-w-lg mb-16">
            <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center mb-6">
              <Shield className="w-5 h-5 text-emerald-400" />
            </div>
            <h2 className="text-2xl font-bold tracking-tight mb-4">47 tools. One extensible registry.</h2>
            <p className="text-zinc-400 text-sm leading-relaxed">Every agent has access to the tools it needs. DuckDuckGo search, web crawler, PDF extraction, Word generation, PowerPoint, Slack, GitHub, Notion. Add your own.</p>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {[
              { icon: Search, label: "DuckDuckGo search", bg: "bg-blue-500/10 border-blue-500/20", fg: "text-blue-400" },
              { icon: FileText, label: "PDF / DOCX extraction", bg: "bg-amber-500/10 border-amber-500/20", fg: "text-amber-400" },
              { icon: Download, label: "Word + PPT generation", bg: "bg-emerald-500/10 border-emerald-500/20", fg: "text-emerald-400" },
              { icon: Network, label: "Web crawler", bg: "bg-violet-500/10 border-violet-500/20", fg: "text-violet-400" },
              { icon: Shield, label: "Code sandbox", bg: "bg-rose-500/10 border-rose-500/20", fg: "text-rose-400" },
              { icon: Terminal, label: "Slack + GitHub APIs", bg: "bg-zinc-500/10 border-zinc-500/20", fg: "text-zinc-400" },
              { icon: Brain, label: "Semantic memory search", bg: "bg-cyan-500/10 border-cyan-500/20", fg: "text-cyan-400" },
              { icon: Bot, label: "Custom tool registry", bg: "bg-orange-500/10 border-orange-500/20", fg: "text-orange-400" },
            ].map((tool) => (
              <div key={tool.label} className="bg-zinc-900 border border-zinc-800/60 rounded-xl p-4 hover:border-zinc-700/60 transition-colors group">
                <div className={`w-8 h-8 rounded-lg border flex items-center justify-center mb-3 ${tool.bg}`}>
                  <tool.icon className={`w-3.5 h-3.5 ${tool.fg}`} />
                </div>
                <div className="text-xs text-zinc-300 font-medium">{tool.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="border-t border-zinc-800/40">
        <div className="max-w-6xl mx-auto px-6 py-32">
          <div className="bg-zinc-900 border border-zinc-800/60 rounded-3xl p-16 text-center relative overflow-hidden">
            <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-blue-950/20 via-transparent to-transparent" />
            <div className="relative">
              <h2 className="text-3xl md:text-4xl font-bold tracking-tight mb-4">Start building with 43 agents.</h2>
              <p className="text-zinc-400 max-w-md mx-auto mb-8 text-sm leading-relaxed">Free to start. Open source. Self-host or cloud.</p>
              <div className="flex items-center justify-center gap-4">
                <SignUpButton mode="modal">
                  <button className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white rounded-xl px-8 py-3.5 text-sm font-medium transition-all duration-150">
                    Get started free
                    <ArrowRight className="w-4 h-4" />
                  </button>
                </SignUpButton>
                <a href="https://github.com/vatsa/autosteer" target="_blank" rel="noopener" className="text-sm text-zinc-500 hover:text-zinc-300 transition-colors flex items-center gap-1.5">
                  View on GitHub
                  <ArrowUpRight className="w-3 h-3" />
                </a>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-zinc-800/40">
        <div className="max-w-6xl mx-auto px-6 py-10 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2.5">
            <div className="w-5 h-5 rounded-md bg-blue-600/20 border border-blue-500/30 flex items-center justify-center">
              <Network className="w-2.5 h-2.5 text-blue-400" />
            </div>
            <span className="text-xs font-medium text-zinc-500">AutoSteer</span>
          </div>
          <p className="text-xs text-zinc-600">Open source. Built with FastAPI, Next.js, PostgreSQL, Redis.</p>
        </div>
      </footer>

      <style jsx>{`
        @keyframes scroll {
          0% { transform: translateX(0); }
          100% { transform: translateX(-50%); }
        }
        .animate-\\[scroll_30s_linear_infinite\\] {
          animation: scroll 30s linear infinite;
        }
      `}</style>
    </div>
    </Show>
  );
}

export default function LandingPage() {
  return (
    <ClerkProvider>
      <RedirectIfSignedIn />
      <LandingContent />
    </ClerkProvider>
  );
}
