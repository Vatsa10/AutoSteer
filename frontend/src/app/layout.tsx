import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { LayoutShell } from "@/components/layout-shell";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "AutoSteer",
  description: "Multi-agent orchestration that routes every request through the right AI specialist — 42 agents across 12 departments",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.className} bg-warm-950 text-warm-100 antialiased`}>
        <LayoutShell>{children}</LayoutShell>
      </body>
    </html>
  );
}
