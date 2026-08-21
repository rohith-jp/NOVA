"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Mic, MicOff, Send, X } from "lucide-react";

// ─── Types ────────────────────────────────────────────────────────────────────
type RecordingState = "idle" | "recording" | "processing" | "done" | "error";

interface VoiceCommandBarProps {
  /** Called with the final command string (transcribed or typed). */
  onCommand?: (text: string) => void;
  /** Backend base URL — defaults to NEXT_PUBLIC_API_URL or localhost:8000 */
  apiBase?: string;
}

// ─── Constants ────────────────────────────────────────────────────────────────
const BAR_COUNT = 28;
const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ─── Component ────────────────────────────────────────────────────────────────
export default function VoiceCommandBar({
  onCommand,
  apiBase = API_BASE,
}: VoiceCommandBarProps) {
  const [recordingState, setRecordingState] = useState<RecordingState>("idle");
  const [transcript, setTranscript] = useState("");
  const [typedInput, setTypedInput] = useState("");
  const [barHeights, setBarHeights] = useState<number[]>(
    Array(BAR_COUNT).fill(4)
  );
  const [error, setError] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const animFrameRef = useRef<number | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

  // ── Waveform animation loop ─────────────────────────────────────────────────
  const animateWaveform = useCallback(() => {
    if (!analyserRef.current) return;
    const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount);
    analyserRef.current.getByteFrequencyData(dataArray);

    const step = Math.floor(dataArray.length / BAR_COUNT);
    const heights = Array.from({ length: BAR_COUNT }, (_, i) => {
      const val = dataArray[i * step] ?? 0;
      // Map 0–255 → 4–48px with a gentle curve
      return 4 + Math.pow(val / 255, 0.6) * 44;
    });
    setBarHeights(heights);
    animFrameRef.current = requestAnimationFrame(animateWaveform);
  }, []);

  // ── Start recording ─────────────────────────────────────────────────────────
  const startRecording = useCallback(async () => {
    setError(null);
    setTranscript("");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      // Hook up analyser for the waveform visualisation
      const audioCtx = new AudioContext();
      const source = audioCtx.createMediaStreamSource(stream);
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 256;
      source.connect(analyser);
      analyserRef.current = analyser;

      chunksRef.current = [];
      const mimeType = MediaRecorder.isTypeSupported("audio/webm")
        ? "audio/webm"
        : "audio/ogg";
      const recorder = new MediaRecorder(stream, { mimeType });

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      recorder.onstop = async () => {
        setRecordingState("processing");
        stopWaveform();

        const blob = new Blob(chunksRef.current, { type: mimeType });
        const ext = mimeType.includes("webm") ? "webm" : "ogg";
        const formData = new FormData();
        formData.append("audio", blob, `recording.${ext}`);

        try {
          const res = await fetch(`${apiBase}/api/voice/transcribe`, {
            method: "POST",
            body: formData,
          });

          if (!res.ok) {
            const detail = await res.json().catch(() => ({}));
            throw new Error(detail?.detail ?? `HTTP ${res.status}`);
          }

          const data: { text: string } = await res.json();
          setTranscript(data.text);
          setRecordingState("done");
          onCommand?.(data.text);
        } catch (err) {
          setError(err instanceof Error ? err.message : "Transcription failed");
          setRecordingState("error");
        }
      };

      recorder.start(200); // collect in 200 ms chunks
      mediaRecorderRef.current = recorder;
      setRecordingState("recording");
      animFrameRef.current = requestAnimationFrame(animateWaveform);
    } catch {
      setError("Microphone access denied or unavailable.");
      setRecordingState("error");
    }
  }, [apiBase, animateWaveform, onCommand]);

  // ── Stop waveform animation ─────────────────────────────────────────────────
  const stopWaveform = () => {
    if (animFrameRef.current !== null) {
      cancelAnimationFrame(animFrameRef.current);
      animFrameRef.current = null;
    }
    setBarHeights(Array(BAR_COUNT).fill(4));
    analyserRef.current = null;
  };

  // ── Stop recording ──────────────────────────────────────────────────────────
  const stopRecording = useCallback(() => {
    mediaRecorderRef.current?.stop();
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
  }, []);

  // ── Reset ───────────────────────────────────────────────────────────────────
  const reset = useCallback(() => {
    stopWaveform();
    setRecordingState("idle");
    setTranscript("");
    setTypedInput("");
    setError(null);
  }, []);

  // ── Submit typed command ────────────────────────────────────────────────────
  const submitTyped = useCallback(() => {
    const text = typedInput.trim();
    if (!text) return;
    setTranscript(text);
    setRecordingState("done");
    onCommand?.(text);
    setTypedInput("");
  }, [typedInput, onCommand]);

  // ── Cleanup on unmount ──────────────────────────────────────────────────────
  useEffect(() => {
    return () => {
      stopWaveform();
      streamRef.current?.getTracks().forEach((t) => t.stop());
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const isRecording = recordingState === "recording";
  const isProcessing = recordingState === "processing";

  return (
    <div className="w-full max-w-2xl mx-auto" id="voice-command-bar">
      {/* ── Main pill container ─────────────────────────────────────────────── */}
      <motion.div
        layout
        className={[
          "relative flex flex-col gap-3 rounded-2xl border px-5 py-4",
          "bg-slate-900/90 backdrop-blur-xl shadow-2xl",
          isRecording
            ? "border-indigo-500/70 shadow-indigo-500/20"
            : "border-slate-700/60",
          "transition-[border-color,box-shadow] duration-300",
        ].join(" ")}
      >
        {/* ── Top row: mic button + waveform / status ─────────────────────── */}
        <div className="flex items-center gap-4">
          {/* Mic button */}
          <motion.button
            id="mic-toggle-button"
            aria-label={isRecording ? "Stop recording" : "Start recording"}
            whileTap={{ scale: 0.90 }}
            onClick={isRecording ? stopRecording : startRecording}
            disabled={isProcessing}
            className={[
              "relative flex h-12 w-12 shrink-0 items-center justify-center",
              "rounded-full border-2 transition-all duration-300 focus:outline-none",
              "focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900",
              isRecording
                ? "border-red-500 bg-red-500/15 text-red-400 hover:bg-red-500/25"
                : isProcessing
                ? "cursor-not-allowed border-slate-600 bg-slate-800 text-slate-500"
                : "border-indigo-500/70 bg-indigo-600/15 text-indigo-400 hover:bg-indigo-600/25",
            ].join(" ")}
          >
            {/* Pulse ring while recording */}
            {isRecording && (
              <motion.span
                className="absolute inset-0 rounded-full border-2 border-red-500"
                initial={{ opacity: 0.8, scale: 1 }}
                animate={{ opacity: 0, scale: 1.7 }}
                transition={{ duration: 1.2, repeat: Infinity, ease: "easeOut" }}
              />
            )}
            {isProcessing ? (
              <motion.div
                className="h-5 w-5 rounded-full border-2 border-slate-500 border-t-indigo-400"
                animate={{ rotate: 360 }}
                transition={{ duration: 0.9, repeat: Infinity, ease: "linear" }}
              />
            ) : isRecording ? (
              <MicOff className="h-5 w-5" />
            ) : (
              <Mic className="h-5 w-5" />
            )}
          </motion.button>

          {/* Waveform / status area */}
          <div className="flex flex-1 items-center overflow-hidden">
            <AnimatePresence mode="wait">
              {isRecording ? (
                /* Live waveform bars */
                <motion.div
                  key="waveform"
                  className="flex h-12 w-full items-center gap-[3px]"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.25 }}
                  id="waveform-visualizer"
                >
                  {barHeights.map((h, i) => (
                    <motion.span
                      key={i}
                      className="flex-1 rounded-full bg-indigo-400"
                      animate={{ height: h }}
                      transition={{ duration: 0.07, ease: "linear" }}
                      style={{ minWidth: 2 }}
                    />
                  ))}
                </motion.div>
              ) : isProcessing ? (
                <motion.p
                  key="processing"
                  className="text-sm font-medium text-slate-400"
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -4 }}
                >
                  Transcribing…
                </motion.p>
              ) : recordingState === "done" && transcript ? (
                <motion.p
                  key="transcript"
                  id="transcription-result"
                  className="truncate text-sm font-medium text-white"
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -4 }}
                >
                  {transcript}
                </motion.p>
              ) : recordingState === "error" ? (
                <motion.p
                  key="error"
                  id="error-message"
                  className="truncate text-sm font-medium text-red-400"
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -4 }}
                >
                  {error}
                </motion.p>
              ) : (
                <motion.p
                  key="idle"
                  className="text-sm text-slate-500"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                >
                  Press the mic or type a command below
                </motion.p>
              )}
            </AnimatePresence>
          </div>

          {/* Reset / dismiss button */}
          <AnimatePresence>
            {(recordingState === "done" || recordingState === "error") && (
              <motion.button
                id="reset-voice-button"
                aria-label="Clear"
                initial={{ opacity: 0, scale: 0.7 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.7 }}
                transition={{ duration: 0.2 }}
                onClick={reset}
                className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full
                           text-slate-500 hover:bg-slate-700/60 hover:text-slate-300
                           transition-colors duration-150 focus:outline-none"
              >
                <X className="h-4 w-4" />
              </motion.button>
            )}
          </AnimatePresence>
        </div>

        {/* ── Divider ─────────────────────────────────────────────────────── */}
        <div className="h-px bg-slate-700/50" />

        {/* ── Typed fallback input ─────────────────────────────────────────── */}
        <div className="flex items-center gap-3">
          <input
            ref={inputRef}
            id="typed-command-input"
            type="text"
            placeholder="…or type a command"
            value={typedInput}
            onChange={(e) => setTypedInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && submitTyped()}
            className={[
              "flex-1 bg-transparent text-sm text-slate-200 placeholder:text-slate-600",
              "focus:outline-none",
            ].join(" ")}
          />
          <AnimatePresence>
            {typedInput.trim().length > 0 && (
              <motion.button
                id="submit-typed-command"
                aria-label="Send typed command"
                initial={{ opacity: 0, scale: 0.7 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.7 }}
                transition={{ duration: 0.15 }}
                whileTap={{ scale: 0.88 }}
                onClick={submitTyped}
                className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full
                           bg-indigo-600 text-white shadow-md hover:bg-indigo-500
                           transition-colors duration-150 focus:outline-none"
              >
                <Send className="h-4 w-4" />
              </motion.button>
            )}
          </AnimatePresence>
        </div>

        {/* ── Recording label ──────────────────────────────────────────────── */}
        <AnimatePresence>
          {isRecording && (
            <motion.div
              className="flex items-center gap-1.5 self-start"
              initial={{ opacity: 0, y: -4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -4 }}
            >
              <span className="h-2 w-2 animate-pulse rounded-full bg-red-500" />
              <span className="text-xs font-semibold uppercase tracking-widest text-red-400">
                Recording
              </span>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </div>
  );
}
