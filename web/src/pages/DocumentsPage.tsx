import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Upload, FileText, Trash2, AlertCircle, CheckCircle, Loader2, Clock } from "lucide-react";
import { useDropzone } from "react-dropzone";
import { api } from "../lib/api";
import type { Document, DocumentList } from "../lib/types";

export function DocumentsPage() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [uploading, setUploading] = useState(false);

  const fetchDocuments = async () => {
    try {
      const data = await api.get<DocumentList>("/api/v1/documents?page_size=50");
      setDocuments(data.items);
    } catch {
      toast.error("Failed to load documents");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, []);

  const onDrop = async (files: File[]) => {
    for (const file of files) {
      setUploading(true);
      try {
        const formData = new FormData();
        formData.append("file", file);
        await api.upload<Document>("/api/v1/documents/upload", formData);
        toast.success(`Uploaded ${file.name}`);
        await fetchDocuments();
      } catch (err: any) {
        toast.error(err.message || `Failed to upload ${file.name}`);
      } finally {
        setUploading(false);
      }
    }
  };

  const handleDelete = async (doc: Document) => {
    if (!confirm(`Delete "${doc.filename}"? This cannot be undone.`)) return;
    try {
      await api.delete(`/api/v1/documents/${doc.id}`);
      setDocuments((prev) => prev.filter((d) => d.id !== doc.id));
      toast.success("Document deleted");
    } catch (err: any) {
      toast.error(err.message || "Failed to delete document");
    }
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/pdf": [".pdf"],
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
      "text/plain": [".txt"],
      "text/markdown": [".md"],
    },
    disabled: uploading,
  });

  return (
    <div className="h-full overflow-y-auto">
      <div className="max-w-4xl mx-auto px-4 py-8">
        <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-6">
          Documents
        </h1>

        {/* Upload zone */}
        <div
          {...getRootProps()}
          className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors cursor-pointer mb-8 ${
            isDragActive
              ? "border-blue-500 bg-blue-50 dark:bg-blue-950/20"
              : "border-gray-300 dark:border-gray-700 hover:border-gray-400 dark:hover:border-gray-600"
          } ${uploading ? "opacity-50 cursor-not-allowed" : ""}`}
        >
          <input {...getInputProps()} />
          <Upload
            size={32}
            className="mx-auto mb-3 text-gray-400 dark:text-gray-500"
          />
          {uploading ? (
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Uploading...
            </p>
          ) : isDragActive ? (
            <p className="text-sm text-blue-600 dark:text-blue-400">
              Drop files here
            </p>
          ) : (
            <>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Drag & drop files here, or click to browse
              </p>
              <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
                PDF, DOCX, TXT, MD — up to 20MB
              </p>
            </>
          )}
        </div>

        {/* Document list */}
        {isLoading ? (
          <div className="flex justify-center py-12">
            <div className="animate-spin h-6 w-6 border-2 border-gray-300 border-t-blue-600 rounded-full" />
          </div>
        ) : documents.length === 0 ? (
          <div className="text-center py-12">
            <FileText size={40} className="mx-auto mb-3 text-gray-300 dark:text-gray-700" />
            <p className="text-sm text-gray-500 dark:text-gray-400">
              No documents uploaded yet
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {documents.map((doc) => (
              <div
                key={doc.id}
                className="flex items-center gap-3 px-4 py-3 rounded-lg border border-gray-200 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-900/50 transition-colors"
              >
                <FileText size={18} className="shrink-0 text-gray-400" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                    {doc.filename}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    {formatFileSize(doc.file_size)} · {doc.chunk_count} chunks ·{" "}
                    {new Date(doc.created_at).toLocaleDateString()}
                  </p>
                </div>
                <StatusBadge status={doc.status} />
                <button
                  onClick={() => handleDelete(doc)}
                  className="p-1.5 text-gray-400 hover:text-red-600 dark:hover:text-red-400 transition-colors"
                  title="Delete"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: Document["status"] }) {
  const config = {
    pending: { icon: Clock, color: "text-yellow-600 dark:text-yellow-400", label: "Pending" },
    processing: { icon: Loader2, color: "text-blue-600 dark:text-blue-400", label: "Processing" },
    ready: { icon: CheckCircle, color: "text-green-600 dark:text-green-400", label: "Ready" },
    failed: { icon: AlertCircle, color: "text-red-600 dark:text-red-400", label: "Failed" },
  };
  const { icon: Icon, color, label } = config[status];

  return (
    <span className={`flex items-center gap-1 text-xs ${color}`}>
      <Icon size={14} className={status === "processing" ? "animate-spin" : ""} />
      {label}
    </span>
  );
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
