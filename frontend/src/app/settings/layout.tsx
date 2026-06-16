"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Sliders, Brain, Plug, Bot, ArrowLeft } from "lucide-react";

const sections = [
  { href: "/settings/preferences", label: "Preferences", icon: Sliders, desc: "Custom instructions and behavior" },
  { href: "/settings/memory", label: "Memory", icon: Brain, desc: "Facts, documents, conversation context" },
  { href: "/settings/integrations", label: "Integrations", icon: Plug, desc: "API keys and service connections" },
  { href: "/settings/agents", label: "Agents", icon: Bot, desc: "Agent preferences and routing" },
];

export default function SettingsLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="h-full flex flex-col">
      <div className="shrink-0 border-b border-slate-200 px-5 py-3 flex items-center gap-4">
        <Link href="/" className="p-1.5 -ml-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors">
          <ArrowLeft className="w-4 h-4" />
        </Link>
        <h1 className="text-sm font-semibold text-slate-800">Settings</h1>
      </div>

      <div className="flex-1 flex overflow-hidden">
        <nav className="w-56 shrink-0 border-r border-slate-200 bg-slate-50/50 p-3 space-y-1 overflow-y-auto">
          {sections.map((s) => {
            const Icon = s.icon;
            const active = pathname === s.href || pathname.startsWith(s.href + "/");
            return (
              <Link
                key={s.href}
                href={s.href}
                className={`flex items-start gap-3 px-3 py-2.5 rounded-lg transition-colors ${
                  active
                    ? "bg-blue-50 text-blue-700 border border-blue-200/60"
                    : "text-slate-600 hover:text-slate-800 hover:bg-slate-100 border border-transparent"
                }`}
              >
                <Icon className={`w-4 h-4 mt-0.5 shrink-0 ${active ? "text-blue-600" : "text-slate-400"}`} />
                <div>
                  <div className="text-sm font-medium">{s.label}</div>
                  <div className="text-[11px] text-slate-400 mt-0.5">{s.desc}</div>
                </div>
              </Link>
            );
          })}
        </nav>

        <main className="flex-1 overflow-y-auto">{children}</main>
      </div>
    </div>
  );
}
