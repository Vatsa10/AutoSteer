import { ClerkProvider } from "@clerk/nextjs";

export default function PublicLayout({ children }: { children: React.ReactNode }) {
  return (
    <ClerkProvider>
      <div className="min-h-screen bg-zinc-950 text-zinc-100">{children}</div>
    </ClerkProvider>
  );
}
