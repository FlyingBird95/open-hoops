import { useCallback, useState } from "react";
import { Upload, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

interface DropZoneProps {
  files: File[];
  onChange: (files: File[]) => void;
  accept?: string;
  disabled?: boolean;
}

export function DropZone({ files, onChange, accept = "video/*", disabled }: DropZoneProps) {
  const [dragOver, setDragOver] = useState(false);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    if (disabled) return;
    const dropped = Array.from(e.dataTransfer.files).filter(f =>
      accept === "video/*" ? f.type.startsWith("video/") : true
    );
    onChange([...files, ...dropped]);
  }, [files, onChange, accept, disabled]);

  const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      onChange([...files, ...Array.from(e.target.files)]);
    }
    e.target.value = "";
  }, [files, onChange]);

  const removeFile = (index: number) => {
    onChange(files.filter((_, i) => i !== index));
  };

  function formatSize(bytes: number) {
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  return (
    <div className="space-y-3">
      <label
        className={cn(
          "flex flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed p-8 cursor-pointer transition-colors",
          dragOver ? "border-primary bg-primary/5" : "border-muted-foreground/25 hover:border-muted-foreground/50",
          disabled && "opacity-50 cursor-not-allowed"
        )}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
      >
        <Upload className="h-8 w-8 text-muted-foreground/60" />
        <span className="text-sm text-muted-foreground">Drag videos here or click to browse</span>
        <input type="file" className="hidden" accept={accept} multiple onChange={handleFileInput} disabled={disabled} />
      </label>

      {files.length > 0 && (
        <ul className="space-y-1">
          {files.map((f, i) => (
            <li key={`${f.name}-${i}`} className="flex items-center justify-between rounded border px-3 py-2 text-sm">
              <span className="truncate">{f.name}</span>
              <div className="flex items-center gap-2">
                <span className="text-muted-foreground">{formatSize(f.size)}</span>
                <Button variant="ghost" size="icon" className="h-6 w-6" onClick={() => removeFile(i)} disabled={disabled}>
                  <X className="h-3 w-3" />
                </Button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
