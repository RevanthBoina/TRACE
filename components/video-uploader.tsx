"use client"

import type React from "react"

import { useCallback, useRef, useState } from "react"
import { Progress } from "@/components/ui/progress"
import { Button } from "@/components/ui/button"
import { UploadCloud, FileVideo, Download, CheckCircle2, Loader2, AlertCircle } from "lucide-react"
import { cn } from "@/lib/utils"

type Status = "idle" | "uploading" | "processing" | "done"

const ACCEPTED = ["video/mp4", "video/quicktime", "video/x-msvideo", "video/x-matroska"]
const ACCEPTED_EXT = [".mp4", ".mov", ".avi", ".mkv"]
const MAX_BYTES = 2 * 1024 * 1024 * 1024 // 2GB

const PROCESSING_STEPS = ["Watermarking", "Generating fingerprint", "Finalizing"]

export function VideoUploader({ onDownloaded }: { onDownloaded: () => void }) {
  const [status, setStatus] = useState<Status>("idle")
  const [progress, setProgress] = useState(0)
  const [step, setStep] = useState(0)
  const [fileName, setFileName] = useState<string | null>(null)
  const [isDragging, setIsDragging] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const validate = (file: File): string | null => {
    const ext = file.name.slice(file.name.lastIndexOf(".")).toLowerCase()
    const okType = ACCEPTED.includes(file.type) || ACCEPTED_EXT.includes(ext)
    if (!okType) return "Unsupported format. Use MP4, MOV, AVI, or MKV."
    if (file.size > MAX_BYTES) return "File exceeds the 2GB free-tier limit."
    return null
  }

  const startUpload = useCallback((file: File) => {
    const validationError = validate(file)
    if (validationError) {
      setError(validationError)
      return
    }
    setError(null)
    setFileName(file.name)
    setStatus("uploading")
    setProgress(0)
    setStep(0)

    const interval = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 100) {
          clearInterval(interval)
          setStatus("processing")
          // Step through the processing pipeline
          PROCESSING_STEPS.forEach((_, i) => setTimeout(() => setStep(i), i * 900))
          setTimeout(() => setStatus("done"), PROCESSING_STEPS.length * 900)
          return 100
        }
        return prev + 4
      })
    }, 100)
  }, [])

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setIsDragging(false)
      const file = e.dataTransfer.files?.[0]
      if (file) startUpload(file)
    },
    [startUpload],
  )

  const handleSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) startUpload(file)
  }

  const reset = () => {
    setStatus("idle")
    setProgress(0)
    setStep(0)
    setFileName(null)
    setError(null)
    if (inputRef.current) inputRef.current.value = ""
  }

  return (
    <div className="flex flex-col gap-4">
      <div
        role="button"
        tabIndex={0}
        onClick={() => status === "idle" && inputRef.current?.click()}
        onKeyDown={(e) => {
          if ((e.key === "Enter" || e.key === " ") && status === "idle") inputRef.current?.click()
        }}
        onDragOver={(e) => {
          e.preventDefault()
          if (status === "idle") setIsDragging(true)
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={status === "idle" ? handleDrop : (e) => e.preventDefault()}
        className={cn(
          "flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-border bg-muted/30 px-6 py-12 text-center transition-colors",
          status === "idle" && "cursor-pointer hover:border-muted-foreground/50 hover:bg-muted/50",
          isDragging && "border-primary/60 bg-muted/60",
        )}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".mp4,.mov,.avi,.mkv,video/*"
          className="sr-only"
          onChange={handleSelect}
        />

        {status === "idle" && (
          <>
            <div className="flex size-12 items-center justify-center rounded-full bg-muted">
              <UploadCloud className="size-6 text-muted-foreground" aria-hidden="true" />
            </div>
            <div className="flex flex-col gap-1">
              <p className="text-sm font-medium text-foreground">Drag and drop your video here</p>
              <p className="text-xs text-muted-foreground">or click to browse — MP4, MOV, AVI, MKV up to 2GB</p>
            </div>
          </>
        )}

        {status !== "idle" && (
          <div className="flex w-full items-center gap-3 text-left">
            <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-muted">
              {status === "done" ? (
                <CheckCircle2 className="size-5 text-emerald-400" aria-hidden="true" />
              ) : status === "processing" ? (
                <Loader2 className="size-5 animate-spin text-muted-foreground" aria-hidden="true" />
              ) : (
                <FileVideo className="size-5 text-muted-foreground" aria-hidden="true" />
              )}
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-foreground">{fileName}</p>
              <p className="text-xs text-muted-foreground">
                {status === "uploading" && `Uploading… ${progress}%`}
                {status === "processing" && `${PROCESSING_STEPS[step]}…`}
                {status === "done" && "Your watermarked video is ready"}
              </p>
            </div>
          </div>
        )}
      </div>

      {error && (
        <p className="flex items-center gap-1.5 text-xs text-red-400" role="alert">
          <AlertCircle className="size-3.5 shrink-0" aria-hidden="true" />
          {error}
        </p>
      )}

      {(status === "uploading" || status === "processing") && (
        <Progress value={status === "processing" ? 100 : progress} className="h-1.5" />
      )}

      {status === "done" && (
        <div className="flex items-center gap-2">
          <Button className="flex-1 gap-2" onClick={onDownloaded}>
            <Download className="size-4" aria-hidden="true" />
            Download watermarked video
          </Button>
          <Button variant="outline" onClick={reset}>
            New upload
          </Button>
        </div>
      )}
    </div>
  )
}
