"use client";

import { useRef, useEffect, useCallback, useState } from "react";
import * as d3 from "d3";
import { useAgentStore, type StreamEvent, type EventType } from "@/store/useAgentStore";

// ─── Visual config per event type ─────────────────────────────────────────────
interface NodeMeta {
  label: string;
  fill: string;
  stroke: string;
  glow: string;
  icon: string;
}

const META: Record<EventType, NodeMeta> = {
  CONNECTED: { label: "Start",    fill: "#334155", stroke: "#475569", glow: "#47556940", icon: "⚡" },
  PLAN:      { label: "Plan",     fill: "#312e81", stroke: "#6366f1", glow: "#6366f140", icon: "📋" },
  TOOL_CALL: { label: "Tool",     fill: "#1e3a5f", stroke: "#3b82f6", glow: "#3b82f640", icon: "🔧" },
  EVIDENCE:  { label: "Evidence", fill: "#422006", stroke: "#f59e0b", glow: "#f59e0b40", icon: "📄" },
  DECISION:  { label: "Verify",   fill: "#042f2e", stroke: "#14b8a6", glow: "#14b8a640", icon: "🛡" },
  SUCCESS:   { label: "Done",     fill: "#052e16", stroke: "#22c55e", glow: "#22c55e40", icon: "✓" },
  ERROR:     { label: "Error",    fill: "#2c0b0b", stroke: "#ef4444", glow: "#ef444440", icon: "✗" },
};

// ─── Layout constants ─────────────────────────────────────────────────────────
const NODE_W = 110;
const NODE_H = 52;
const GAP_X = 36;
const GAP_Y = 20;
const PAD = 24;

// ─── Graph node data ──────────────────────────────────────────────────────────
interface GNode {
  id: string;
  event: EventType;
  label: string;
  detail: string;
  x: number;
  y: number;
}

