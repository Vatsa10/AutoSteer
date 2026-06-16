"use client";

import { useEffect, useState, type ReactNode } from "react";
import { Plus, ArrowUpRight, Menu, X } from "lucide-react";
import { ClerkProvider, SignInButton, SignUpButton, Show, useUser } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import { motion, useReducedMotion, MotionConfig } from "motion/react";

const EASE = [0.16, 1, 0.3, 1] as const;
const GITHUB = "https://github.com/vatsa10/autosteer";

function RedirectIfSignedIn() {
  const { isSignedIn } = useUser();
  const router = useRouter();
  useEffect(() => { if (isSignedIn) router.push("/chat"); }, [isSignedIn, router]);
  return null;
}

// ── Primitives ───────────────────────────────────────────────
function Crosshair({ className = "" }: { className?: string }) {
  return <Plus className={`w-3 h-3 text-ink/40 ${className}`} strokeWidth={2} aria-hidden />;
}

function HazardButton({ children }: { children: ReactNode }) {
  return (
    <SignUpButton mode="modal">
      <button className="font-tele text-xs bg-[#e61919] text-[#f4f4f0] px-5 py-3 transition-transform active:scale-[0.98] hover:bg-[#0a0a0a]">
        [ {children} ]
      </button>
    </SignUpButton>
  );
}

function Reveal({ children, delay = 0 }: { children: ReactNode; delay?: number }) {
  const reduce = useReducedMotion();
  return (
    <motion.div
      initial={reduce ? false : { opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.3 }}
      transition={{ duration: 0.7, delay, ease: EASE }}
    >
      {children}
    </motion.div>
  );
}

// ── Nav ──────────────────────────────────────────────────────
function Nav() {
  const [open, setOpen] = useState(false);
  return (
    <nav className="fixed inset-x-0 top-0 z-50 h-[68px] border-b-2 border-[#0a0a0a] bg-[#f4f4f0]">
      <div className="max-w-[1400px] mx-auto h-full px-6 flex items-center justify-between">
        <span className="font-tele text-sm font-bold tracking-[0.12em]">
          AUTOSTEER<sup className="text-[0.6em] align-super">®</sup>
        </span>

        <div className="hidden md:flex items-center gap-6">
          <a href={GITHUB} target="_blank" rel="noopener" className="font-tele text-xs text-ink/60 hover:text-[#0a0a0a] transition-colors flex items-center gap-1">
            GITHUB <ArrowUpRight className="w-3 h-3" strokeWidth={2} />
          </a>
          <SignInButton mode="modal">
            <button className="font-tele text-xs hover:text-[#e61919] transition-colors">SIGN IN</button>
          </SignInButton>
          <HazardButton>GET STARTED</HazardButton>
        </div>

        <button className="md:hidden" onClick={() => setOpen((v) => !v)} aria-label="Menu">
          {open ? <X className="w-5 h-5" strokeWidth={2} /> : <Menu className="w-5 h-5" strokeWidth={2} />}
        </button>
      </div>

      {open && (
        <div className="md:hidden border-b-2 border-[#0a0a0a] bg-[#f4f4f0] px-6 py-5 flex flex-col gap-4">
          <a href={GITHUB} target="_blank" rel="noopener" className="font-tele text-xs text-ink/60">GITHUB ›</a>
          <SignInButton mode="modal"><button className="font-tele text-xs text-left">SIGN IN</button></SignInButton>
          <HazardButton>GET STARTED</HazardButton>
        </div>
      )}
    </nav>
  );
}

