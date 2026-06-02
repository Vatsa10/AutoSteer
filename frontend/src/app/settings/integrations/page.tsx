"use client";

import { useState } from "react";
import {
  CheckCircle2,
  Loader2,
  Plug,
  Unplug,
  Zap,
} from "lucide-react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  connectIntegration,
  disconnectIntegration,
  getIntegrations,
  testIntegration,
  type IntegrationProvider,
} from "@/lib/api";

function StatusDot({ connected }: { connected: boolean }) {
  return (
    <span
      className={`inline-block w-2 h-2 rounded-full ${connected ? "bg-green-500" : "bg-slate-300"}`}
    />
  );
}

function ProviderCard({ provider }: { provider: IntegrationProvider }) {
  const queryClient = useQueryClient();
  const [token, setToken] = useState("");
  const [notionPageId, setNotionPageId] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function handleConnect() {
    setBusy("connect");
    setMessage(null);
    try {
      const metadata =
        provider.id === "notion" && notionPageId
          ? { default_page_id: notionPageId }
          : undefined;
      await connectIntegration(provider.id, token, metadata);
      setToken("");
      setMessage("Connected successfully");
      queryClient.invalidateQueries({ queryKey: ["integrations"] });
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Connect failed");
    } finally {
      setBusy(null);
    }
  }

  async function handleTest() {
    setBusy("test");
    setMessage(null);
    try {
      const result = await testIntegration(provider.id);
      setMessage(result.ok ? "Connection OK" : result.error || "Test failed");
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Test failed");
    } finally {
      setBusy(null);
    }
  }

  async function handleDisconnect() {
    setBusy("disconnect");
    try {
      await disconnectIntegration(provider.id);
      setMessage("Disconnected");
      queryClient.invalidateQueries({ queryKey: ["integrations"] });
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="border border-slate-200 rounded-xl p-5 bg-white shadow-sm">
      <div className="flex items-start justify-between gap-3 mb-3">
        <div>
          <div className="flex items-center gap-2">
            <StatusDot connected={provider.connected} />
            <h3 className="font-semibold text-slate-900">{provider.name}</h3>
          </div>
          <p className="text-sm text-slate-500 mt-1">{provider.description}</p>
        </div>
        {provider.connected ? (
          <span className="text-xs px-2 py-1 rounded-full bg-green-50 text-green-700 border border-green-200">
            {provider.connection_source === "env" ? "Env" : "Connected"}
          </span>
        ) : (
          <span className="text-xs px-2 py-1 rounded-full bg-slate-50 text-slate-500 border border-slate-200">
            Not connected
          </span>
        )}
      </div>

      <p className="text-xs text-slate-400 mb-3 font-mono">{provider.env_var}</p>

      {!provider.connected && (
        <div className="space-y-2 mb-3">
          <input
            type="password"
            placeholder="API token / bot token"
            value={token}
            onChange={(e) => setToken(e.target.value)}
            className="w-full text-sm px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/30"
          />
          {provider.id === "notion" && (
            <input
              type="text"
              placeholder="Default parent page ID (optional)"
              value={notionPageId}
              onChange={(e) => setNotionPageId(e.target.value)}
              className="w-full text-sm px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/30"
            />
          )}
        </div>
      )}

      <div className="flex flex-wrap gap-2">
        {!provider.connected && (
          <button
            onClick={handleConnect}
            disabled={!token || busy !== null}
            className="inline-flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {busy === "connect" ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Plug className="w-3.5 h-3.5" />}
            Connect
          </button>
        )}
        {provider.connected && provider.connection_source !== "env" && (
          <button
            onClick={handleDisconnect}
            disabled={busy !== null}
            className="inline-flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50"
          >
            <Unplug className="w-3.5 h-3.5" />
            Disconnect
          </button>
        )}
        <button
          onClick={handleTest}
          disabled={busy !== null}
          className="inline-flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50"
        >
          {busy === "test" ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Zap className="w-3.5 h-3.5" />}
          Test
        </button>
      </div>

      {message && (
        <p className="text-xs mt-2 text-slate-500">{message}</p>
      )}
    </div>
  );
}

export default function IntegrationsPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["integrations"],
    queryFn: getIntegrations,
  });

  return (
    <div className="h-full overflow-y-auto">
      <div className="max-w-3xl mx-auto px-6 py-8">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-slate-900">Integrations</h1>
          <p className="text-slate-500 mt-1">
            Connect external services for your workspace. Tokens are encrypted at rest.
          </p>
        </div>

        {isLoading && (
          <div className="flex justify-center py-12">
            <Loader2 className="w-6 h-6 text-slate-400 animate-spin" />
          </div>
        )}

        {error && (
          <p className="text-red-600 text-sm">Failed to load integrations. Is the backend running?</p>
        )}

        {data && (
          <div className="grid gap-4">
            {data.providers.map((p) => (
              <ProviderCard key={p.id} provider={p} />
            ))}
          </div>
        )}

        <div className="mt-8 p-4 rounded-xl bg-slate-50 border border-slate-200 text-sm text-slate-600">
          <div className="flex items-center gap-2 font-medium text-slate-800 mb-2">
            <CheckCircle2 className="w-4 h-4 text-green-600" />
            Self-hosted shortcut
          </div>
          <p>
            Set env vars in <code className="text-xs bg-white px-1 py-0.5 rounded border">backend/.env</code> instead
            of connecting here. See{" "}
            <a href="https://github.com" className="text-blue-600 hover:underline">
              docs/integrations.md
            </a>
            .
          </p>
        </div>
      </div>
    </div>
  );
}
