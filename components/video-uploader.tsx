"use client"

import type React from "react"

import { useCallback, useEffect, useRef, useState } from "react"
import { Progress } from "@/components/ui/progress"
import { Button } from "@/components/ui/button"
import { UploadCloud, FileVideo, Download, CheckCircle2, Loader2, AlertCircle, ShieldCheck } from "lucide-react"
import { cn } from "@/lib/utils"
import { trackUploadStarted, trackUploadSuccess, trackWatermarkCompleted, trackDownloadStarted, trackError } from "@/lib/analytics"

// Backend API URL - update this to your deployed EC2/backend URL
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

type Status = "idle" | "uploading" | "processing" | "done" | "already-protected" | "error"

const ACCEPTED = ["video/mp4", "video/quicktime", "video/x-msvideo", "video/x-matroska"]
const ACCEPTED_EXT = [".mp4", ".mov", ".avi", ".mkv"]
const MAX_BYTES = 2 * 1024 * 1024 * 1024 // 2GB

const PROCESSING_STEPS = ["Uploading to server", "Processing watermark", "Finalizing"]

interface UploadResponse {
  job_id: string
  status: string
  message: string
  celery_task_id?: string
}

interface JobStatusResponse {
  job_id: string
  status: string
  progress: number
  output_key?: string
  error?: string
  message: string
}

