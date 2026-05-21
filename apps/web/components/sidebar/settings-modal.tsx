"use client";

import { useEffect, useState } from "react";
import { X, Bot, Wrench, Loader2, ChevronRight } from "lucide-react";

interface ToolInfo {
  name: string;
  description: string;
}

interface AgentInfo {
  name: string;
  description: string;
  tools: ToolInfo[];
}

function formatName(name: string): string {
  return name
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export function SettingsModal({ onClose }: { onClose: () => void }) {
  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    fetch("/api/agents")
      .then((res) => res.json())
      .then((data) => {
        setAgents(data.agents || []);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  // Close on escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative w-full max-w-2xl max-h-[80vh] bg-white dark:bg-gray-900 rounded-2xl shadow-2xl border border-gray-200 dark:border-gray-700 flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-200">
            Settings
          </h2>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          <h3 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-4">
            Registered Agents & Tools
          </h3>

          {loading && (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-6 h-6 text-gray-400 animate-spin" />
            </div>
          )}

          {error && (
            <p className="text-sm text-red-500 py-4">Failed to load: {error}</p>
          )}

          {!loading && !error && (
            <div className="space-y-4">
              {agents.map((agent) => (
                <AgentCard key={agent.name} agent={agent} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function AgentCard({ agent }: { agent: AgentInfo }) {
  const [open, setOpen] = useState(false);
  const toolCount = agent.tools.length;

  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
      {/* Agent header */}
      <div className="flex items-start gap-3 px-4 py-3 bg-gray-50 dark:bg-gray-800/50">
        <Bot className="w-5 h-5 text-violet-500 mt-0.5 flex-shrink-0" />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-gray-800 dark:text-gray-200">
            {formatName(agent.name)}
          </p>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
            {agent.description}
          </p>
        </div>
      </div>

      {/* Tools toggle */}
      {toolCount > 0 ? (
        <>
          <button
            onClick={() => setOpen(!open)}
            className="flex items-center gap-2 w-full px-4 py-2 text-xs text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800/30 transition-colors border-t border-gray-100 dark:border-gray-800"
          >
            <ChevronRight
              className={`w-3 h-3 transition-transform ${open ? "rotate-90" : ""}`}
            />
            <Wrench className="w-3 h-3" />
            <span>
              {toolCount} tool{toolCount > 1 ? "s" : ""}
            </span>
          </button>

          {open && (
            <div className="px-4 pb-3 divide-y divide-gray-100 dark:divide-gray-800">
              {agent.tools.map((tool) => (
                <div
                  key={tool.name}
                  className="flex items-start gap-2.5 py-2.5 pl-5"
                >
                  <Wrench className="w-3.5 h-3.5 text-gray-400 mt-0.5 flex-shrink-0" />
                  <div>
                    <p className="text-xs font-medium text-gray-700 dark:text-gray-300">
                      {formatName(tool.name)}
                    </p>
                    <p className="text-[11px] text-gray-400 dark:text-gray-500 mt-0.5 leading-relaxed">
                      {tool.description}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      ) : (
        <div className="px-4 py-2.5 border-t border-gray-100 dark:border-gray-800">
          <p className="text-xs text-gray-400 italic">
            No tools — uses LLM reasoning only
          </p>
        </div>
      )}
    </div>
  );
}
