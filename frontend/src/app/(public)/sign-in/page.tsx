"use client";

import { SignIn } from "@clerk/nextjs";
import Link from "next/link";
import { Network } from "lucide-react";

export default function SignInPage() {
  return (
    <div className="min-h-screen flex">
      <div className="hidden lg:flex w-1/2 bg-zinc-900 items-center justify-center p-16 relative overflow-hidden">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_bottom_left,_var(--tw-gradient-stops))] from-blue-900/30 via-transparent to-transparent" />
        <div className="relative max-w-md">
          <Link href="/landing" className="flex items-center gap-2.5 mb-12">
            <div className="w-8 h-8 rounded-lg bg-blue-600/20 border border-blue-500/30 flex items-center justify-center">
              <Network className="w-4 h-4 text-blue-400" />
            </div>
            <span className="text-lg font-semibold tracking-tight text-zinc-100">AutoSteer</span>
          </Link>
          <blockquote className="text-2xl font-medium text-zinc-300 leading-relaxed">
            One interface for research, writing, coding, analysis, and document generation.
          </blockquote>
          <div className="mt-8 flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-blue-600/20 border border-blue-500/30" />
            <div>
              <div className="text-sm font-medium text-zinc-200">43 AI agents</div>
              <div className="text-xs text-zinc-500">12 departments. 47 tools.</div>
            </div>
          </div>
        </div>
      </div>
      <div className="flex-1 flex items-center justify-center p-8">
        <SignIn
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
