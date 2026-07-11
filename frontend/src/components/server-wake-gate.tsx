"use client";

import { useEffect, useRef, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Free Render instances spin down after inactivity and take ~30-60s to wake.
 * This gate pings /api/health on mount. If the server is asleep (slow/failed),
 * it shows a modal and keeps polling until a 200, then dismisses.
 */
export function ServerWakeGate() {
  const [waking, setWaking] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const stopped = useRef(false);

  useEffect(() => {
    stopped.current = false;
    let slowTimer: ReturnType<typeof setTimeout> | null = null;
    let tick: ReturnType<typeof setInterval> | null = null;

    // If the first ping takes >2.5s, assume cold start and show the modal.
    slowTimer = setTimeout(() => {
      if (!stopped.current) {
        setWaking(true);
        tick = setInterval(() => setSeconds((s) => s + 1), 1000);
      }
    }, 2500);

    async function ping(): Promise<boolean> {
      try {
        const res = await fetch(`${API}/api/health`, { cache: "no-store" });
        return res.ok;
      } catch {
        return false;
      }
    }

    async function poll() {
      while (!stopped.current) {
        if (await ping()) {
          stopped.current = true;
          setWaking(false);
          return;
        }
        await new Promise((r) => setTimeout(r, 3000));
      }
    }

    poll();

    return () => {
      stopped.current = true;
      if (slowTimer) clearTimeout(slowTimer);
      if (tick) clearInterval(tick);
    };
  }, []);

  if (!waking) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-[#0A0A0A]/70 backdrop-blur-sm p-4">
      <div className="bg-[#F4F4F0] border-2 border-[#0A0A0A] max-w-sm w-full p-8 text-center">
        <div className="flex items-center justify-center gap-2 mb-6">
          <span className="w-2 h-2 bg-[#E61919] animate-pulse" />
          <span className="font-tele text-[10px] tracking-[0.12em]">SERVER / COLD START</span>
        </div>
        <h2 className="font-display text-2xl mb-3">WAKING UP</h2>
        <p className="font-tele text-[11px] text-ink/60 leading-relaxed">
          Free tier server is spinning up from sleep.
          <br />
          This takes up to 60 seconds. Hang tight.
        </p>
        <div className="mt-6 border-t-2 border-[#0A0A0A] pt-4">
          <span className="font-tele text-[10px] text-ink/50">ELAPSED: {seconds}s</span>
        </div>
      </div>
    </div>
  );
}
