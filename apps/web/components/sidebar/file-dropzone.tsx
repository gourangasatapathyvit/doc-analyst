"use client";

import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { Upload, Loader2 } from "lucide-react";
import type { FileMetadata } from "@doc-analyst/contracts";
import { log } from "@/lib/logger";

interface FileDropzoneProps {
  sessionId: string;
  onFileUploaded: (file: FileMetadata) => void;
}

export function FileDropzone({ sessionId, onFileUploaded }: FileDropzoneProps) {
  const [uploading, setUploading] = useState(false);

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      for (const file of acceptedFiles) {
        setUploading(true);
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
        } finally {
          setUploading(false);
        }
      }
    },
    [sessionId, onFileUploaded]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/pdf": [".pdf"],
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
      "application/vnd.openxmlformats-officedocument.presentationml.presentation": [".pptx"],
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"],
      "image/*": [".png", ".jpg", ".jpeg", ".tiff"],
    },
    multiple: true,
    disabled: uploading,
  });

  return (
    <div
      {...getRootProps()}
      className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors ${
        isDragActive
          ? "border-blue-500 bg-blue-50 dark:bg-blue-950"
          : "border-gray-300 dark:border-gray-600 hover:border-gray-400"
      } ${uploading ? "opacity-50 cursor-not-allowed" : ""}`}
    >
      <input {...getInputProps()} />
      {uploading ? (
        <div className="flex flex-col items-center gap-2">
          <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
          <p className="text-sm text-gray-500">Uploading...</p>
        </div>
      ) : (
        <div className="flex flex-col items-center gap-2">
          <Upload className="w-8 h-8 text-gray-400" />
          <p className="text-sm text-gray-500">
            {isDragActive ? "Drop files here" : "Drop files here or click to upload"}
          </p>
          <p className="text-xs text-gray-400">PDF, DOCX, PPTX, XLSX, images</p>
        </div>
      )}
    </div>
  );
}
