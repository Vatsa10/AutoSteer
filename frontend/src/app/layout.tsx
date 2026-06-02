import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { LayoutShell } from "@/components/layout-shell";
import { Providers } from "@/lib/query-provider";
import { ToastContainer } from "@/components/toast";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "AutoSteer",
  description: "Multi-agent orchestration that routes every request through the right AI specialist — 42 agents across 12 departments",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${inter.className} bg-white text-slate-900 antialiased`}>
        <Providers>
          <LayoutShell>{children}</LayoutShell>
          <ToastContainer />
        </Providers>
      </body>
    </html>
  );
}
