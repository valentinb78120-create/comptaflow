import { useCallback, useState } from "react";
import { isAxiosError } from "axios";
import { useDropzone } from "react-dropzone";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { UploadCloud, ArrowRight } from "lucide-react";
import { api } from "../lib/api";
import { useCabinetId } from "../lib/CabinetContext";
import { cn } from "../lib/utils";

type FileState = {
  name: string;
  size: number;
  status: "uploading" | "done" | "error";
  error?: string;
};

const ACCEPTED = {
  "application/pdf": [".pdf"],
  "image/jpeg": [".jpg", ".jpeg"],
  "image/png": [".png"],
};

export function UploadPage() {
  const cabinetId = useCabinetId();
  const [files, setFiles] = useState<FileState[]>([]);
  const [busy, setBusy] = useState(false);

  const onDrop = useCallback(
    async (accepted: File[]) => {
      if (!accepted.length) return;
      setBusy(true);

      // Affiche immédiatement tous les fichiers en "uploading"
      const startIndex = files.length;
      setFiles((prev) => [
        ...prev,
        ...accepted.map((f) => ({ name: f.name, size: f.size, status: "uploading" as const })),
      ]);

      let okCount = 0;
      for (let i = 0; i < accepted.length; i++) {
        const idx = startIndex + i;
        try {
          await api.uploadInvoice(accepted[i], cabinetId);
          okCount++;
          setFiles((prev) => prev.map((f, j) => (j === idx ? { ...f, status: "done" } : f)));
        } catch (err: unknown) {
          let msg = "Erreur d'upload";
          if (isAxiosError(err)) {
            if (err.response?.status === 409) msg = "Doublon — facture déjà uploadée";
            // 402 = trial expiré OU quota mensuel atteint : le serveur précise
            else if (err.response?.data?.detail) msg = String(err.response.data.detail);
          }
          setFiles((prev) =>
            prev.map((f, j) => (j === idx ? { ...f, status: "error", error: msg } : f))
          );
        }
      }

      setBusy(false);
      if (okCount > 0) {
        toast.success(
          `${okCount} facture${okCount > 1 ? "s" : ""} envoyée${okCount > 1 ? "s" : ""} — OCR en cours`
        );
      }
    },
    [cabinetId, files.length]
  );

  const { getRootProps, getInputProps, isDragActive, fileRejections } = useDropzone({
    onDrop,
    accept: ACCEPTED,
    maxSize: 20 * 1024 * 1024,
    disabled: busy,
  });

  const doneCount = files.filter((f) => f.status === "done").length;

  return (
    <main className="max-w-3xl mx-auto px-6 py-8 space-y-6">
      <div>
        <h1 className="font-display text-2xl font-bold text-ink-900">Ajouter des factures</h1>
        <p className="text-sm text-ink-500 mt-0.5">PDF ou photos, par lot. L'OCR démarre automatiquement.</p>
      </div>

      <div
        {...getRootProps()}
        className={cn(
          "relative overflow-hidden rounded-4xl p-16 text-center cursor-pointer transition-all duration-200",
          "border-2 border-dashed",
          isDragActive
            ? "border-brand-500 bg-brand-50 scale-[1.01] shadow-glow"
            : "border-ink-200 bg-white hover:border-brand-400 hover:bg-brand-50/40 shadow-card",
          busy && "opacity-60 cursor-not-allowed"
        )}
      >
        {isDragActive && <div className="absolute inset-0 bg-mesh opacity-60" />}
        <input {...getInputProps()} />
        <div className="relative flex flex-col items-center gap-4">
          <div className={cn(
            "w-16 h-16 rounded-2xl flex items-center justify-center transition-all duration-200",
            isDragActive ? "bg-brand-gradient scale-110 shadow-glow" : "bg-brand-50"
          )}>
            <UploadCloud className={cn("w-8 h-8 transition-colors", isDragActive ? "text-white" : "text-brand-600")} />
          </div>
          {busy ? (
            <p className="text-sm font-medium text-ink-500">Envoi en cours…</p>
          ) : isDragActive ? (
            <p className="text-base font-semibold text-brand-700">Déposez les fichiers ici</p>
          ) : (
            <>
              <p className="text-base font-semibold text-ink-700">
                Glissez vos factures ici ou <span className="text-gradient">parcourez</span>
              </p>
              <p className="text-xs text-ink-400">PDF, JPG, PNG — max 20 Mo — plusieurs fichiers acceptés</p>
            </>
          )}
        </div>
      </div>

      {fileRejections.length > 0 && (
        <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-xl px-4 py-3">
          {fileRejections.length} fichier(s) refusé(s) : format non supporté ou taille &gt; 20 Mo
        </div>
      )}

      {files.length > 0 && (
        <section className="card divide-y divide-ink-100 overflow-hidden">
          {files.map((f, i) => (
            <div key={`${f.name}-${i}`} className="flex items-center gap-3 px-5 py-3.5">
              <FileIcon status={f.status} />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-ink-900 truncate">{f.name}</p>
                <p className="text-xs text-ink-400">{(f.size / 1024 / 1024).toFixed(2)} Mo{f.error ? ` — ${f.error}` : ""}</p>
              </div>
              <StatusText status={f.status} />
            </div>
          ))}
        </section>
      )}

      {doneCount > 0 && !busy && (
        <div className="flex justify-end">
          <Link to="/dashboard" className="btn-primary">
            Voir le traitement OCR <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      )}
    </main>
  );
}

function FileIcon({ status }: { status: FileState["status"] }) {
  if (status === "done")
    return (
      <span className="w-7 h-7 rounded-full bg-green-100 text-green-600 flex items-center justify-center shrink-0">
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
        </svg>
      </span>
    );
  if (status === "error")
    return (
      <span className="w-7 h-7 rounded-full bg-red-100 text-red-600 flex items-center justify-center shrink-0">
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
        </svg>
      </span>
    );
  return (
    <span className="w-7 h-7 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center shrink-0 animate-pulse">
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6l4 2" />
      </svg>
    </span>
  );
}

function StatusText({ status }: { status: FileState["status"] }) {
  const map = {
    uploading: <span className="text-xs text-blue-600">Envoi…</span>,
    done: <span className="text-xs text-green-600">Envoyé</span>,
    error: <span className="text-xs text-red-600">Échec</span>,
  };
  return map[status];
}
