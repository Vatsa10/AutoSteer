"use client";

import { useState, useEffect } from "react";
import { Save, Loader2 } from "lucide-react";
import { useToastStore } from "@/lib/store";
import { getPreferences, savePreferences } from "@/lib/api";

export default function PreferencesPage() {
  const addToast = useToastStore((s) => s.addToast);
  const [about, setAbout] = useState("");
  const [responseStyle, setResponseStyle] = useState("");
  const [defaultAgent, setDefaultAgent] = useState("auto");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    // Load from backend (source of truth for the LLM); fall back to localStorage cache.
    (async () => {
      try {
        const p = await getPreferences();
        setAbout(p.about || "");
        setResponseStyle(p.responseStyle || "");
        setDefaultAgent(p.defaultAgent || "auto");
        return;
      } catch {}
      try {
        const stored = localStorage.getItem("autosteer_preferences");
        if (stored) {
          const p = JSON.parse(stored);
          setAbout(p.about || "");
          setResponseStyle(p.responseStyle || "");
          setDefaultAgent(p.defaultAgent || "auto");
        }
      } catch {}
    })();
  }, []);

  async function handleSave() {
    setSaving(true);
    const prefs = { about, responseStyle, defaultAgent };
    try {
      await savePreferences(prefs); // persist to DB so the LLM sees it
      localStorage.setItem("autosteer_preferences", JSON.stringify(prefs)); // cache
      addToast("Preferences saved", "success");
    } catch (e) {
      addToast(e instanceof Error ? e.message : "Failed to save", "error");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="max-w-2xl px-8 py-8 space-y-10">
      <div>
        <h2 className="text-base font-semibold text-slate-800 mb-1">Preferences</h2>
        <p className="text-sm text-slate-500">
          What AutoSteer knows about you and how it should respond.
        </p>
      </div>

      <section className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1.5">
            What should AutoSteer know about you?
          </label>
          <p className="text-xs text-slate-400 mb-2">
            Tell AutoSteer about yourself — your role, projects, preferences. This context is included in every conversation to give you better answers.
          </p>
          <textarea
            value={about}
            onChange={(e) => setAbout(e.target.value)}
            placeholder="I'm a full-stack engineer working on an AI orchestration platform. I prefer TypeScript and Python. My team uses Linear for project tracking and deploys on AWS..."
            rows={6}
            className="w-full bg-white border border-slate-300 rounded-xl px-4 py-3 text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-200 transition-all resize-none"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1.5">
            How should AutoSteer respond?
          </label>
          <p className="text-xs text-slate-400 mb-2">
            Set your preferred communication style, detail level, and any constraints.
          </p>
          <textarea
            value={responseStyle}
            onChange={(e) => setResponseStyle(e.target.value)}
            placeholder="Be concise and code-focused. Use bullet points for lists. Never use emoji. When generating code, include TypeScript types. Prefer practical examples over theoretical explanations."
            rows={4}
            className="w-full bg-white border border-slate-300 rounded-xl px-4 py-3 text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-200 transition-all resize-none"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1.5">
            Default routing preference
          </label>
          <p className="text-xs text-slate-400 mb-2">
            When AutoSteer routes your request, prefer this mode.
          </p>
          <select
            value={defaultAgent}
            onChange={(e) => setDefaultAgent(e.target.value)}
            className="w-full bg-white border border-slate-300 rounded-lg px-3 py-2 text-sm text-slate-900 focus:outline-none focus:border-blue-400"
          >
            <option value="auto">Auto (let the system decide)</option>
            <option value="fastest">Fastest available agent</option>
            <option value="most_capable">Most capable agent</option>
          </select>
        </div>
      </section>

      <button
        onClick={handleSave}
        disabled={saving}
        className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-xl px-5 py-2.5 text-sm font-medium transition-colors"
      >
        {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
        Save preferences
      </button>
    </div>
  );
}
