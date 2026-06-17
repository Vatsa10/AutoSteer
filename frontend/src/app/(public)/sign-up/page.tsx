"use client";

import { SignUp } from "@clerk/nextjs";
import Link from "next/link";
import { Network } from "lucide-react";

export default function SignUpPage() {
  return (
    <div className="min-h-screen flex">
      <div className="hidden lg:flex w-1/2 bg-zinc-900 items-center justify-center p-16 relative overflow-hidden">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_bottom_left,_var(--tw-gradient-stops))] from-blue-900/30 via-transparent to-transparent" />
        <div className="relative max-w-md">
          <Link href="/landing" className="flex items-center gap-2.5 mb-12">
            <div className="w-8 h-8 rounded-lg bg-blue-600/20 border border-blue-500/30 flex items-center justify-center">
              <Network className="w-4 h-4 text-blue-400" />
            </div>
            <span className="text-lg font-semibold tracking-tight text-zinc-100">Raah</span>
          </Link>
          <div className="space-y-6">
            <h2 className="text-2xl font-bold text-zinc-100">Everything you need</h2>
            <ul className="space-y-4">
              {[
                "43 specialized AI agents across 12 departments",
                "Upload PDFs, Word docs, images for instant analysis",
                "Generate professional documents and presentations",
                "Multi-agent workflows that run in parallel",
                "Memory that compounds as you use it",
              ].map((item) => (
                <li key={item} className="flex items-start gap-3 text-sm text-zinc-400">
                  <span className="w-1.5 h-1.5 rounded-full bg-blue-500 mt-1.5 shrink-0" />
                  {item}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
      <div className="flex-1 flex items-center justify-center p-8">
        <SignUp
          appearance={{
            elements: {
              rootBox: "w-full max-w-sm",
              card: "bg-transparent shadow-none",
              headerTitle: "text-zinc-100 text-xl font-semibold",
              headerSubtitle: "text-zinc-500 text-sm",
              formFieldLabel: "text-zinc-400 text-sm",
              formFieldInput: "bg-zinc-900 border-zinc-700 text-zinc-100 rounded-lg focus:border-blue-500",
              formButtonPrimary: "bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-medium",
              footerActionLink: "text-blue-400 hover:text-blue-300",
              dividerLine: "bg-zinc-800",
              dividerText: "text-zinc-600",
              socialButtonsBlockButton: "bg-zinc-900 border-zinc-700 text-zinc-300 hover:bg-zinc-800 rounded-lg",
            },
          }}
        />
      </div>
    </div>
  );
}
