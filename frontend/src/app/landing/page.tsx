"use client";

import Link from "next/link";
import { ArrowRight, Bot, Check, Network, Search, Slack, Github, FileText, X } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { getTools } from "@/lib/api";

const deptPacks = [
  { dept: "Product", tools: ["web_search", "notion_export", "linear_read", "posthog_read"] },
  { dept: "Engineering", tools: ["github_read", "arxiv_search", "code_sandbox_lite", "sentry_read"] },
  { dept: "Sales", tools: ["hubspot_read", "apollo_search", "email_draft", "notion_export"] },
  { dept: "Customer Success", tools: ["intercom_read", "sentry_read", "slack_post"] },
  { dept: "Operations", tools: ["linear_read", "zapier_webhook", "semantic_search"] },
  { dept: "Executive", tools: ["stripe_metrics_read", "notion_export", "calendar_read"] },
];

const pricingPlans = [
  {
    id: "self-host",
    name: "Self-host",
    price: "$0",
    period: "forever",
    description: "Run on your infrastructure with full agent definitions.",
    features: ["42 agents", "All integration tools", "Docker Compose", "No vendor lock-in"],
    cta: "Open app",
    href: "/",
    highlighted: false,
  },
  {
    id: "starter",
    name: "Hosted Starter",
    price: "$49",
    period: "/mo",
    description: "For small teams getting started with AI ops.",
    features: ["Up to 5 seats", "Live integrations hub", "Workspace credentials vault", "Email support"],
    cta: "Start trial",
    href: "/settings/integrations",
    highlighted: false,
  },
  {
    id: "team",
    name: "Hosted Team",
    price: "$199",
    period: "/mo",
    description: "For teams running cross-dept workflows daily.",
    features: ["Unlimited seats", "Custom agents", "Workflow cost caps", "Priority support", "Semantic search RAG"],
    cta: "Contact sales",
    href: "/landing#pricing",
    highlighted: true,
  },
];

const comparison = [
  { feature: "Pre-built org (42 agents)", autosteer: true, chatgpt: false, crewai: false },
  { feature: "Dept integration packs", autosteer: true, chatgpt: false, crewai: "partial" },
  { feature: "3-level routing UX", autosteer: true, chatgpt: false, crewai: false },
  { feature: "Cross-dept workflows", autosteer: true, chatgpt: false, crewai: true },
  { feature: "Per-agent tool allowlists", autosteer: true, chatgpt: false, crewai: false },
  { feature: "Self-hostable", autosteer: true, chatgpt: false, crewai: true },
];

const iconMap: Record<string, typeof Search> = {
  web_search: Search,
  slack_post: Slack,
  github_read: Github,
  notion_export: FileText,
};

function CompareCell({ value }: { value: boolean | string }) {
  if (value === true) return <Check className="w-4 h-4 text-green-600 mx-auto" />;
  if (value === false) return <X className="w-4 h-4 text-slate-300 mx-auto" />;
  return <span className="text-xs text-amber-600">{value}</span>;
}

