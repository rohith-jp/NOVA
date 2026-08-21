"use client";

import { useEffect, useRef, useState, useCallback, useMemo } from "react";
import * as d3 from "d3";
import { AnimatePresence, motion } from "framer-motion";
import {
  Brain,
  Search,
  Plus,
  Clock,
  Tag,
  Sparkles,
  RefreshCw,
  Eye,
  EyeOff,
  SlidersHorizontal,
  LayoutGrid,
  GitCommit,
  X,
  Database,
  Lock,
} from "lucide-react";
import { useAuthStore } from "@/store/useAuthStore";

// ─── Types ────────────────────────────────────────────────────────────────────
export interface MemoryItem {
  id: string;
  content: string;
  metadata: {
    memory_type?: string;
    source?: string;
    [key: string]: any;
  };
  created_at?: string;
  user_id?: string;
  embedding?: number[];
}

interface D3Node extends d3.SimulationNodeDatum {
  id: string;
  content: string;
  category: string;
  source: string;
  dateStr: string;
  timestamp: number;
  val: number;
}

interface D3Link extends d3.SimulationLinkDatum<D3Node> {
  source: string | D3Node;
  target: string | D3Node;
  value: number;
}

// ─── Category Configuration ───────────────────────────────────────────────────
const CATEGORY_COLORS: Record<string, { fill: string; border: string; bg: string; text: string }> = {
  preference: { fill: "#818cf8", border: "#6366f1", bg: "bg-indigo-500/10", text: "text-indigo-400" },
  fact:       { fill: "#38bdf8", border: "#0284c7", bg: "bg-sky-500/10",    text: "text-sky-400" },
  task:       { fill: "#34d399", border: "#059669", bg: "bg-emerald-500/10",text: "text-emerald-400" },
  general:    { fill: "#fbbf24", border: "#d97706", bg: "bg-amber-500/10",  text: "text-amber-400" },
};

const DEFAULT_COLOR = { fill: "#a7f3d0", border: "#10b981", bg: "bg-slate-500/10", text: "text-slate-400" };

function getCategoryStyle(cat: string) {
  const key = (cat || "general").toLowerCase();
  return CATEGORY_COLORS[key] || DEFAULT_COLOR;
}

// Demo fallback data if API returns empty array
const DEMO_MEMORIES: MemoryItem[] = [
  {
    id: "mem-1",
    content: "User prefers concise Python code over verbose solutions.",
    metadata: { memory_type: "preference", source: "chat" },
    created_at: new Date(Date.now() - 3600000 * 24 * 3).toISOString(),
  },
  {
    id: "mem-2",
    content: "Deployed production database to Supabase pgvector.",
    metadata: { memory_type: "task", source: "system" },
    created_at: new Date(Date.now() - 3600000 * 24 * 2).toISOString(),
  },
  {
    id: "mem-3",
    content: "NOVA AI architecture uses AES-256-GCM for encrypted storage.",
    metadata: { memory_type: "fact", source: "audit" },
    created_at: new Date(Date.now() - 3600000 * 24 * 1).toISOString(),
  },
  {
    id: "mem-4",
    content: "User requested modern dark-mode aesthetic with Framer Motion.",
    metadata: { memory_type: "preference", source: "ui_feedback" },
    created_at: new Date(Date.now() - 3600000 * 12).toISOString(),
  },
  {
    id: "mem-5",
    content: "Voice pipeline integrated with OpenAI Whisper and ElevenLabs.",
    metadata: { memory_type: "task", source: "feature_flag" },
    created_at: new Date(Date.now() - 3600000 * 4).toISOString(),
  },
];

