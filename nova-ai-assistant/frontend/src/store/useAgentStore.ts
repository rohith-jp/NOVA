import { create } from "zustand";

// ─── Event types emitted by the backend ───────────────────────────────────────
export type EventType =
  | "CONNECTED"
  | "PLAN"
  | "TOOL_CALL"
  | "EVIDENCE"
  | "DECISION"
  | "SUCCESS"
  | "ERROR";

export interface StreamEvent {
  id: string;
  event: EventType;
  timestamp: number;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any -- dynamic WS JSON
  data: Record<string, any>;
}

// ─── A single "Turn" = one user command + its downstream events ───────────────
export interface Turn {
  id: string;
  command: string;
  startedAt: number;
  status: "running" | "success" | "error" | "idle";
  /** Final response text from SUCCESS event, if any */
  response: string | null;
  /** Error message from ERROR event, if any */
  error: string | null;
  events: StreamEvent[];
}

// ─── Store shape ──────────────────────────────────────────────────────────────
interface AgentStore {
  turns: Turn[];
  activeTurnId: string | null;
  isStreaming: boolean;

  /** Start a new turn and open a WebSocket session */
  startTurn: (command: string, wsUrl?: string) => void;
  /** Manually disconnect */
  stopStream: () => void;
  /** Clear all history */
  clearHistory: () => void;
}

// ─── Internal WebSocket ref (outside Zustand to avoid serialisation) ──────────
let _ws: WebSocket | null = null;

const WS_URL =
  process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000/ws/stream";

// ─── Helpers ──────────────────────────────────────────────────────────────────
const makeId = () => Math.random().toString(36).slice(2, 9);

export const useAgentStore = create<AgentStore>((set, get) => ({
  turns: [],
  activeTurnId: null,
  isStreaming: false,

  startTurn: (command: string, wsUrl = WS_URL) => {
    // Close any existing connection
    _ws?.close();

    const turnId = makeId();
    const newTurn: Turn = {
      id: turnId,
      command,
      startedAt: Date.now(),
      status: "running",
      response: null,
      error: null,
      events: [],
    };

    set((s) => ({
      turns: [...s.turns, newTurn],
      activeTurnId: turnId,
      isStreaming: true,
    }));

    _ws = new WebSocket(wsUrl);

    _ws.onopen = () => {
      _ws?.send(JSON.stringify({ command }));
    };

    _ws.onmessage = (msgEvent) => {
      let payload: Record<string, unknown>;
      try {
        payload = JSON.parse(msgEvent.data);
      } catch {
        return;
      }

      const evtType = (payload.event as EventType) ?? "CONNECTED";

      // ── Strip chain-of-thought from PLAN events ───────────────────────────
      // We intentionally omit raw reasoning / internal_notes fields.
      let safeData = payload.data as Record<string, unknown> | undefined;
      if (evtType === "PLAN" && safeData) {
        // Keep only the public-facing summary and steps (purpose + tool only)
        safeData = {
          summary: safeData.summary,
          steps: Array.isArray(safeData.steps)
            ? (safeData.steps as Array<Record<string, unknown>>).map((s) => ({
                step_number: s.step_number,
                purpose: s.purpose,
                tool: s.tool,
              }))
            : [],
        };
      }

      const streamEvent: StreamEvent = {
        id: makeId(),
        event: evtType,
        timestamp:
          typeof payload.timestamp === "number"
            ? payload.timestamp
            : Date.now() / 1000,
        data: (safeData ?? payload.message ?? {}) as Record<string, unknown>,
      };

      set((s) => ({
        turns: s.turns.map((t) =>
          t.id === turnId
            ? { ...t, events: [...t.events, streamEvent] }
            : t
        ),
      }));

      if (evtType === "SUCCESS") {
        const msg =
          typeof (payload.data as Record<string, unknown>)?.message === "string"
            ? ((payload.data as Record<string, unknown>).message as string)
            : "Completed.";
        set((s) => ({
          isStreaming: false,
          turns: s.turns.map((t) =>
            t.id === turnId ? { ...t, status: "success", response: msg } : t
          ),
        }));
        _ws?.close();
      } else if (evtType === "ERROR") {
        const errMsg =
          typeof (payload.data as Record<string, unknown>)?.error === "string"
            ? ((payload.data as Record<string, unknown>).error as string)
            : "An error occurred.";
        set((s) => ({
          isStreaming: false,
          turns: s.turns.map((t) =>
            t.id === turnId ? { ...t, status: "error", error: errMsg } : t
          ),
        }));
        _ws?.close();
      }
    };

    _ws.onerror = () => {
      set((s) => ({
        isStreaming: false,
        turns: s.turns.map((t) =>
          t.id === turnId
            ? { ...t, status: "error", error: "WebSocket connection failed." }
            : t
        ),
      }));
    };

    _ws.onclose = () => {
      const { turns } = get();
      const turn = turns.find((t) => t.id === turnId);
      // Mark running turns as errored if WS closed unexpectedly
      if (turn?.status === "running") {
        set((s) => ({
          isStreaming: false,
          turns: s.turns.map((t) =>
            t.id === turnId
              ? { ...t, status: "error", error: "Connection closed unexpectedly." }
              : t
          ),
        }));
      } else {
        set({ isStreaming: false });
      }
    };
  },

  stopStream: () => {
    _ws?.close();
    set({ isStreaming: false });
  },

  clearHistory: () => {
    _ws?.close();
    set({ turns: [], activeTurnId: null, isStreaming: false });
  },
}));
