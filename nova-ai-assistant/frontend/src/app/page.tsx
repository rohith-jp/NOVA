"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/store/useAuthStore";
import { useAgentStore } from "@/store/useAgentStore";
import { Button } from "@/components/ui/button";
import VoiceCommandBar from "@/components/VoiceCommandBar";
import TaskTimeline from "@/components/TaskTimeline";
import ExecutionGraph from "@/components/ExecutionGraph";
import MemoryConstellation from "@/components/MemoryConstellation";
import SecurityDashboard from "@/components/SecurityDashboard";

export default function Home() {
  const router = useRouter();
  const { user, loading, initialized, initialize, signOut } = useAuthStore();
  const { startTurn, isStreaming } = useAgentStore();

  useEffect(() => {
    const cleanup = initialize();
    return () => cleanup();
  }, [initialize]);

  useEffect(() => {
    if (initialized && !loading && !user) {
      router.push("/login");
    }
  }, [initialized, loading, user, router]);

  if (!initialized || (loading && !user)) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-950 text-white">
        <div className="flex items-center space-x-3">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent" />
          <span className="text-sm font-medium text-slate-400">Verifying session…</span>
        </div>
      </div>
    );
  }

  if (!user) return null;

  return (
    <div className="flex min-h-screen flex-col bg-slate-950 text-slate-100">
      {/* ── Header ──────────────────────────────────────────────────────────── */}
      <header className="flex items-center justify-between border-b border-slate-800 bg-slate-900/60 px-8 py-4 backdrop-blur-md">
        <div className="flex items-center space-x-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 font-bold text-white">
            N
          </div>
          <span className="text-lg font-extrabold text-white">NOVA Assistant</span>
        </div>

        <div className="flex items-center space-x-4">
          <span className="text-xs text-slate-400" id="user-email-display">
            {user.email}
          </span>
          <Button
            onClick={signOut}
            variant="outline"
            id="logout-button"
            className="border-slate-700 bg-slate-800 text-xs font-semibold text-slate-200 hover:bg-slate-700 hover:text-white"
          >
            Log Out
          </Button>
        </div>
      </header>

      {/* ── Main ────────────────────────────────────────────────────────────── */}
      <main className="flex flex-1 flex-col items-center gap-6 px-6 py-8">

        {/* Task Timeline — full conversation history */}
        <TaskTimeline />

        {/* Live Execution Graph */}
        <ExecutionGraph />

        {/* Memory Constellation & Vector Space Visualization */}
        <MemoryConstellation />

        {/* Security & Audit Telemetry Dashboard */}
        <SecurityDashboard />

        {/* Voice Command Bar — pinned above bottom */}
        <div className="w-full max-w-3xl">
          <VoiceCommandBar
            onCommand={(text) => {
              if (!isStreaming) startTurn(text);
            }}
          />
          {isStreaming && (
            <p className="mt-2 text-center text-xs text-slate-600">
              Agent is running — please wait before sending another command
            </p>
          )}
        </div>
      </main>
    </div>
  );
}
