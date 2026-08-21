"use client";

import { useRef, useEffect } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  CheckCircle,
  XCircle,
  Zap,
  Search,
  ListChecks,
  FileText,
  Shield,
  Trash2,
  Loader2,
} from "lucide-react";
import {
  useAgentStore,
  type Turn,
  type StreamEvent,
  type EventType,
} from "@/store/useAgentStore";

// ─── Event metadata ───────────────────────────────────────────────────────────
const EVENT_META: Record<
  EventType,
  { label: string; color: string; Icon: React.ElementType }
> = {
  CONNECTED: { label: "Connected",  color: "text-slate-400",   Icon: Zap },
  PLAN:      { label: "Plan",       color: "text-indigo-400",  Icon: ListChecks },
  TOOL_CALL: { label: "Tool",       color: "text-blue-400",    Icon: Search },
  EVIDENCE:  { label: "Evidence",   color: "text-amber-400",   Icon: FileText },
  DECISION:  { label: "Decision",   color: "text-teal-400",    Icon: Shield },
  SUCCESS:   { label: "Done",       color: "text-emerald-400", Icon: CheckCircle },
  ERROR:     { label: "Error",      color: "text-red-400",     Icon: XCircle },
};

// ─── PLAN sub-renderer ────────────────────────────────────────────────────────
function PlanContent({ data }: { data: StreamEvent["data"] }) {
  return (
    <div className="mt-2 space-y-1.5">
      {data.summary && (
        <p className="text-sm font-medium text-slate-200">{data.summary}</p>
      )}
      {Array.isArray(data.steps) && data.steps.length > 0 && (
        <ol className="mt-1 space-y-1 pl-1">
          {data.steps.map((s: { step_number: number; purpose: string; tool?: string }) => (
            <li
              key={s.step_number}
              className="flex items-baseline gap-1.5 text-xs text-slate-400"
            >
              <span className="shrink-0 font-mono text-indigo-500">
                {s.step_number}.
              </span>
              <span>{s.purpose}</span>
              {s.tool && (
                <span className="shrink-0 rounded bg-slate-800 px-1.5 py-0.5 font-mono text-[10px] text-amber-400">
                  {s.tool}
                </span>
              )}
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}

// ─── TOOL_CALL sub-renderer ───────────────────────────────────────────────────
function ToolCallContent({ data }: { data: StreamEvent["data"] }) {
  return (
    <p className="mt-1.5 text-xs text-slate-300">
      Running{" "}
      <span className="rounded bg-slate-800 px-1.5 py-0.5 font-mono text-[11px] text-blue-300">
        {data.tool ?? "unknown"}
      </span>
      {data.purpose && (
        <span className="ml-1.5 text-slate-500">— {data.purpose}</span>
      )}
    </p>
  );
}

// ─── EVIDENCE sub-renderer ────────────────────────────────────────────────────
function EvidenceContent({ data }: { data: StreamEvent["data"] }) {
  if (data.summary) {
    return <p className="mt-1.5 text-xs text-slate-300">{data.summary}</p>;
  }
  if (data.output) {
    const text =
      typeof data.output === "string"
        ? data.output
        : JSON.stringify(data.output, null, 2);
    return (
      <pre className="mt-1.5 max-h-28 overflow-y-auto rounded-lg bg-slate-950 p-2.5 font-mono text-[10px] leading-relaxed text-slate-300 whitespace-pre-wrap">
        {text}
      </pre>
    );
  }
  return (
    <p className="mt-1.5 text-xs text-slate-500 italic">No output captured.</p>
  );
}

// ─── DECISION sub-renderer ────────────────────────────────────────────────────
function DecisionContent({ data }: { data: StreamEvent["data"] }) {
  return (
    <p className="mt-1.5 text-xs text-slate-300">
      <span
        className={`mr-1.5 font-bold ${
          data.passed ? "text-emerald-400" : "text-red-400"
        }`}
      >
        {data.passed ? "Passed" : "Failed"}
      </span>
      {data.reason && (
        <span className="text-slate-500">— {data.reason}</span>
      )}
    </p>
  );
}

// ─── Single event row ─────────────────────────────────────────────────────────
function EventRow({ evt }: { evt: StreamEvent }) {
  const meta = EVENT_META[evt.event] ?? EVENT_META.CONNECTED;
  const { Icon, label, color } = meta;

  // CONNECTED events are silent — they just confirm the WS handshake
  if (evt.event === "CONNECTED") return null;

  return (
    <motion.div
      layout
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.2 }}
      className="flex gap-3 group"
    >
      {/* Timeline track */}
      <div className="flex flex-col items-center">
        <div
          className={`mt-1 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-slate-800 ${color}`}
        >
          <Icon className="h-3.5 w-3.5" />
        </div>
        <div className="mt-1 w-px flex-1 bg-slate-800/60" />
      </div>

      {/* Content card */}
      <div className="mb-3 min-w-0 flex-1 rounded-xl border border-slate-800/70 bg-slate-900/60 px-4 py-3">
        <div className="flex items-center justify-between gap-2">
          <span
            className={`text-[10px] font-bold uppercase tracking-widest ${color}`}
          >
            {label}
          </span>
          <span className="font-mono text-[10px] text-slate-600">
            {new Date(evt.timestamp * 1000).toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
              second: "2-digit",
            })}
          </span>
        </div>

        {evt.event === "PLAN" && <PlanContent data={evt.data} />}
        {evt.event === "TOOL_CALL" && <ToolCallContent data={evt.data} />}
        {evt.event === "EVIDENCE" && <EvidenceContent data={evt.data} />}
        {evt.event === "DECISION" && <DecisionContent data={evt.data} />}

        {evt.event === "ERROR" && evt.data.error && (
          <p className="mt-1.5 text-xs text-red-400">{evt.data.error}</p>
        )}
      </div>
    </motion.div>
  );
}

// ─── A single conversation turn card ──────────────────────────────────────────
function TurnCard({ turn }: { turn: Turn }) {
  const isRunning = turn.status === "running";

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className="space-y-3"
      id={`turn-${turn.id}`}
    >
      {/* ── User command bubble ──────────────────────────────────────────── */}
      <div className="flex justify-end">
        <div className="max-w-[80%] rounded-2xl rounded-tr-sm border border-indigo-500/30 bg-indigo-600/20 px-4 py-2.5">
          <p className="text-sm font-medium text-slate-100">{turn.command}</p>
          <p className="mt-0.5 text-right text-[10px] text-indigo-400/70">
            {new Date(turn.startedAt).toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </p>
        </div>
      </div>

      {/* ── Event timeline ───────────────────────────────────────────────── */}
      <div className="pl-2">
        <AnimatePresence initial={false}>
          {turn.events.map((evt) => (
            <EventRow key={evt.id} evt={evt} />
          ))}
        </AnimatePresence>

        {/* Typing / in-progress indicator */}
        {isRunning && (
          <motion.div
            className="flex items-center gap-2 pl-9 text-xs text-slate-500"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
          >
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
            <span>Agent working…</span>
          </motion.div>
        )}
      </div>

      {/* ── Final response bubble (SUCCESS) ──────────────────────────────── */}
      <AnimatePresence>
        {turn.status === "success" && turn.response && (
          <motion.div
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
            className="flex gap-3"
          >
            <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-indigo-600 text-xs font-bold text-white">
              N
            </div>
            <div
              id={`response-${turn.id}`}
              className="max-w-[85%] rounded-2xl rounded-tl-sm border border-slate-700/60 bg-slate-800/70 px-4 py-3"
            >
              <p className="text-sm leading-relaxed text-slate-200">
                {turn.response}
              </p>
            </div>
          </motion.div>
        )}

        {/* Error final state */}
        {turn.status === "error" && turn.error && (
          <motion.div
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex gap-3"
          >
            <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-red-900/50 text-red-400">
              <XCircle className="h-4 w-4" />
            </div>
            <div className="max-w-[85%] rounded-2xl rounded-tl-sm border border-red-500/20 bg-red-950/30 px-4 py-3">
              <p className="text-sm text-red-400">{turn.error}</p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Separator */}
      <div className="h-px bg-slate-800/50" />
    </motion.div>
  );
}

// ─── Main TaskTimeline component ──────────────────────────────────────────────
export default function TaskTimeline() {
  const { turns, isStreaming, clearHistory } = useAgentStore();
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll on new events
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [turns]);

  return (
    <div
      id="task-timeline"
      className="flex w-full max-w-3xl flex-col rounded-2xl border border-slate-800 bg-slate-950/80 shadow-2xl backdrop-blur-xl"
    >
      {/* ── Header ───────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between border-b border-slate-800/70 px-5 py-3.5">
        <div className="flex items-center gap-2.5">
          <div
            className={`h-2 w-2 rounded-full transition-colors duration-500 ${
              isStreaming ? "animate-pulse bg-indigo-500" : "bg-slate-700"
            }`}
          />
          <h2 className="text-sm font-semibold text-slate-200">
            Task Timeline
          </h2>
          {turns.length > 0 && (
            <span className="rounded-full bg-slate-800 px-2 py-0.5 text-[10px] font-medium text-slate-400">
              {turns.length}
            </span>
          )}
        </div>

        {turns.length > 0 && (
          <button
            id="clear-timeline-button"
            onClick={clearHistory}
            aria-label="Clear timeline"
            className="flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs text-slate-600 transition-colors hover:bg-slate-800 hover:text-slate-400"
          >
            <Trash2 className="h-3.5 w-3.5" />
            Clear
          </button>
        )}
      </div>

      {/* ── Timeline scroll area ─────────────────────────────────────────── */}
      <div className="min-h-[320px] max-h-[620px] flex-1 space-y-2 overflow-y-auto px-5 py-5">
        {turns.length === 0 ? (
          <div className="flex h-full min-h-[280px] flex-col items-center justify-center gap-3 text-center">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-slate-800/60 text-slate-600">
              <Zap className="h-6 w-6" />
            </div>
            <div>
              <p className="text-sm font-medium text-slate-500">
                No activity yet
              </p>
              <p className="mt-1 text-xs text-slate-700">
                Use the voice bar or type a command to get started
              </p>
            </div>
          </div>
        ) : (
          <AnimatePresence initial={false}>
            {turns.map((turn) => (
              <TurnCard key={turn.id} turn={turn} />
            ))}
          </AnimatePresence>
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
