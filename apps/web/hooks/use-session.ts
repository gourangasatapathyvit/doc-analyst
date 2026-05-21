"use client";

import { useCallback, useEffect, useState } from "react";
import { v4 as uuidv4 } from "uuid";
import type { FileMetadata } from "@doc-analyst/contracts";
import { log } from "@/lib/logger";

const SESSION_KEY = "doc_analyst_session_id";
const FILES_KEY = "doc_analyst_files";

export function useSession() {
  // Start with stable defaults to avoid hydration mismatch
  const [sessionId, setSessionId] = useState<string>("");
  const [uploadedFiles, setUploadedFiles] = useState<FileMetadata[]>([]);
  const [hydrated, setHydrated] = useState(false);

  // Hydrate from localStorage after mount (client only)
  useEffect(() => {
    let id = localStorage.getItem(SESSION_KEY);
    if (!id) {
      id = uuidv4();
      localStorage.setItem(SESSION_KEY, id);
    }
    setSessionId(id);

    try {
      const stored = localStorage.getItem(FILES_KEY);
      if (stored) setUploadedFiles(JSON.parse(stored));
    } catch { /* ignore */ }

    setHydrated(true);
  }, []);

  // Persist files to localStorage whenever they change
  useEffect(() => {
    if (hydrated) {
      localStorage.setItem(FILES_KEY, JSON.stringify(uploadedFiles));
    }
  }, [uploadedFiles, hydrated]);

  const resetSession = useCallback(() => {
    const newId = uuidv4();
    setSessionId(newId);
    setUploadedFiles([]);
    localStorage.setItem(SESSION_KEY, newId);
    localStorage.removeItem(FILES_KEY);
    log("session_reset", { sessionId: newId });
  }, []);

  const addFile = useCallback((file: FileMetadata) => {
    setUploadedFiles((prev) => [...prev, file]);
  }, []);

  const removeFile = useCallback(
    async (fileId: string) => {
      await fetch(`/api/files/${fileId}?session_id=${sessionId}`, {
        method: "DELETE",
      });
      setUploadedFiles((prev) => prev.filter((f) => f.file_id !== fileId));
      log("file_removed", { fileId });
    },
    [sessionId]
  );

  return {
    sessionId,
    uploadedFiles,
    addFile,
    removeFile,
    resetSession,
    hydrated,
  };
}
