import type { Metadata } from "next";
import { Archivo_Black } from "next/font/google";
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";
import "./globals.css";

const archivoBlack = Archivo_Black({
  subsets: ["latin"],
  weight: "400",
  variable: "--font-display",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Raah",
  description: "Multi-agent orchestration that routes every request through the right AI specialist — 43 agents across 12 departments",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${archivoBlack.variable} ${GeistSans.variable} ${GeistMono.variable}`}>
      <body className="bg-[#F4F4F0] text-[#0A0A0A] antialiased">
        {children}
      </body>
    </html>
  );
}
