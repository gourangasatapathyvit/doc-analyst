"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { CircleUser, Sparkles } from "lucide-react";
import { ToolTrace, parseToolMarkers } from "./tool-trace";

interface MessageBubbleProps {
  role: "user" | "assistant";
  content: string;
}

export function MessageBubble({ role, content }: MessageBubbleProps) {
  const isUser = role === "user";
  const parsed = isUser ? null : parseToolMarkers(content);
  const displayText = parsed?.text || content;
  const toolCalls = parsed?.toolCalls || [];
  const agents = parsed?.agents || [];

  return (
    <div className="w-full">
      <div className="max-w-3xl mx-auto px-4 py-6">
        {/* Header row: icon + name + agent badges */}
        <div className="flex items-center gap-2 mb-2">
          {isUser ? (
            <CircleUser className="w-5 h-5 text-gray-500 dark:text-gray-400" />
          ) : (
            <Sparkles className="w-5 h-5 text-violet-500" />
          )}
          <span className="text-sm font-semibold text-gray-800 dark:text-gray-200">
            {isUser ? "You" : "Document Analyst"}
          </span>
          {!isUser && agents.length > 0 && (
            <div className="flex gap-1 ml-1">
              {agents.map((agent) => (
                <span
                  key={agent}
                  className="text-[10px] px-1.5 py-0.5 rounded bg-violet-100 dark:bg-violet-900/40 text-violet-600 dark:text-violet-400 font-medium"
                >
                  {agent.replace(/_/g, " ")}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Tool trace — collapsible */}
        {!isUser && toolCalls.length > 0 && (
          <div className="pl-7 mb-3">
            <ToolTrace calls={toolCalls} />
          </div>
        )}

        {/* Content */}
        {isUser ? (
          <div className="pl-7 text-[15px] text-gray-800 dark:text-gray-200 whitespace-pre-wrap">
            {displayText}
          </div>
        ) : (
          <div className="pl-7 text-[15px] text-gray-800 dark:text-gray-200 prose prose-gray dark:prose-invert max-w-none prose-p:my-2 prose-ul:my-2 prose-ol:my-2 prose-li:my-0.5 prose-headings:my-3 prose-pre:bg-gray-900 prose-pre:text-gray-100 prose-code:text-violet-600 dark:prose-code:text-violet-400 prose-code:before:content-[''] prose-code:after:content-[''] prose-a:text-blue-600 dark:prose-a:text-blue-400">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{displayText}</ReactMarkdown>
          </div>
        )}
      </div>
    </div>
  );
}
