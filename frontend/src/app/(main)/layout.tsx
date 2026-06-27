"use client";

import { ClerkProvider, Show, SignInButton, SignUpButton } from "@clerk/nextjs";
import { LayoutShell } from "@/components/layout-shell";
import { Providers } from "@/lib/query-provider";
import { ToastContainer } from "@/components/toast";

export default function MainLayout({ children }: { children: React.ReactNode }) {
  return (
    <ClerkProvider>
      <Show when="signed-out">
        <div className="h-screen flex flex-col items-center justify-center gap-6 p-8">
          <div className="text-center space-y-3 max-w-md">
            <h1 className="text-2xl font-bold text-slate-800">AutoSteer</h1>
            <p className="text-sm text-slate-500">
              43 AI agents across 12 departments. One interface.
            </p>
          </div>
          <div className="flex gap-3">
            <SignInButton mode="modal">
              <button className="px-6 py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-sm font-medium transition-colors">
                Sign in
              </button>
            </SignInButton>
            <SignUpButton mode="modal">
              <button className="px-6 py-2.5 bg-white hover:bg-slate-50 text-slate-700 border border-slate-300 rounded-xl text-sm font-medium transition-colors">
                Create account
              </button>
            </SignUpButton>
          </div>
        </div>
      </Show>
      <Show when="signed-in">
        <Providers>
          <LayoutShell>{children}</LayoutShell>
          <ToastContainer />
        </Providers>
      </Show>
    </ClerkProvider>
  );
}
