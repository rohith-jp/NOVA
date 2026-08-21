"use client";

import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";

export interface StreamEvent {
  id: string;
  event: "CONNECTED" | "PLAN" | "TOOL_CALL" | "EVIDENCE" | "DECISION" | "SUCCESS" | "ERROR";
  timestamp: number;
  data: any;
}

export default function AgentStreamListener() {
  const [command, setCommand] = useState("Search for Next.js 15 features and summarize");
  const [isStreaming, setIsStreaming] = useState(false);
  const [events, setEvents] = useState<StreamEvent[]>([]);
  const [statusMessage, setStatusMessage] = useState<string>("Ready to stream agent execution.");
  const wsRef = useRef<WebSocket | null>(null);
  const eventsEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    eventsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [events]);

  const startStream = () => {
    if (!command.trim()) return;

    if (wsRef.current) {
      wsRef.current.close();
    }

    setEvents([]);
    setIsStreaming(true);
    setStatusMessage("Connecting to NOVA Agent Stream...");

    const ws = new WebSocket("ws://localhost:8000/ws/stream");
    wsRef.current = ws;

    ws.onopen = () => {
      setStatusMessage("WebSocket connected. Sending command...");
      ws.send(JSON.stringify({ command }));
    };

    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        const newEvt: StreamEvent = {
          id: Math.random().toString(36).substring(2, 9),
          event: payload.event,
          timestamp: payload.timestamp || Date.now() / 1000,
          data: payload.data || payload.message,
        };

        setEvents((prev) => [...prev, newEvt]);

        if (payload.event === "SUCCESS") {
          setIsStreaming(false);
          setStatusMessage("Execution completed successfully!");
        } else if (payload.event === "ERROR") {
          setIsStreaming(false);
          setStatusMessage(`Execution stopped: ${payload.data?.error || "Error occurred"}`);
        }
      } catch (err) {
        console.error("Failed to parse WS message:", err);
      }
    };

    ws.onerror = (err) => {
      console.error("WebSocket error:", err);
      setIsStreaming(false);
      setStatusMessage("WebSocket connection error.");
    };

    ws.onclose = () => {
      setIsStreaming(false);
    };
  };

  const getEventBadge = (type: string) => {
    switch (type) {
      case "PLAN":
        return "bg-indigo-500/20 text-indigo-300 border-indigo-500/30";
      case "TOOL_CALL":
        return "bg-blue-500/20 text-blue-300 border-blue-500/30";
      case "EVIDENCE":
        return "bg-amber-500/20 text-amber-300 border-amber-500/30";
      case "DECISION":
        return "bg-teal-500/20 text-teal-300 border-teal-500/30";
      case "SUCCESS":
        return "bg-emerald-500/20 text-emerald-300 border-emerald-500/30";
      case "ERROR":
        return "bg-red-500/20 text-red-300 border-red-500/30";
      default:
        return "bg-slate-800 text-slate-400 border-slate-700";
    }
  };

  return (
    <div className="w-full max-w-3xl space-y-6 rounded-2xl border border-slate-800 bg-slate-900/90 p-6 shadow-2xl backdrop-blur-xl">
      <div className="flex items-center justify-between border-b border-slate-800 pb-4">
        <div>
          <h2 className="text-lg font-bold text-white">Live Agent Event Stream</h2>
          <p className="text-xs text-slate-400">
            Real-time WebSocket event listener (PLAN → TOOL_CALL → EVIDENCE → DECISION → SUCCESS/ERROR)
          </p>
        </div>
        <span className="rounded-full border border-indigo-500/20 bg-indigo-500/10 px-3 py-1 text-xs font-semibold text-indigo-400">
          ws://localhost:8000/ws/stream
        </span>
      </div>

      {/* Input Command Control */}
      <div className="space-y-3">
        <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400">
          Agent Command
        </label>
        <div className="flex space-x-3">
          <input
            type="text"
            value={command}
            onChange={(e) => setCommand(e.target.value)}
            disabled={isStreaming}
            placeholder="Enter command for agent..."
            className="flex-1 rounded-lg border border-slate-800 bg-slate-950 px-4 py-2.5 text-sm text-white placeholder-slate-500 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 disabled:opacity-50"
          />
          <Button
            onClick={startStream}
            disabled={isStreaming || !command.trim()}
            className="bg-indigo-600 font-semibold text-white hover:bg-indigo-500 disabled:opacity-50"
          >
            {isStreaming ? (
              <div className="flex items-center space-x-2">
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                <span>Streaming...</span>
              </div>
            ) : (
              "Stream Command"
            )}
          </Button>
        </div>
        <p className="text-xs text-slate-500">{statusMessage}</p>
      </div>

      {/* Event Feed Console */}
      <div className="space-y-3">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
          Event Feed ({events.length} events)
        </h3>
        <div className="h-80 overflow-y-auto rounded-xl border border-slate-800 bg-slate-950 p-4 space-y-3 scrollbar-thin scrollbar-thumb-slate-800">
          {events.length === 0 ? (
            <div className="flex h-full items-center justify-center text-xs text-slate-600">
              No stream events received yet. Click "Stream Command" to trigger live execution.
            </div>
          ) : (
            events.map((evt) => (
              <div
                key={evt.id}
                className="rounded-lg border border-slate-800/80 bg-slate-900/60 p-3 text-xs space-y-1.5 transition-all"
              >
                <div className="flex items-center justify-between">
                  <span
                    className={`rounded-md border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${getEventBadge(
                      evt.event
                    )}`}
                  >
                    {evt.event}
                  </span>
                  <span className="font-mono text-[10px] text-slate-500">
                    {new Date(evt.timestamp * 1000).toLocaleTimeString()}
                  </span>
                </div>

                {evt.event === "PLAN" && (
                  <div className="space-y-1 text-slate-300">
                    <p className="font-semibold text-indigo-300">{evt.data?.summary}</p>
                    <div className="space-y-1 pl-2">
                      {evt.data?.steps?.map((step: any) => (
                        <div key={step.step_number} className="text-[11px] text-slate-400">
                          <span className="text-indigo-400 font-mono">Step {step.step_number}:</span>{" "}
                          {step.purpose}{" "}
                          {step.tool && (
                            <span className="text-amber-400/90">[{step.tool}]</span>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {evt.event === "TOOL_CALL" && (
                  <p className="text-slate-300">
                    <span className="text-blue-400 font-semibold">Invoking Tool:</span>{" "}
                    <span className="font-mono text-amber-300">{evt.data?.tool}</span> — Step{" "}
                    {evt.data?.step_number}: {evt.data?.purpose}
                  </p>
                )}

                {evt.event === "EVIDENCE" && (
                  <div className="text-slate-300 space-y-1">
                    <span className="text-amber-400 font-semibold">Evidence Collected:</span>
                    <pre className="overflow-x-auto rounded bg-slate-950 p-2 font-mono text-[10px] text-slate-300">
                      {JSON.stringify(evt.data?.output, null, 2)}
                    </pre>
                  </div>
                )}

                {evt.event === "DECISION" && (
                  <p className="text-slate-300">
                    <span className="text-teal-400 font-semibold">Verification Decision:</span>{" "}
                    <span
                      className={
                        evt.data?.passed ? "text-emerald-400 font-bold" : "text-red-400 font-bold"
                      }
                    >
                      {evt.data?.passed ? "PASSED" : "FAILED"}
                    </span>{" "}
                    — {evt.data?.reason}
                  </p>
                )}

                {evt.event === "SUCCESS" && (
                  <p className="text-emerald-400 font-semibold">
                    🎉 {evt.data?.message || "Execution completed."}
                  </p>
                )}

                {evt.event === "ERROR" && (
                  <p className="text-red-400 font-semibold">
                    ❌ {evt.data?.error || "Error during execution."}
                  </p>
                )}

                {evt.event === "CONNECTED" && (
                  <p className="text-slate-400 italic">{evt.data}</p>
                )}
              </div>
            ))
          )}
          <div ref={eventsEndRef} />
        </div>
      </div>
    </div>
  );
}