// ── Hero ─────────────────────────────────────────────────────
function Hero() {
  const reduce = useReducedMotion();
  return (
    <section className="relative min-h-[100dvh] border-b-2 border-[#0a0a0a] pt-[68px] overflow-hidden">
      <div className="max-w-[1400px] mx-auto px-6 grid grid-cols-1 lg:grid-cols-12 min-h-[calc(100dvh-68px)]">
        {/* Left: macro headline */}
        <div className="lg:col-span-7 flex flex-col justify-center py-16 lg:pr-10 lg:border-r-2 lg:border-[#0a0a0a]">
          <motion.p
            initial={reduce ? false : { opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.5 }}
            className="font-tele text-[11px] text-[#e61919] mb-8"
          >
            [ MULTI-AGENT ORCHESTRATION SYSTEM / REV 2.6 ]
          </motion.p>

          <h1 className="font-display text-[clamp(2.75rem,9vw,7.5rem)]">
            {["EVERY AI TASK.", "ONE CONVERSATION."].map((line, i) => (
              <motion.span
                key={line}
                initial={reduce ? false : { opacity: 0, y: 40 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.8, delay: 0.1 + i * 0.12, ease: EASE }}
                className="block"
              >
                {line}
              </motion.span>
            ))}
          </h1>

          <motion.p
            initial={reduce ? false : { opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.6, delay: 0.45 }}
            className="font-tele text-xs text-ink/70 mt-8 max-w-md leading-relaxed"
          >
            ONE REQUEST DECOMPOSED INTO A TASK GRAPH. AGENTS RUN IN PARALLEL. ONE COHERENT ANSWER RETURNED.
          </motion.p>

          <motion.div
            initial={reduce ? false : { opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.6 }}
            className="flex items-center gap-6 mt-10"
          >
            <HazardButton>GET STARTED</HazardButton>
            <a href={GITHUB} target="_blank" rel="noopener" className="font-tele text-xs text-ink/60 hover:text-[#0a0a0a] transition-colors flex items-center gap-1">
              VIEW ON GITHUB <ArrowUpRight className="w-3.5 h-3.5" strokeWidth={2} />
            </a>
          </motion.div>
        </div>

        {/* Right: bleeding numeral */}
        <div className="lg:col-span-5 relative flex flex-col justify-center items-end border-t-2 border-[#0a0a0a] lg:border-t-0 py-16 lg:py-0 overflow-hidden">
          <div className="absolute inset-0 halftone opacity-[0.07]" aria-hidden />
          <motion.span
            initial={reduce ? false : { opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.9, delay: 0.3, ease: EASE }}
            className="relative font-display text-[#e61919] text-[clamp(7rem,18vw,16rem)] leading-none select-none -mr-2"
          >
            43
          </motion.span>
          <p className="relative font-tele text-[11px] text-ink/60 mt-4 text-right">
            SPECIALIZED AGENTS<br />UNIT / D-01
          </p>
        </div>
      </div>
    </section>
  );
}

// ── Telemetry strip ──────────────────────────────────────────
const LOG = [
  "CLASSIFY INTENT",
  "ROUTE > DATA_ANALYTICS",
  "DECOMPOSE > 3 SUBTASKS",
  "SUB-AGENTS RUNNING ×3",
  "SYNTHESIZE RESULTS",
];

function Telemetry() {
  const reduce = useReducedMotion();
  return (
    <section className="bg-[#0a0a0a] text-[#f4f4f0] border-b-2 border-[#0a0a0a]">
      <div className="max-w-[1400px] mx-auto px-6 py-5 flex flex-col lg:flex-row lg:items-center gap-4 lg:gap-8">
        <div className="flex items-center gap-3 shrink-0">
          <span className="w-2 h-2 bg-[#e61919] animate-breathe" aria-hidden />
          <span className="font-tele text-[11px]">
            <span className="text-[#e61919]">{">"}</span> ROUTE &quot;ANALYZE Q3 TRENDS&quot;
          </span>
        </div>
        <div className="flex flex-wrap items-center gap-x-5 gap-y-2">
          {LOG.map((l, i) => (
            <motion.span
              key={l}
              initial={reduce ? false : { opacity: 0 }}
              whileInView={{ opacity: 1 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.12, duration: 0.3 }}
              className="font-tele text-[10px] text-paper/70 flex items-center gap-2"
            >
              <span className="text-[#e61919]">OK</span> {l}
              {i < LOG.length - 1 && <span className="text-paper/30 ml-3">{">>>"}</span>}
            </motion.span>
          ))}
        </div>
      </div>
    </section>
  );
}

// ── Capability ledger ────────────────────────────────────────
const LEDGER = [
  {
    n: "01",
    title: "DECOMPOSE & ROUTE",
    body: "An LLM planner breaks each request into a directed acyclic graph of subtasks with dependencies, then routes each to the right department of 12.",
  },
  {
    n: "02",
    title: "RUN IN PARALLEL",
    body: "Web researcher finds sources while content drafts while security reviews — concurrent sub-agents, one synthesized response.",
  },
  {
    n: "03",
    title: "REMEMBER EVERYTHING",
    body: "Four-tier memory plus pgvector semantic recall. Uploaded PDFs, Word docs and images are extracted into persistent conversation context.",
  },
  {
    n: "04",
    title: "GENERATE DOCUMENTS",
    body: "Native Word and PowerPoint output from any conversation — 8 slide layouts, 4 themes, download link in the response.",
  },
];

function Ledger() {
  return (
    <section className="border-b-2 border-[#0a0a0a]">
      <div className="max-w-[1400px] mx-auto px-6 py-24 md:py-32">
        <Reveal>
          <h2 className="font-display text-[clamp(2rem,6vw,4.5rem)] mb-16">
            HOW IT<br className="md:hidden" /> OPERATES
          </h2>
        </Reveal>
        <dl className="grid grid-cols-1 md:grid-cols-2">
          {LEDGER.map((item, i) => (
            <Reveal key={item.n} delay={i * 0.05}>
              <div className={`flex gap-6 py-10 md:px-10 border-t-2 border-[#0a0a0a] ${i % 2 === 0 ? "md:border-r-2" : ""} h-full`}>
                <span className="font-tele text-sm text-[#e61919] shrink-0">{item.n}</span>
                <div>
                  <dt className="font-display text-2xl md:text-3xl mb-3">{item.title}</dt>
                  <dd className="font-sans text-sm text-ink/70 leading-relaxed max-w-sm">{item.body}</dd>
                </div>
              </div>
            </Reveal>
          ))}
        </dl>
      </div>
    </section>
  );
}