export default function LandingPage() {
  const { data: toolsData } = useQuery({
    queryKey: ["tools"],
    queryFn: getTools,
  });

  const liveCount = toolsData?.tools.filter((t) => t.status === "live").length ?? 0;
  const betaCount = toolsData?.tools.filter((t) => t.status === "beta").length ?? 0;

  return (
    <div className="min-h-screen bg-white">
      <header className="border-b border-slate-200">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center">
              <Network className="w-4 h-4 text-blue-600" />
            </div>
            <span className="font-bold text-slate-900">AutoSteer</span>
          </div>
          <div className="flex items-center gap-3">
            <Link href="/landing#pricing" className="text-sm text-slate-600 hover:text-slate-900">
              Pricing
            </Link>
            <Link href="/" className="text-sm text-slate-600 hover:text-slate-900">
              Open app
            </Link>
            <Link
              href="/settings/integrations"
              className="text-sm px-4 py-2 rounded-lg bg-blue-600 text-white hover:bg-blue-700"
            >
              Connect integrations
            </Link>
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-16">
        <div className="text-center max-w-2xl mx-auto mb-16">
          <p className="text-sm font-medium text-blue-600 mb-3">AI company operating system</p>
          <h1 className="text-4xl md:text-5xl font-bold text-slate-900 tracking-tight leading-tight">
            42 agents. One inbox. Real integrations.
          </h1>
          <p className="text-lg text-slate-500 mt-4">
            Route every request to the right specialist — then take action in HubSpot, Intercom,
            GitHub, Notion, and Linear. Not just advice.
          </p>
          <div className="flex justify-center gap-3 mt-8">
            <Link
              href="/"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-blue-600 text-white font-medium hover:bg-blue-700"
            >
              Start chatting <ArrowRight className="w-4 h-4" />
            </Link>
            <Link
              href="/agents"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg border border-slate-200 text-slate-700 font-medium hover:bg-slate-50"
            >
              <Bot className="w-4 h-4" /> Browse agents
            </Link>
          </div>
          {liveCount > 0 && (
            <p className="text-sm text-slate-400 mt-4">
              {liveCount} live + {betaCount} beta tools registered
            </p>
          )}
        </div>

        <section id="pricing" className="mb-16 scroll-mt-8">
          <h2 className="text-xl font-semibold text-slate-900 mb-2 text-center">Pricing</h2>
          <p className="text-sm text-slate-500 text-center mb-8">
            Self-host free. Hosted tiers for teams who want zero ops.
          </p>
          <div className="grid md:grid-cols-3 gap-4">
            {pricingPlans.map((plan) => (
              <div
                key={plan.id}
                className={`rounded-xl border p-6 flex flex-col ${
                  plan.highlighted
                    ? "border-blue-300 bg-blue-50/30 shadow-sm"
                    : "border-slate-200 bg-white"
                }`}
              >
                <h3 className="font-semibold text-slate-900">{plan.name}</h3>
                <div className="mt-2 mb-3">
                  <span className="text-3xl font-bold text-slate-900">{plan.price}</span>
                  <span className="text-sm text-slate-500">{plan.period}</span>
                </div>
                <p className="text-sm text-slate-500 mb-4">{plan.description}</p>
                <ul className="space-y-2 mb-6 flex-1">
                  {plan.features.map((f) => (
                    <li key={f} className="flex items-start gap-2 text-sm text-slate-600">
                      <Check className="w-4 h-4 text-green-600 shrink-0 mt-0.5" />
                      {f}
                    </li>
                  ))}
                </ul>
                <Link
                  href={plan.href}
                  className={`text-center text-sm font-medium py-2.5 rounded-lg ${
                    plan.highlighted
                      ? "bg-blue-600 text-white hover:bg-blue-700"
                      : "border border-slate-200 text-slate-700 hover:bg-slate-50"
                  }`}
                >
                  {plan.cta}
                </Link>
              </div>
            ))}
          </div>
        </section>

        <section className="mb-16">
          <h2 className="text-xl font-semibold text-slate-900 mb-6 text-center">
            vs ChatGPT Teams & CrewAI
          </h2>
          <div className="overflow-x-auto border border-slate-200 rounded-xl">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50">
                  <th className="text-left p-3 font-medium text-slate-700">Feature</th>
                  <th className="p-3 font-medium text-blue-600">AutoSteer</th>
                  <th className="p-3 font-medium text-slate-600">ChatGPT</th>
                  <th className="p-3 font-medium text-slate-600">CrewAI</th>
                </tr>
              </thead>
              <tbody>
                {comparison.map((row) => (
                  <tr key={row.feature} className="border-b border-slate-100 last:border-0">
                    <td className="p-3 text-slate-700">{row.feature}</td>
                    <td className="p-3"><CompareCell value={row.autosteer} /></td>
                    <td className="p-3"><CompareCell value={row.chatgpt} /></td>
                    <td className="p-3"><CompareCell value={row.crewai} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="mb-16">
          <h2 className="text-xl font-semibold text-slate-900 mb-6 text-center">
            Integration packs by department
          </h2>
          <div className="grid md:grid-cols-2 gap-4">
            {deptPacks.map((pack) => (
              <div
                key={pack.dept}
                className="border border-slate-200 rounded-xl p-5 bg-slate-50/50"
              >
                <h3 className="font-medium text-slate-900 mb-3">{pack.dept}</h3>
                <div className="flex flex-wrap gap-2">
                  {pack.tools.map((tool) => {
                    const Icon = iconMap[tool] ?? Bot;
                    const tier = toolsData?.tools.find((t) => t.name === tool)?.status ?? "live";
                    return (
                      <span
                        key={tool}
                        className={`inline-flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full border ${
                          tier === "live"
                            ? "bg-green-50 text-green-800 border-green-200"
                            : tier === "beta"
                              ? "bg-amber-50 text-amber-800 border-amber-200"
                              : "bg-slate-100 text-slate-500 border-slate-200"
                        }`}
                      >
                        <Icon className="w-3 h-3" />
                        {tool.replace(/_/g, " ")}
                      </span>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        </section>

        {toolsData && (
          <section>
            <h2 className="text-xl font-semibold text-slate-900 mb-4">All tools</h2>
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-2">
              {toolsData.tools.map((tool) => (
                <div
                  key={tool.name}
                  className="flex items-center gap-2 text-sm px-3 py-2 rounded-lg border border-slate-100"
                >
                  <span
                    className={`w-1.5 h-1.5 rounded-full shrink-0 ${
                      tool.status === "live"
                        ? "bg-green-500"
                        : tool.status === "beta"
                          ? "bg-amber-500"
                          : "bg-slate-300"
                    }`}
                  />
                  <span className="font-mono text-xs text-slate-700">{tool.name}</span>
                </div>
              ))}
            </div>
          </section>
        )}
      </main>
    </div>
  );
}
