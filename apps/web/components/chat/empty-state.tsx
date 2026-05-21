"use client";

import { FileText, Globe, Lightbulb } from "lucide-react";

export function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center px-8">
      <h2 className="text-2xl font-semibold text-gray-800 dark:text-gray-200 mb-4">
        Document Analyst
      </h2>
      <p className="text-gray-500 dark:text-gray-400 mb-8 max-w-md">
        Upload a document and ask me anything about it. I can search, analyze,
        and compare information across your files and the web.
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 max-w-lg">
        <div className="flex flex-col items-center gap-2 p-4 rounded-lg bg-gray-50 dark:bg-gray-800">
          <FileText className="w-6 h-6 text-blue-500" />
          <p className="text-xs text-gray-500">Search documents</p>
        </div>
        <div className="flex flex-col items-center gap-2 p-4 rounded-lg bg-gray-50 dark:bg-gray-800">
          <Globe className="w-6 h-6 text-green-500" />
          <p className="text-xs text-gray-500">Web research</p>
        </div>
        <div className="flex flex-col items-center gap-2 p-4 rounded-lg bg-gray-50 dark:bg-gray-800">
          <Lightbulb className="w-6 h-6 text-amber-500" />
          <p className="text-xs text-gray-500">Analyze & compare</p>
        </div>
      </div>
    </div>
  );
}