export function VideoUploader({ onReveal }: { onReveal: () => void }) {
  const [status, setStatus] = useState<Status>("idle")
  const [progress, setProgress] = useState(0)
  const [step, setStep] = useState(0)
  const [fileName, setFileName] = useState<string | null>(null)
  const [isDragging, setIsDragging] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [jobId, setJobId] = useState<string | null>(null)
  const [outputKey, setOutputKey] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null)

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current)
      }
    }
  }, [])

  // Reveal the registration panel when done
  useEffect(() => {
    if (status === "done") onReveal()
  }, [status, onReveal])

  const processingStartRef = useRef<number>(Date.now())

  const pollJobStatus = useCallback(async (id: string) => {
    try {
      const response = await fetch(`${API_BASE_URL}/job/${id}`)
      if (!response.ok) {
        throw new Error("Failed to get job status")
      }
      
      const data: JobStatusResponse = await response.json()
      
      if (data.status === "completed") {
        setStatus("done")
        setOutputKey(data.output_key)
        setProgress(100)
        if (pollIntervalRef.current) {
          clearInterval(pollIntervalRef.current)
        }
        // Track watermark completion
        trackWatermarkCompleted({
          jobId: id,
          processingTimeMs: Date.now() - processingStartRef.current,
          outputSize: 0, // Would need to get from backend
        })
      } else if (data.status === "failed") {
        trackError({
          errorType: "watermark_failed",
          errorMessage: data.error || "Processing failed",
          context: "watermark_processing",
        })
        setStatus("error")
        setError(data.error || "Processing failed")
        if (pollIntervalRef.current) {
          clearInterval(pollIntervalRef.current)
        }
      } else {
        // Still processing
        setProgress(data.progress || 50)
        setStep(1) // Watermarking step
      }
    } catch (err) {
      console.error("Poll error:", err)
    }
  }, [])

  const uploadVideo = useCallback(async (file: File) => {
    setError(null)
    setFileName(file.name)
    setProgress(0)
    setStep(0)
    setStatus("uploading")

    const uploadStartTime = Date.now()
    trackUploadStarted({
      filename: file.name,
      fileSize: file.size,
      fileType: file.type || "unknown",
    })

    const formData = new FormData()
    formData.append("file", file)

    try {
      // Upload to backend
      const uploadResponse = await fetch(`${API_BASE_URL}/upload`, {
        method: "POST",
        body: formData,
      })

      if (!uploadResponse.ok) {
        const errorData = await uploadResponse.json()
        throw new Error(errorData.detail || "Upload failed")
      }

      const data: UploadResponse = await uploadResponse.json()
      
      setJobId(data.job_id)
      setProgress(30)
      setStep(1)

      // Track upload success
      trackUploadSuccess({
        filename: file.name,
        jobId: data.job_id,
        processingTimeMs: Date.now() - uploadStartTime,
      })

      if (data.status === "duplicate") {
        // File already processed
        setStatus("already-protected")
        return
      }

      // Start polling for job status
      setStatus("processing")
      setStep(1)
      
      pollJobStatus(data.job_id)
      pollIntervalRef.current = setInterval(() => {
        pollJobStatus(data.job_id)
      }, 2000) // Poll every 2 seconds

    } catch (err) {
      trackError({
        errorType: "upload_error",
        errorMessage: err instanceof Error ? err.message : "Upload failed",
        context: "video_upload",
      })
      setStatus("error")
      setError(err instanceof Error ? err.message : "Upload failed")
    }
  }, [pollJobStatus])

  const validate = (file: File): string | null => {
    const ext = file.name.slice(file.name.lastIndexOf(".")).toLowerCase()
    const okType = ACCEPTED.includes(file.type) || ACCEPTED_EXT.includes(ext)
    if (!okType) return "Unsupported format. Use MP4, MOV, AVI, or MKV."
    if (file.size > MAX_BYTES) return "File exceeds the 2GB limit."
    return null
  }

  const startUpload = useCallback((file: File) => {
    const validationError = validate(file)
    if (validationError) {
      setError(validationError)
      return
    }
    uploadVideo(file)
  }, [uploadVideo])

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
    setJobId(null)
    setOutputKey(null)
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current)
    }
    if (inputRef.current) inputRef.current.value = ""
  }

  const isProtected = status === "already-protected"
  const isDone = status === "done"
  const isError = status === "error"
  const isProcessing = status === "uploading" || status === "processing"

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
          isProtected && "border-solid border-teal-500/40 bg-teal-500/5",
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
            <div
              className={cn(
                "flex size-10 shrink-0 items-center justify-center rounded-lg bg-muted",
                isProtected && "bg-teal-500/15",
                isDone && "bg-emerald-500/15",
                isError && "bg-red-500/15",
              )}
            >
              {isDone ? (
                <CheckCircle2 className="size-5 text-emerald-400" aria-hidden="true" />
              ) : isProtected ? (
                <ShieldCheck className="size-5 text-teal-400" aria-hidden="true" />
              ) : isError ? (
                <AlertCircle className="size-5 text-red-400" aria-hidden="true" />
              ) : isProcessing ? (
                <Loader2 className="size-5 animate-spin text-muted-foreground" aria-hidden="true" />
              ) : (
                <FileVideo className="size-5 text-muted-foreground" aria-hidden="true" />
              )}
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-foreground">{fileName}</p>
              <p className="text-xs text-muted-foreground">
                {status === "uploading" && "Uploading…"}
                {status === "processing" && `${PROCESSING_STEPS[step]}… ${progress}%`}
                {isDone && "Your watermarked video is ready"}
                {isProtected && "Existing protection found"}
                {isError && "Processing failed"}
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

      {/* Teal info banner for already-protected files */}
      {isProtected && (
        <div className="flex items-start gap-2.5 rounded-lg border border-teal-500/30 bg-teal-500/10 px-4 py-3">
          <ShieldCheck className="mt-0.5 size-4 shrink-0 text-teal-400" aria-hidden="true" />
          <p className="text-sm text-teal-200">
            This video was already protected by TRACE — your watermarked copy is ready.
          </p>
        </div>
      )}

      {/* Progress bar for processing */}
      {isProcessing && (
        <Progress value={progress} className="h-1.5" />
      )}

      {/* Done state - download button */}
      {isDone && (
        <div className="flex items-center gap-2">
          <Button 
            className="flex-1 gap-2" 
            onClick={() => {
              if (outputKey) {
                trackDownloadStarted({ jobId: jobId || "", filename: outputKey })
              }
              onReveal()
            }}
          >
            <Download className="size-4" aria-hidden="true" />
            Download watermarked video
          </Button>
          <Button variant="outline" onClick={reset}>
            New upload
          </Button>
        </div>
      )}

      {/* Already protected state */}
      {isProtected && (
        <div className="flex items-center gap-2">
          <Button className="flex-1 gap-2" variant="outline">
            <Download className="size-4" aria-hidden="true" />
            Download watermarked copy
          </Button>
          <Button variant="ghost" onClick={reset}>
            New upload
          </Button>
        </div>
      )}

      {/* Error state - retry button */}
      {isError && (
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={reset}>
            Try again
          </Button>
        </div>
      )}
    </div>
  )
}
