"use client";

import { ArrowUp, Square, Plus, Loader2 } from "lucide-react";
import { type FormEvent, type KeyboardEvent, useRef, useEffect, useCallback, useState } from "react";
import type { FileMetadata } from "@doc-analyst/contracts";
import { log } from "@/lib/logger";

interface ChatInputProps {
  input: string;
  isLoading: boolean;
  sessionId: string;
  onInputChange: (e: React.ChangeEvent<HTMLTextAreaElement>) => void;
  onSubmit: (e: FormEvent) => void;
  onStop: () => void;
  onFileUploaded: (file: FileMetadata) => void;
}

export function ChatInput({
  input,
  isLoading,
  sessionId,
  onInputChange,
  onSubmit,
  onStop,
  onFileUploaded,
}: ChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    const el = textareaRef.current;
    if (el) {
      el.style.height = "auto";
      el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
    }
  }, [input]);

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (input.trim() && !isLoading) {
        onSubmit(e as unknown as FormEvent);
      }
    }
  };

  const handleFileSelect = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files;
      if (!files || files.length === 0) return;

      setUploading(true);

      for (const file of Array.from(files)) {
        try {
          const formData = new FormData();
          formData.append("file", file);
          formData.append("session_id", sessionId);

          const res = await fetch("/api/upload", {
            method: "POST",
            body: formData,
          });

          if (res.ok) {
            const data: FileMetadata = await res.json();
            onFileUploaded(data);
            log("file_uploaded", { filename: data.filename });
          }
        } catch (err) {
          console.error("Upload failed:", err);
        }
      }

      setUploading(false);
      e.target.value = "";
    },
    [sessionId, onFileUploaded]
  );

  return (
    <form onSubmit={onSubmit} className="p-4 pb-2">
      <div className="flex items-end gap-1 rounded-2xl border border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-800 shadow-sm focus-within:border-gray-400 dark:focus-within:border-gray-500 focus-within:shadow-md transition-all px-2 pb-2">
        {/* + button / upload spinner */}
        <div className="flex-shrink-0">
          {uploading ? (
            <div className="flex items-center justify-center w-8 h-8">
              <Loader2 className="w-5 h-5 text-violet-500 animate-spin" />
            </div>
          ) : (
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="flex items-center justify-center w-8 h-8 rounded-full hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-500 dark:text-gray-400 transition-colors"
              title="Attach file"
            >
              <Plus className="w-5 h-5" />
            </button>
          )}
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            accept="application/pdf,.pdf,.docx,.pptx,.xlsx,.png,.jpg,.jpeg,.tiff,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.openxmlformats-officedocument.presentationml.presentation,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,image/*"
            multiple
            onChange={handleFileSelect}
          />
        </div>

        <textarea
          ref={textareaRef}
          value={input}
          onChange={onInputChange}
          onKeyDown={handleKeyDown}
          placeholder={uploading ? "Uploading file..." : "Message Document Analyst..."}
          rows={1}
          className="flex-1 resize-none bg-transparent px-1 py-2.5 text-[15px] text-gray-800 dark:text-gray-200 placeholder-gray-400 focus:outline-none min-h-[36px]"
          disabled={isLoading || uploading}
        />

        <div className="flex-shrink-0">
          {isLoading ? (
            <button
              type="button"
              onClick={onStop}
              className="flex items-center justify-center w-8 h-8 rounded-lg bg-gray-800 dark:bg-gray-200 text-white dark:text-gray-800 hover:bg-gray-700 dark:hover:bg-gray-300 transition-colors"
            >
              <Square className="w-3.5 h-3.5" />
            </button>
          ) : (
            <button
              type="submit"
              disabled={!input.trim() || uploading}
              className="flex items-center justify-center w-8 h-8 rounded-lg bg-gray-800 dark:bg-gray-200 text-white dark:text-gray-800 disabled:bg-gray-300 dark:disabled:bg-gray-600 disabled:text-gray-400 dark:disabled:text-gray-500 disabled:cursor-not-allowed hover:bg-gray-700 dark:hover:bg-gray-300 transition-colors"
            >
              <ArrowUp className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>
      <p className="text-[11px] text-gray-400 text-center mt-2">
        Document Analyst can make mistakes. Verify important information.
      </p>
    </form>
  );
}