interface GLink {
  source: string;
  target: string;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────
/** Derive a short user-facing detail string. Never expose reasoning. */
function safeDetail(evt: StreamEvent): string {
  const d = evt.data;
  switch (evt.event) {
    case "PLAN":
      return d.summary ? String(d.summary).slice(0, 50) : "Planning…";
    case "TOOL_CALL":
      return d.tool ? String(d.tool) : "Tool";
    case "EVIDENCE":
      return d.summary ? String(d.summary).slice(0, 50) : "Data collected";
    case "DECISION":
      return d.passed ? "Passed" : "Failed";
    case "SUCCESS":
      return "Completed";
    case "ERROR":
      return d.error ? String(d.error).slice(0, 50) : "Error";
    default:
      return "";
  }
}

/** Layout nodes in a responsive grid (left → right, wrapping to new rows). */
function layoutNodes(
  events: StreamEvent[],
  containerW: number
): { nodes: GNode[]; links: GLink[] } {
  // Filter out CONNECTED events
  const visible = events.filter((e) => e.event !== "CONNECTED");
  if (visible.length === 0) return { nodes: [], links: [] };

  const cols = Math.max(1, Math.floor((containerW - PAD * 2 + GAP_X) / (NODE_W + GAP_X)));
  const nodes: GNode[] = visible.map((evt, i) => {
    const col = i % cols;
    const row = Math.floor(i / cols);
    return {
      id: evt.id,
      event: evt.event,
      label: META[evt.event]?.label ?? evt.event,
      detail: safeDetail(evt),
      x: PAD + col * (NODE_W + GAP_X),
      y: PAD + row * (NODE_H + GAP_Y),
    };
  });

  const links: GLink[] = [];
  for (let i = 1; i < nodes.length; i++) {
    links.push({ source: nodes[i - 1].id, target: nodes[i].id });
  }

  return { nodes, links };
}

// ─── Component ────────────────────────────────────────────────────────────────
export default function ExecutionGraph() {
  const svgRef = useRef<SVGSVGElement>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(640);

  const { turns, activeTurnId } = useAgentStore();
  const activeTurn = turns.find((t) => t.id === activeTurnId) ?? turns[turns.length - 1];
  const events = activeTurn?.events ?? [];

  // ── Responsive width tracking ───────────────────────────────────────────────
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

  // ── D3 render ───────────────────────────────────────────────────────────────
  const render = useCallback(() => {
    const svg = d3.select(svgRef.current);
    if (!svgRef.current) return;

    const { nodes, links } = layoutNodes(events, width);

    // Calculate required SVG height
    const maxY = nodes.length > 0 ? Math.max(...nodes.map((n) => n.y)) + NODE_H + PAD : 120;
    svg.attr("viewBox", `0 0 ${width} ${maxY}`);

    // ── Defs: glow filter ───────────────────────────────────────────────────
    let defs = svg.select<SVGDefsElement>("defs");
    if (defs.empty()) {
      defs = svg.append("defs");
      const filter = defs.append("filter").attr("id", "glow");
      filter.append("feGaussianBlur").attr("stdDeviation", "3").attr("result", "blur");
      const merge = filter.append("feMerge");
      merge.append("feMergeNode").attr("in", "blur");
      merge.append("feMergeNode").attr("in", "SourceGraphic");
    }

    // ── Links ───────────────────────────────────────────────────────────────
    const nodeMap = new Map(nodes.map((n) => [n.id, n]));

    const linkSel = svg
      .selectAll<SVGLineElement, GLink>("line.graph-link")
      .data(links, (d) => `${d.source}-${d.target}`);

    linkSel.exit().transition().duration(200).style("opacity", 0).remove();

    const linkEnter = linkSel
      .enter()
      .append("line")
      .attr("class", "graph-link")
      .style("opacity", 0);

    linkEnter
      .merge(linkSel)
      .transition()
      .duration(400)
      .ease(d3.easeCubicOut)
      .attr("x1", (d) => (nodeMap.get(d.source)?.x ?? 0) + NODE_W / 2)
      .attr("y1", (d) => (nodeMap.get(d.source)?.y ?? 0) + NODE_H / 2)
      .attr("x2", (d) => (nodeMap.get(d.target)?.x ?? 0) + NODE_W / 2)
      .attr("y2", (d) => (nodeMap.get(d.target)?.y ?? 0) + NODE_H / 2)
      .attr("stroke", "#334155")
      .attr("stroke-width", 2)
      .attr("stroke-dasharray", "6 4")
      .style("opacity", 0.6);

    // ── Node groups ─────────────────────────────────────────────────────────
    const nodeSel = svg
      .selectAll<SVGGElement, GNode>("g.graph-node")
      .data(nodes, (d) => d.id);

    nodeSel.exit().transition().duration(200).style("opacity", 0).remove();

    const nodeEnter = nodeSel.enter().append("g").attr("class", "graph-node").style("opacity", 0);

    // Rect background
    nodeEnter
      .append("rect")
      .attr("rx", 12)
      .attr("ry", 12)
      .attr("width", NODE_W)
      .attr("height", NODE_H);

    // Icon
    nodeEnter
      .append("text")
      .attr("class", "node-icon")
      .attr("x", 14)
      .attr("y", NODE_H / 2 + 1)
      .attr("dominant-baseline", "central")
      .attr("font-size", "14px");

    // Label
    nodeEnter
      .append("text")
      .attr("class", "node-label")
      .attr("x", 32)
      .attr("y", 20)
      .attr("font-size", "11px")
      .attr("font-weight", "700")
      .attr("letter-spacing", "0.05em");

    // Detail
    nodeEnter
      .append("text")
      .attr("class", "node-detail")
      .attr("x", 32)
      .attr("y", 37)
      .attr("font-size", "9px")
      .attr("fill", "#94a3b8");

    // ── Enter + Update merge ────────────────────────────────────────────────
    const merged = nodeEnter.merge(nodeSel);

    merged
      .transition()
      .duration(400)
      .ease(d3.easeCubicOut)
      .attr("transform", (d) => `translate(${d.x},${d.y})`)
      .style("opacity", 1);

    merged
      .select("rect")
      .transition()
      .duration(400)
      .attr("fill", (d) => META[d.event]?.fill ?? "#1e293b")
      .attr("stroke", (d) => META[d.event]?.stroke ?? "#475569")
      .attr("stroke-width", 1.5)
      .attr("filter", "url(#glow)");

    merged.select(".node-icon").text((d) => META[d.event]?.icon ?? "");

    merged
      .select(".node-label")
      .attr("fill", (d) => META[d.event]?.stroke ?? "#94a3b8")
      .text((d) => d.label.toUpperCase());

    merged
      .select(".node-detail")
      .text((d) => (d.detail.length > 16 ? d.detail.slice(0, 16) + "…" : d.detail));

    // ── Pulse animation on the latest node ──────────────────────────────────
    merged.select("rect").classed("node-pulse", false);
    if (nodes.length > 0 && activeTurn?.status === "running") {
      const lastGroup = merged.filter((_d, i, nodes_el) => i === nodes_el.length - 1);
      lastGroup.select("rect").classed("node-pulse", true);
    }
  }, [events, width, activeTurn?.status]);

  useEffect(() => {
    render();
  }, [render]);

  const hasEvents = events.filter((e) => e.event !== "CONNECTED").length > 0;

  return (
    <div
      ref={wrapperRef}
      id="execution-graph"
      className="w-full max-w-3xl rounded-2xl border border-slate-800 bg-slate-950/80 shadow-2xl backdrop-blur-xl overflow-hidden"
    >
      {/* Header */}
      <div className="flex items-center gap-2.5 border-b border-slate-800/70 px-5 py-3">
        <div
          className={`h-2 w-2 rounded-full transition-colors duration-500 ${
            activeTurn?.status === "running"
              ? "animate-pulse bg-indigo-500"
              : "bg-slate-700"
          }`}
        />
        <h2 className="text-sm font-semibold text-slate-200">Execution Graph</h2>
      </div>

      {/* SVG canvas */}
      <div className="relative min-h-[120px]">
        {!hasEvents && (
          <div className="absolute inset-0 flex items-center justify-center text-xs text-slate-600">
            Waiting for execution events…
          </div>
        )}
        <svg ref={svgRef} className="w-full" style={{ minHeight: 120 }}>
          {/* D3 renders here */}
        </svg>
      </div>

      {/* CSS for pulse animation */}
      <style jsx>{`
        :global(.node-pulse) {
          animation: nodePulse 1.6s ease-in-out infinite;
        }
        @keyframes nodePulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.65; }
        }
      `}</style>
    </div>
  );
}
