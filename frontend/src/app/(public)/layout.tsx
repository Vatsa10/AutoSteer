import { ServerWakeGate } from "@/components/server-wake-gate";

export default function PublicLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-[#F4F4F0] text-[#0A0A0A]">
      <ServerWakeGate />
      {children}
    </div>
  );
}
