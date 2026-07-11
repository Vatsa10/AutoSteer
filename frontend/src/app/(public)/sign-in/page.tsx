"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, Plus } from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function AuthPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit() {
    setError("");
    if (!email.trim() || !password.trim()) { setError("Email and password required."); return; }
    if (mode === "signup" && !username.trim()) { setError("Username required."); return; }
    setBusy(true);
    try {
      const endpoint = mode === "signin" ? "/api/auth/signin" : "/api/auth/signup";
      const body: Record<string, string> = { email: email.trim(), password };
      if (mode === "signup") body.username = username.trim();
      const res = await fetch(`${API}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Authentication failed");
      localStorage.setItem("autosteer_token", data.token);
      localStorage.setItem("autosteer_user", JSON.stringify(data.user));
      router.push("/chat");
    } catch (e: any) {
      setError(e.message || "Something went wrong");
    } finally { setBusy(false); }
  }

  return (
    <div className="min-h-screen bg-[#F4F4F0] flex items-center justify-center p-6">
      <div className="w-full max-w-md">
        {/* Brand */}
        <div className="text-center mb-12">
          <div className="flex items-center justify-center gap-2 mb-4">
            <Plus className="w-4 h-4 text-[#0A0A0A]/40" />
            <span className="font-tele text-sm font-bold tracking-[0.12em]">
              AutoSteer<sup className="text-[0.6em] align-super">®</sup>
            </span>
          </div>
          <h1 className="font-display text-4xl md:text-5xl">
            {mode === "signin" ? "SIGN IN" : "SIGN UP"}
          </h1>
        </div>

        {/* Toggle */}
        <div className="grid grid-cols-2 border-2 border-[#0A0A0A] mb-8">
          <button
            onClick={() => setMode("signin")}
            className={`font-tele text-xs py-3 transition-colors ${
              mode === "signin" ? "bg-[#0A0A0A] text-[#F4F4F0]" : "hover:bg-[#0A0A0A]/[0.04]"
            }`}
          >[ SIGN IN ]</button>
          <button
            onClick={() => setMode("signup")}
            className={`font-tele text-xs py-3 border-l-2 border-[#0A0A0A] transition-colors ${
              mode === "signup" ? "bg-[#0A0A0A] text-[#F4F4F0]" : "hover:bg-[#0A0A0A]/[0.04]"
            }`}
          >[ SIGN UP ]</button>
        </div>

        {/* Form */}
        <div className="space-y-4">
          {mode === "signup" && (
            <div>
              <label className="font-tele text-[10px] text-ink/60 block mb-1">USERNAME</label>
              <input
                type="text" value={username} onChange={(e) => setUsername(e.target.value)}
                placeholder="yourname"
                className="w-full bg-transparent border-2 border-[#0A0A0A] px-4 py-3 font-tele text-sm placeholder:text-ink/20 focus:outline-none focus:border-[#E61919]"
              />
            </div>
          )}
          <div>
            <label className="font-tele text-[10px] text-ink/60 block mb-1">EMAIL</label>
            <input
              type="text" value={email} onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              className="w-full bg-transparent border-2 border-[#0A0A0A] px-4 py-3 font-tele text-sm placeholder:text-ink/20 focus:outline-none focus:border-[#E61919]"
              autoFocus
            />
          </div>
          <div>
            <label className="font-tele text-[10px] text-ink/60 block mb-1">PASSWORD</label>
            <input
              type="password" value={password} onChange={(e) => setPassword(e.target.value)}
              placeholder="········"
              className="w-full bg-transparent border-2 border-[#0A0A0A] px-4 py-3 font-tele text-sm placeholder:text-ink/20 focus:outline-none focus:border-[#E61919]"
              onKeyDown={(e) => e.key === "Enter" && submit()}
            />
          </div>

          {error && (
            <p className="font-tele text-[10px] text-[#E61919]">{error}</p>
          )}

          <button
            onClick={submit}
            disabled={busy}
            className="w-full font-tele text-xs bg-[#E61919] text-[#F4F4F0] py-4 hover:bg-[#0A0A0A] transition-colors disabled:opacity-40 flex items-center justify-center gap-2"
          >
            {busy ? "..." : `[ ${mode === "signin" ? "SIGN IN" : "CREATE ACCOUNT"} ]`}
            {!busy && <ArrowRight className="w-3.5 h-3.5" />}
          </button>
        </div>
      </div>
    </div>
  );
}
