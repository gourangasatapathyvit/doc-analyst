"use client";

import { FileText, X } from "lucide-react";
import type { FileMetadata } from "@doc-analyst/contracts";

interface FileListProps {
  files: FileMetadata[];
  onRemove: (fileId: string) => void;
}

export function FileList({ files, onRemove }: FileListProps) {
  if (files.length === 0) return null;

  return (
    <div className="space-y-2">
      <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300">Files</h3>
      {files.map((file) => (
        <div
          key={file.file_id}
          className="flex items-center justify-between p-2 rounded-md bg-gray-50 dark:bg-gray-800"
        >
          <div className="flex items-center gap-2 min-w-0">
            <FileText className="w-4 h-4 text-blue-500 flex-shrink-0" />
            <div className="min-w-0">
              <p className="text-sm truncate">{file.filename}</p>
              <p className="text-xs text-gray-400">
                {file.pages} pages
              </p>
            </div>
          </div>
          <button
            onClick={() => onRemove(file.file_id)}
            className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded"
          >
            <X className="w-3 h-3" />
          </button>
        </div>
      ))}
    </div>
  );
}
