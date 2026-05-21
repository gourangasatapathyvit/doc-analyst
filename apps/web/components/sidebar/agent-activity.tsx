"use client";

const AGENTS = ["pdf_agent", "research_agent", "analyzer_agent"];

interface AgentActivityProps {
  activeAgent: string | null;
}

export function AgentActivity({ activeAgent }: AgentActivityProps) {
  return (
    <div className="space-y-2">
      <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300">
        Agent Activity
      </h3>
      {AGENTS.map((agent) => (
        <div key={agent} className="flex items-center gap-2">
          <span
            className={`w-2 h-2 rounded-full ${
              activeAgent === agent
                ? "bg-green-500 animate-pulse"
                : "bg-gray-300 dark:bg-gray-600"
            }`}
          />
          <span className="text-sm text-gray-600 dark:text-gray-400">
            {agent.replace("_", " ")}
          </span>
        </div>
      ))}
    </div>
  );
}