export default function MemoryConstellation() {
  const { session } = useAuthStore();
  const [memories, setMemories] = useState<MemoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  const [selectedMemory, setSelectedMemory] = useState<MemoryItem | null>(null);
  const [viewMode, setViewMode] = useState<"constellation" | "timeline">("constellation");
  const [isAddOpen, setIsAddOpen] = useState(false);

  // New Memory Form State
  const [newContent, setNewContent] = useState("");
  const [newType, setNewType] = useState("preference");
  const [storing, setStoring] = useState(false);

  const svgRef = useRef<SVGSVGElement>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(700);

  const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  // ── 1. Fetch Memories from API ──────────────────────────────────────────────
  const fetchMemories = useCallback(async () => {
    setLoading(true);
    try {
      const headers: Record<string, string> = {};
      if (session?.access_token) {
        headers["Authorization"] = `Bearer ${session.access_token}`;
      }

      const res = await fetch(`${API_BASE}/api/memory/`, { headers });
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data) && data.length > 0) {
          setMemories(data);
        } else {
          setMemories(DEMO_MEMORIES);
        }
      } else {
        setMemories(DEMO_MEMORIES);
      }
    } catch {
      setMemories(DEMO_MEMORIES);
    } finally {
      setLoading(false);
    }
  }, [session, API_BASE]);

  useEffect(() => {
    fetchMemories();
  }, [fetchMemories]);

  // ── 2. Create Memory Submission ─────────────────────────────────────────────
  const handleCreateMemory = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newContent.trim()) return;

    setStoring(true);
    try {
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (session?.access_token) {
        headers["Authorization"] = `Bearer ${session.access_token}`;
      }

      const res = await fetch(`${API_BASE}/api/memory/store`, {
        method: "POST",
        headers,
        body: JSON.stringify({
          content: newContent.trim(),
          memory_type: newType,
          source: "user_ui",
        }),
      });

      if (res.ok) {
        setNewContent("");
        setIsAddOpen(false);
        await fetchMemories();
      } else {
        // Fallback local insert if offline/mock
        const localItem: MemoryItem = {
          id: `mem-local-${Date.now()}`,
          content: newContent.trim(),
          metadata: { memory_type: newType, source: "user_ui" },
          created_at: new Date().toISOString(),
        };
        setMemories((prev) => [localItem, ...prev]);
        setNewContent("");
        setIsAddOpen(false);
      }
    } catch {
      const localItem: MemoryItem = {
        id: `mem-local-${Date.now()}`,
        content: newContent.trim(),
        metadata: { memory_type: newType, source: "user_ui" },
        created_at: new Date().toISOString(),
      };
      setMemories((prev) => [localItem, ...prev]);
      setNewContent("");
      setIsAddOpen(false);
    } finally {
      setStoring(false);
    }
  };

  // ── Filtered Memories ───────────────────────────────────────────────────────
  const filteredMemories = useMemo(() => {
    return memories.filter((m) => {
      const cat = m.metadata?.memory_type || "general";
      const matchesCat = selectedCategory === "all" || cat.toLowerCase() === selectedCategory.toLowerCase();
      const matchesSearch =
        !searchQuery ||
        m.content.toLowerCase().includes(searchQuery.toLowerCase()) ||
        cat.toLowerCase().includes(searchQuery.toLowerCase());
      return matchesCat && matchesSearch;
    });
  }, [memories, selectedCategory, searchQuery]);

  // ── Responsive Resize Observer ──────────────────────────────────────────────
  useEffect(() => {
    const el = wrapperRef.current;
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      const w = entries[0]?.contentRect.width;
      if (w && w > 0) setWidth(w);
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // ── 3. Render D3 Force-Directed Constellation ───────────────────────────────
  const renderConstellation = useCallback(() => {
    if (!svgRef.current || viewMode !== "constellation") return;

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    const height = 360;
    svg.attr("viewBox", `0 0 ${width} ${height}`);

    if (filteredMemories.length === 0) return;

    // Build Nodes
    const nodes: D3Node[] = filteredMemories.map((m) => ({
      id: m.id,
      content: m.content,
      category: m.metadata?.memory_type || "general",
      source: m.metadata?.source || "unknown",
      dateStr: m.created_at ? new Date(m.created_at).toLocaleDateString() : "recent",
      timestamp: m.created_at ? new Date(m.created_at).getTime() : Date.now(),
      val: 16,
    }));

    // Build Links (connect nodes in the same category)
    const links: D3Link[] = [];
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        if (nodes[i].category === nodes[j].category) {
          links.push({
            source: nodes[i].id,
            target: nodes[j].id,
            value: 1,
          });
        }
      }
    }

    // Force Simulation
    const simulation = d3
      .forceSimulation<D3Node>(nodes)
      .force(
        "link",
        d3
          .forceLink<D3Node, D3Link>(links)
          .id((d) => d.id)
          .distance(75)
      )
      .force("charge", d3.forceManyBody().strength(-140))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collide", d3.forceCollide().radius(28));

    // Container Group
    const g = svg.append("g");

    // Render Links
    const link = g
      .append("g")
      .attr("stroke-opacity", 0.3)
      .selectAll("line")
      .data(links)
      .join("line")
      .attr("stroke", (d) => {
        const sourceNode = typeof d.source === "object" ? (d.source as D3Node) : nodes.find((n) => n.id === d.source);
        return getCategoryStyle(sourceNode?.category || "general").fill;
      })
      .attr("stroke-width", 1.5)
      .attr("stroke-dasharray", "4,3");

    // Render Node Groups
    const node = g
      .append("g")
      .selectAll<SVGGElement, D3Node>("g")
      .data(nodes)
      .join("g")
      .style("cursor", "pointer")
      .on("click", (_evt, d) => {
        const mem = memories.find((m) => m.id === d.id);
        if (mem) setSelectedMemory(mem);
      });

    // Outer Halo Circle
    node
      .append("circle")
      .attr("r", 20)
      .attr("fill", (d) => getCategoryStyle(d.category).fill)
      .attr("fill-opacity", 0.15)
      .attr("stroke", (d) => getCategoryStyle(d.category).border)
      .attr("stroke-width", 1.5);

    // Inner Core Circle
    node
      .append("circle")
      .attr("r", 7)
      .attr("fill", (d) => getCategoryStyle(d.category).fill);

    // Label Text
    node
      .append("text")
      .text((d) => (d.content.length > 20 ? d.content.slice(0, 20) + "…" : d.content))
      .attr("x", 24)
      .attr("y", 4)
      .attr("font-size", "11px")
      .attr("fill", "#e2e8f0")
      .attr("font-weight", "500");

    // Category Tag Text
    node
      .append("text")
      .text((d) => d.category.toUpperCase())
      .attr("x", 24)
      .attr("y", 18)
      .attr("font-size", "9px")
      .attr("fill", (d) => getCategoryStyle(d.category).fill)
      .attr("font-weight", "700")
      .attr("letter-spacing", "0.05em");

    // Drag behavior
    node.call(
      d3
        .drag<SVGGElement, D3Node>()
        .on("start", (event, d) => {
          if (!event.active) simulation.alphaTarget(0.3).restart();
          d.fx = d.x;
          d.fy = d.y;
        })
        .on("drag", (event, d) => {
          d.fx = event.x;
          d.fy = event.y;
        })
        .on("end", (event, d) => {
          if (!event.active) simulation.alphaTarget(0);
          d.fx = null;
          d.fy = null;
        })
    );

    // Simulation Tick
    simulation.on("tick", () => {
      link
        .attr("x1", (d) => (d.source as D3Node).x!)
        .attr("y1", (d) => (d.source as D3Node).y!)
        .attr("x2", (d) => (d.target as D3Node).x!)
        .attr("y2", (d) => (d.target as D3Node).y!);

      node.attr("transform", (d) => {
        // Constrain to bounds
        const r = 24;
        d.x = Math.max(r, Math.min(width - r, d.x!));
        d.y = Math.max(r, Math.min(height - r, d.y!));
        return `translate(${d.x},${d.y})`;
      });
    });

    return () => {
      simulation.stop();
    };
  }, [filteredMemories, viewMode, width, memories]);

  useEffect(() => {
    renderConstellation();
  }, [renderConstellation]);

  return (
    <div
      ref={wrapperRef}
      id="memory-constellation-panel"
      className="w-full max-w-3xl rounded-2xl border border-slate-800 bg-slate-950/80 shadow-2xl backdrop-blur-xl overflow-hidden"
    >
      {/* ── 1. Top Header ───────────────────────────────────────────────────── */}
      <div className="flex flex-col gap-3 border-b border-slate-800/70 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600/20 text-indigo-400 border border-indigo-500/30">
            <Brain className="h-4 w-4" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-slate-100 flex items-center gap-2">
              Memory Constellation
              <span className="rounded-full bg-indigo-500/10 border border-indigo-500/20 px-2 py-0.5 text-[10px] font-semibold text-indigo-400">
                AES-256-GCM Encrypted
              </span>
            </h2>
            <p className="text-xs text-slate-400">
              Vector space graph of long-term NOVA memories
            </p>
          </div>
        </div>

        {/* Controls: Add Memory, View Toggle, Refresh */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsAddOpen(!isAddOpen)}
            className="flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-indigo-500 transition-colors"
          >
            <Plus className="h-3.5 w-3.5" />
            Add Memory
          </button>

          <div className="flex rounded-lg border border-slate-800 bg-slate-900 p-0.5">
            <button
              onClick={() => setViewMode("constellation")}
              className={`flex items-center gap-1 rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
                viewMode === "constellation" ? "bg-indigo-600 text-white" : "text-slate-400 hover:text-slate-200"
              }`}
            >
              <GitCommit className="h-3.5 w-3.5" />
              Constellation
            </button>
            <button
              onClick={() => setViewMode("timeline")}
              className={`flex items-center gap-1 rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
                viewMode === "timeline" ? "bg-indigo-600 text-white" : "text-slate-400 hover:text-slate-200"
              }`}
            >
              <Clock className="h-3.5 w-3.5" />
              Timeline
            </button>
          </div>

          <button
            onClick={fetchMemories}
            disabled={loading}
            className="flex h-8 w-8 items-center justify-center rounded-lg border border-slate-800 bg-slate-900 text-slate-400 hover:bg-slate-800 hover:text-slate-200 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      {/* ── 2. Add Memory Form (Expandable) ──────────────────────────────────── */}
      <AnimatePresence>
        {isAddOpen && (
          <motion.form
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            onSubmit={handleCreateMemory}
            className="border-b border-slate-800/70 bg-slate-900/60 px-5 py-4 space-y-3"
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-indigo-400 uppercase tracking-wider flex items-center gap-1.5">
                <Lock className="h-3 w-3" /> Encrypted Memory Entry
              </span>
              <button
                type="button"
                onClick={() => setIsAddOpen(false)}
                className="text-slate-500 hover:text-slate-300"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="flex flex-col sm:flex-row gap-3">
              <input
                type="text"
                value={newContent}
                onChange={(e) => setNewContent(e.target.value)}
                placeholder="Enter memory content to encrypt and vectorize…"
                className="flex-1 rounded-lg border border-slate-800 bg-slate-950 px-3.5 py-2 text-xs text-white placeholder-slate-500 focus:border-indigo-500 focus:outline-none"
              />
              <select
                value={newType}
                onChange={(e) => setNewType(e.target.value)}
                className="rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-slate-300 focus:border-indigo-500 focus:outline-none"
              >
                <option value="preference">Preference</option>
                <option value="fact">Fact</option>
                <option value="task">Task</option>
                <option value="general">General</option>
              </select>
              <button
                type="submit"
                disabled={storing || !newContent.trim()}
                className="rounded-lg bg-indigo-600 px-4 py-2 text-xs font-semibold text-white hover:bg-indigo-500 disabled:opacity-50"
              >
                {storing ? "Encrypting…" : "Save Memory"}
              </button>
            </div>
          </motion.form>
        )}
      </AnimatePresence>

      {/* ── 3. Filters & Search Bar ──────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row gap-3 border-b border-slate-800/70 px-5 py-3 bg-slate-950/40">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-slate-500" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search memory vector space…"
            className="w-full rounded-lg border border-slate-800 bg-slate-900/80 pl-9 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:border-indigo-500 focus:outline-none"
          />
        </div>

        {/* Category Pills */}
        <div className="flex items-center gap-1.5 overflow-x-auto">
          {["all", "preference", "fact", "task", "general"].map((cat) => {
            const isSelected = selectedCategory === cat;
            const style = getCategoryStyle(cat);
            return (
              <button
                key={cat}
                onClick={() => setSelectedCategory(cat)}
                className={`rounded-full px-3 py-1 text-[10px] font-bold uppercase tracking-wider transition-all border ${
                  isSelected
                    ? "border-indigo-500/50 bg-indigo-500/20 text-indigo-300"
                    : "border-slate-800 bg-slate-900/60 text-slate-400 hover:border-slate-700"
                }`}
              >
                {cat}
              </button>
            );
          })}
        </div>
      </div>

      {/* ── 4. Main View (Constellation vs Timeline) ─────────────────────────── */}
      <div className="relative min-h-[360px] bg-slate-950/50">
        {loading ? (
          <div className="flex min-h-[360px] items-center justify-center text-xs text-slate-500 gap-2">
            <RefreshCw className="h-4 w-4 animate-spin text-indigo-400" />
            Loading vector memories…
          </div>
        ) : filteredMemories.length === 0 ? (
          <div className="flex min-h-[360px] flex-col items-center justify-center text-center p-6 text-slate-500">
            <Database className="h-8 w-8 mb-2 text-slate-600" />
            <p className="text-sm font-medium text-slate-400">No memories found</p>
            <p className="text-xs text-slate-600 mt-1">
              Try adjusting your search filter or click "Add Memory" to store new information.
            </p>
          </div>
        ) : viewMode === "constellation" ? (
          /* D3 Constellation View */
          <div className="relative">
            <svg ref={svgRef} className="w-full h-[360px]" />

            {/* Overlay hint */}
            <div className="absolute bottom-3 left-4 text-[10px] text-slate-500 pointer-events-none">
              • Drag nodes to explore • Click node to decrypt view
            </div>
          </div>
        ) : (
          /* Timeline View */
          <div className="p-5 space-y-3 max-h-[360px] overflow-y-auto">
            {filteredMemories.map((m) => {
              const cat = m.metadata?.memory_type || "general";
              const style = getCategoryStyle(cat);
              return (
                <div
                  key={m.id}
                  onClick={() => setSelectedMemory(m)}
                  className="flex items-start justify-between rounded-xl border border-slate-800/80 bg-slate-900/60 p-3.5 hover:border-indigo-500/40 transition-all cursor-pointer group"
                >
                  <div className="space-y-1.5 pr-4">
                    <div className="flex items-center gap-2">
                      <span className={`rounded-md border px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider ${style.bg} ${style.text} border-slate-700/50`}>
                        {cat}
                      </span>
                      {m.created_at && (
                        <span className="text-[10px] font-mono text-slate-500">
                          {new Date(m.created_at).toLocaleString()}
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-slate-200 font-medium group-hover:text-white transition-colors">
                      {m.content}
                    </p>
                  </div>

                  <div className="shrink-0 text-slate-600 group-hover:text-indigo-400 transition-colors">
                    <Eye className="h-4 w-4" />
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* ── 5. Memory Details Modal ──────────────────────────────────────────── */}
      <AnimatePresence>
        {selectedMemory && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 p-4 backdrop-blur-sm">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="w-full max-w-lg rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl space-y-4"
            >
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div className="flex items-center gap-2">
                  <span className={`rounded-md border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${getCategoryStyle(selectedMemory.metadata?.memory_type || "general").bg} ${getCategoryStyle(selectedMemory.metadata?.memory_type || "general").text} border-slate-700/50`}>
                    {selectedMemory.metadata?.memory_type || "general"}
                  </span>
                  <span className="text-xs font-semibold text-slate-300">Memory Inspector</span>
                </div>
                <button
                  onClick={() => setSelectedMemory(null)}
                  className="rounded-lg p-1 text-slate-400 hover:bg-slate-800 hover:text-white"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              <div className="space-y-3">
                <div>
                  <label className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
                    Decrypted Content
                  </label>
                  <p className="mt-1 rounded-xl bg-slate-950 p-3 text-xs leading-relaxed text-slate-200 border border-slate-800 font-mono">
                    {selectedMemory.content}
                  </p>
                </div>

                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div className="rounded-lg bg-slate-950/60 p-2.5 border border-slate-800/60">
                    <span className="text-[10px] font-bold uppercase text-slate-500">Memory ID</span>
                    <p className="font-mono text-[10px] text-indigo-400 truncate mt-0.5">{selectedMemory.id}</p>
                  </div>
                  <div className="rounded-lg bg-slate-950/60 p-2.5 border border-slate-800/60">
                    <span className="text-[10px] font-bold uppercase text-slate-500">Source</span>
                    <p className="font-mono text-[10px] text-amber-400 truncate mt-0.5">{selectedMemory.metadata?.source || "user_input"}</p>
                  </div>
                </div>

                {selectedMemory.created_at && (
                  <div className="flex items-center gap-1.5 text-[10px] text-slate-500 font-mono">
                    <Clock className="h-3 w-3" />
                    <span>Created: {new Date(selectedMemory.created_at).toUTCString()}</span>
                  </div>
                )}
              </div>

              <div className="pt-2 flex justify-end">
                <button
                  onClick={() => setSelectedMemory(null)}
                  className="rounded-lg bg-slate-800 px-4 py-2 text-xs font-semibold text-slate-200 hover:bg-slate-700"
                >
                  Close
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
