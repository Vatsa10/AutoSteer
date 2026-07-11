"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { LayoutShell } from "@/components/layout-shell";
import { Providers } from "@/lib/query-provider";
import { ToastContainer } from "@/components/toast";
import { ServerWakeGate } from "@/components/server-wake-gate";

function isAuthed() {
  try { return !!localStorage.getItem("autosteer_token"); } catch { return false; }
}

export default function MainLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [authed, setAuthed] = useState<boolean | null>(null);

  useEffect(() => {
    if (!isAuthed()) { router.replace("/sign-in"); return; }
    setAuthed(true);
  }, [router]);

  if (authed === null) {
    return <div className="h-screen bg-[#F4F4F0]" />;
  }

  return (
    <Providers>
      <ServerWakeGate />
      <LayoutShell>{children}</LayoutShell>
      <ToastContainer />
    </Providers>
  );
}