// ── Oversized numerals ───────────────────────────────────────
const STATS = [
  { v: "43", l: "AGENTS" },
  { v: "12", l: "DEPARTMENTS" },
  { v: "47", l: "TOOLS" },
  { v: "4", l: "TIER MEMORY" },
];

function Numerals() {
  return (
    <section className="border-b-2 border-[#0a0a0a] bg-[#0a0a0a]">
      <div className="max-w-[1400px] mx-auto grid grid-cols-2 md:grid-cols-4 gap-[2px] bg-[#0a0a0a]">
        {STATS.map((s, i) => (
          <Reveal key={s.l} delay={i * 0.06}>
            <div className="bg-[#f4f4f0] flex flex-col items-center justify-center py-14 h-full relative">
              <Crosshair className="absolute top-3 left-3" />
              <span className="font-display text-[clamp(4rem,11vw,9rem)] text-[#0a0a0a]">{s.v}</span>
              <span className="font-tele text-[10px] text-ink/60 mt-2">{s.l}</span>
            </div>
          </Reveal>
        ))}
      </div>
    </section>
  );
}

// ── Tool registry ────────────────────────────────────────────
const TOOLS = [
  "DDG_SEARCH", "WEB_CRAWL", "ARXIV_SEARCH", "SEMANTIC_SEARCH",
  "CREATE_DOCX", "CREATE_PPTX", "PDF_EXTRACT", "CODE_SANDBOX",
  "SLACK_POST", "GITHUB_ISSUE", "NOTION_SYNC", "FILE_UPLOAD",
];

function Registry() {
  return (
    <section className="border-b-2 border-[#0a0a0a]">
      <div className="max-w-[1400px] mx-auto px-6 py-24 md:py-32">
        <Reveal>
          <p className="font-tele text-[11px] text-[#e61919] mb-4">[ TOOL REGISTRY / 47 INTEGRATED ]</p>
          <h2 className="font-display text-[clamp(2rem,6vw,4.5rem)] mb-12">
            EXTENSIBLE<br className="md:hidden" /> BY DEFAULT
          </h2>
        </Reveal>
        <Reveal delay={0.05}>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-[2px] bg-[#0a0a0a] border-2 border-[#0a0a0a]">
            {TOOLS.map((t) => (
              <div key={t} className="bg-[#f4f4f0] px-5 py-6 font-tele text-xs hover:bg-[#e61919] hover:text-[#f4f4f0] transition-colors">
                {t}
              </div>
            ))}
          </div>
          <p className="font-tele text-[10px] text-ink/50 mt-4">+ 35 MORE IN THE REGISTRY · ZERO-CONFIG EXTENSION</p>
        </Reveal>
      </div>
    </section>
  );
}

// ── CTA ──────────────────────────────────────────────────────
function CTA() {
  return (
    <section className="bg-[#0a0a0a] text-[#f4f4f0] border-b-2 border-[#0a0a0a]">
      <div className="max-w-[1400px] mx-auto px-6 py-28 md:py-40">
        <Reveal>
          <h2 className="font-display text-[clamp(2.5rem,9vw,8rem)]">
            STOP<br />SWITCHING<br /><span className="text-[#e61919]">TABS.</span>
          </h2>
          <div className="flex flex-col sm:flex-row sm:items-center gap-6 mt-12">
            <HazardButton>GET STARTED</HazardButton>
            <p className="font-tele text-[11px] text-paper/60">FREE TO START · OPEN SOURCE · SELF-HOST OR CLOUD</p>
          </div>
        </Reveal>
      </div>
    </section>
  );
}

// ── Footer ───────────────────────────────────────────────────
function Footer() {
  return (
    <footer className="max-w-[1400px] mx-auto px-6 py-10 grid grid-cols-1 sm:grid-cols-3 gap-6 items-center">
      <span className="font-tele text-xs font-bold tracking-[0.12em]">
        AUTOSTEER<sup className="text-[0.6em] align-super">®</sup>
      </span>
      <p className="font-tele text-[10px] text-ink/50 sm:text-center">FASTAPI · NEXT.JS · POSTGRESQL · REDIS</p>
      <p className="font-tele text-[10px] text-ink/50 sm:text-right">REV 2.6 / © 2026</p>
    </footer>
  );
}

// ── Page ─────────────────────────────────────────────────────
export default function LandingPage() {
  return (
    <ClerkProvider>
      <RedirectIfSignedIn />
      <Show when="signed-out">
        <MotionConfig reducedMotion="user">
          <div className="grain bg-[#f4f4f0] text-[#0a0a0a]">
            <Nav />
            <Hero />
            <Telemetry />
            <Ledger />
            <Numerals />
            <Registry />
            <CTA />
            <Footer />
          </div>
        </MotionConfig>
      </Show>
    </ClerkProvider>
  );
}
