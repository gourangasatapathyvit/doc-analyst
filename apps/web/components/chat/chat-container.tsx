"use client";

import { useChat } from "@ai-sdk/react";
import { TextStreamChatTransport } from "ai";
import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { Sparkles } from "lucide-react";
import { MessageBubble } from "./message-bubble";
import { ChatInput } from "./chat-input";
import { EmptyState } from "./empty-state";
import type { FileMetadata } from "@doc-analyst/contracts";

interface ChatContainerProps {
  sessionId: string;
  uploadedFiles: FileMetadata[];
  onAgentChange: (agent: string | null) => void;
  onFileUploaded: (file: FileMetadata) => void;
}

// Inner component that gets re-mounted when chatKey changes
function ChatInner({
  sessionId,
  fileIds,
  onAgentChange,
  onFileUploaded,
}: {
  sessionId: string;
  fileIds: string[];
  onAgentChange: (agent: string | null) => void;
  onFileUploaded: (file: FileMetadata) => void;
}) {
  const [input, setInput] = useState("");

  const transport = useMemo(
    () =>
      new TextStreamChatTransport({
        api: "/api/chat",
        body: {
          session_id: sessionId,
          file_ids: fileIds,
        },
      }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [] // intentionally empty — component remounts when key changes
  );

  const { messages, sendMessage, stop, status } = useChat({ transport });
  const isLoading = status === "streaming" || status === "submitted";
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;
    const msg = input;
    setInput("");
    await sendMessage({ text: msg });
  };

  const getMessageText = (msg: (typeof messages)[0]): string => {
    return (
      msg.parts
        ?.filter((p): p is { type: "text"; text: string } => p.type === "text")
        .map((p) => p.text)
        .join("") ?? ""
    );
  };

  if (messages.length === 0) {
    return (
      <div className="flex flex-col h-full">
        <div className="flex-1">
          <EmptyState />
        </div>
        <ChatInput
          input={input}
          isLoading={isLoading}
          sessionId={sessionId}
          onInputChange={(e) => setInput(e.target.value)}
          onSubmit={handleSubmit}
          onStop={stop}
          onFileUploaded={onFileUploaded}
        />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-white dark:bg-gray-900">
      <div className="flex-1 overflow-y-auto">
        <div className="divide-y divide-gray-100 dark:divide-gray-800">
          {messages.map((m) => (
            <MessageBubble
              key={m.id}
              role={m.role as "user" | "assistant"}
              content={getMessageText(m)}
            />
          ))}
        </div>
        {isLoading && (
          <div className="w-full border-t border-gray-100 dark:border-gray-800">
            <div className="max-w-3xl mx-auto px-4 py-4 flex items-center gap-3">
              <Sparkles className="w-5 h-5 text-violet-500 animate-pulse" />
              <span className="text-sm text-gray-400">Thinking...</span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>
      <div className="border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900">
        <div className="max-w-3xl mx-auto">
          <ChatInput
            input={input}
            isLoading={isLoading}
            sessionId={sessionId}
            onInputChange={(e) => setInput(e.target.value)}
            onSubmit={handleSubmit}
            onStop={stop}
            onFileUploaded={onFileUploaded}
          />
        </div>
      </div>
    </div>
  );
}

export function ChatContainer({
  sessionId,
  uploadedFiles,
  onAgentChange,
  onFileUploaded,
}: ChatContainerProps) {
  // Key changes when files change → ChatInner remounts → new transport with current file_ids
  const fileIds = uploadedFiles.map((f) => f.file_id);
  const chatKey = `${sessionId}-${fileIds.join(",")}`;

  return (
    <ChatInner
      key={chatKey}
      sessionId={sessionId}
      fileIds={fileIds}
      onAgentChange={onAgentChange}
      onFileUploaded={onFileUploaded}
    />
  );
}
