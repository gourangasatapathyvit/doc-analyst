"use client";

import { useState } from "react";
import { Sidebar } from "@/components/sidebar/sidebar";
import { ChatContainer } from "@/components/chat/chat-container";
import { useSession } from "@/hooks/use-session";
import { PanelLeftClose, PanelLeft } from "lucide-react";

export default function Home() {
  const { sessionId, uploadedFiles, addFile, removeFile, resetSession, hydrated } = useSession();
  const [sidebarOpen, setSidebarOpen] = useState(true);

  if (!hydrated) {
    return <div className="flex h-screen bg-white dark:bg-gray-900" />;
  }

  return (
    <div className="flex h-screen bg-white dark:bg-gray-900">
      {sidebarOpen && (
        <Sidebar
          uploadedFiles={uploadedFiles}
          onFileRemoved={removeFile}
          onNewChat={resetSession}
        />
      )}
      <main className="flex-1 flex flex-col min-w-0">
        <header className="h-12 flex items-center px-4 gap-3 flex-shrink-0">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500 transition-colors"
          >
            {sidebarOpen ? (
              <PanelLeftClose className="w-5 h-5" />
            ) : (
              <PanelLeft className="w-5 h-5" />
            )}
          </button>
          <h1 className="text-sm font-medium text-gray-600 dark:text-gray-400">
            Document Analyst
          </h1>
        </header>
        <div className="flex-1 overflow-hidden">
          <ChatContainer
            sessionId={sessionId}
            uploadedFiles={uploadedFiles}
            onAgentChange={() => {}}
            onFileUploaded={addFile}
          />
        </div>
      </main>
    </div>
  );
}
