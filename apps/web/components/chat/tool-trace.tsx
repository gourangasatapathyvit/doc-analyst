"use client";

import { useState } from "react";
import { ChevronRight, Wrench, Search, FileText, Globe } from "lucide-react";

interface ToolCall {
  tool: string;
  agent: string;
  input?: string;
  output?: string;
}

const TOOL_ICONS: Record<string, typeof Wrench> = {
  search_document: Search,
  get_page: FileText,
  list_documents: FileText,
  tavily_search: Globe,
};

function formatToolName(name: string): string {
  return name.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatAgentName(name: string): string {
  return name.replace(/_/g, " ");
}

export function ToolTrace({ calls }: { calls: ToolCall[] }) {
  const [open, setOpen] = useState(false);

  if (calls.length === 0) return null;

  // Collect unique agents
  const agents = [...new Set(calls.map((c) => c.agent).filter(Boolean))];

  return (
    <div className="my-2">
      {/* Parent toggle */}
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 px-3 py-2 rounded-lg text-xs text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors border border-gray-150 dark:border-gray-700 w-full text-left"
      >
        <ChevronRight
          className={`w-3 h-3 transition-transform ${open ? "rotate-90" : ""}`}
        />
        <Wrench className="w-3.5 h-3.5 text-violet-500" />
        <span className="font-medium">
          {calls.length} tool call{calls.length > 1 ? "s" : ""}
        </span>
        {agents.length > 0 && (
          <span className="text-gray-400">
            via {agents.map(formatAgentName).join(", ")}
          </span>
        )}
      </button>

      {/* Expanded: individual tool calls */}
      {open && (
        <div className="flex flex-col gap-1 mt-1 pl-3">
          {calls.map((call, i) => (
            <ToolCallItem key={i} call={call} />
          ))}
        </div>
      )}
    </div>
  );
}

function ToolCallItem({ call }: { call: ToolCall }) {
  const [open, setOpen] = useState(false);
  const Icon = TOOL_ICONS[call.tool] || Wrench;

  return (
    <div className="rounded-lg border border-gray-150 dark:border-gray-700 overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 w-full px-3 py-2 text-left text-xs hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
      >
        <ChevronRight
          className={`w-3 h-3 text-gray-400 transition-transform ${open ? "rotate-90" : ""}`}
        />
        <Icon className="w-3.5 h-3.5 text-violet-500" />
        <span className="font-medium text-gray-600 dark:text-gray-300">
          {formatToolName(call.tool)}
        </span>
        {call.input && call.input.length > 0 && (
          <span className="text-gray-400 truncate max-w-[200px]">
            {call.input.length > 60 ? call.input.slice(0, 60) + "..." : call.input}
          </span>
        )}
      </button>

      {open && (
        <div className="px-3 pb-3 pt-1 border-t border-gray-100 dark:border-gray-700 space-y-2">
          {call.input && (
            <div>
              <p className="text-[10px] font-semibold uppercase text-gray-400 mb-1">Input</p>
              <pre className="text-xs text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-gray-800 rounded p-2 overflow-x-auto whitespace-pre-wrap">
                {call.input}
              </pre>
            </div>
          )}
          {call.output && (
            <div>
              <p className="text-[10px] font-semibold uppercase text-gray-400 mb-1">Output</p>
              <pre className="text-xs text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-gray-800 rounded p-2 overflow-x-auto whitespace-pre-wrap max-h-48 overflow-y-auto">
                {call.output}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// Parse the TRACE block appended at the end of the stream
export interface ParsedMessage {
  text: string;
  toolCalls: ToolCall[];
  agents: string[];
}

export function parseToolMarkers(raw: string): ParsedMessage {
  let text = raw;
  let toolCalls: ToolCall[] = [];
  let agents: string[] = [];

  // Extract the single <!--TRACE:{...}--> block at the end
  const traceMatch = text.match(/<!--TRACE:(.*?)-->/s);
  if (traceMatch) {
    try {
      const trace = JSON.parse(traceMatch[1]);
      toolCalls = trace.toolCalls || [];
      agents = trace.agents || [];
    } catch { /* skip */ }
    // Remove the trace block from display text
    text = text.replace(/\s*<!--TRACE:.*?-->\s*/s, "");
  }

  // Strip any partial <!--TRACE at the end (still streaming)
  text = text.replace(/\s*<!--TRACE[^>]*$/s, "");
  text = text.replace(/\s*<!--[^>]*$/s, "");

  text = text.trim();

  return { text, toolCalls, agents };
}
