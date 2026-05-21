"use client";

import { useState } from "react";
import { RotateCcw, Settings } from "lucide-react";
import type { FileMetadata } from "@doc-analyst/contracts";
import { FileList } from "./file-list";
import { SettingsModal } from "./settings-modal";

interface SidebarProps {
  uploadedFiles: FileMetadata[];
  onFileRemoved: (fileId: string) => void;
  onNewChat: () => void;
}

export function Sidebar({
  uploadedFiles,
  onFileRemoved,
  onNewChat,
}: SidebarProps) {
  const [settingsOpen, setSettingsOpen] = useState(false);

  return (
    <>
      <aside className="w-64 border-r border-gray-200 dark:border-gray-700 p-4 flex flex-col gap-4 bg-gray-50 dark:bg-gray-900 overflow-y-auto">
        <button
          onClick={onNewChat}
          className="flex items-center gap-2 w-full p-2.5 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
        >
          <RotateCcw className="w-4 h-4" />
          New Chat
        </button>

        <FileList files={uploadedFiles} onRemove={onFileRemoved} />

        {/* Settings at bottom */}
        <div className="mt-auto">
          <button
            onClick={() => setSettingsOpen(true)}
            className="flex items-center gap-2 w-full p-2 rounded-lg text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          >
            <Settings className="w-4 h-4" />
            Settings
          </button>
        </div>
      </aside>

      {settingsOpen && <SettingsModal onClose={() => setSettingsOpen(false)} />}
    </>
  );
}
