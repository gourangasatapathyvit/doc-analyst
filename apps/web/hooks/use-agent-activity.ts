"use client";

import { useEffect, useState } from "react";
import type { JSONValue } from "ai";

export function useAgentActivity(data: JSONValue[] | undefined) {
  const [activeAgent, setActiveAgent] = useState<string | null>(null);
  const [agentHistory, setAgentHistory] = useState<string[]>([]);

  useEffect(() => {
    if (!data || data.length === 0) return;

    const latest = data[data.length - 1];
    if (typeof latest !== "object" || latest === null || Array.isArray(latest)) return;

    const annotation = latest as Record<string, unknown>;
    if (annotation.type === "agent_start" && typeof annotation.agent === "string") {
      setActiveAgent(annotation.agent);
      setAgentHistory((prev) =>
        prev.includes(annotation.agent as string) ? prev : [...prev, annotation.agent as string]
      );
    } else if (annotation.type === "agent_end") {
      setActiveAgent(null);
    }
  }, [data]);

  const reset = () => {
    setActiveAgent(null);
    setAgentHistory([]);
  };

  return { activeAgent, agentHistory, reset };
}
