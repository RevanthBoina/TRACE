"use client"

import { useEffect, useState } from "react"
import { Activity, Upload, CheckCircle2, XCircle, Clock } from "lucide-react"

interface BackendMetrics {
  uptime_seconds: number
  uptime_human: string
  trace_upload_requests_total: number
  trace_upload_duplicates_total: number
  trace_upload_bytes_total: number
  trace_upload_s3_success_total: number
  trace_upload_s3_errors_total: number
  trace_celery_tasks_created_total: number
  trace_celery_tasks_failed_total: number
  trace_watermark_completed_total: number
  trace_watermark_failed_total: number
  trace_job_status_requests_total: number
  trace_upload_duration_ms_avg: number
  trace_upload_duration_ms_count: number
}

export function BackendStats() {
  const [metrics, setMetrics] = useState<BackendMetrics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/metrics`)
        if (!response.ok) throw new Error("Failed to fetch metrics")
        const data = await response.json()
        setMetrics(data)
        setError(null)
      } catch (err) {
        setError("Unable to connect to backend")
      } finally {
        setLoading(false)
      }
    }

    fetchMetrics()
    // Refresh every 30 seconds
    const interval = setInterval(fetchMetrics, 30000)
    return () => clearInterval(interval)
  }, [])

  if (loading) {
    return (
      <div className="rounded-lg border border-border bg-card p-4">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Activity className="h-4 w-4 animate-pulse" />
          Connecting to backend...
        </div>
      </div>
    )
  }

  if (error || !metrics) {
    return (
      <div className="rounded-lg border border-border bg-card p-4">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Activity className="h-4 w-4" />
          Backend: <span className="text-red-400">Offline</span>
        </div>
      </div>
    )
  }

  const successRate = metrics.trace_upload_requests_total > 0
    ? Math.round((metrics.trace_watermark_completed_total / metrics.trace_upload_requests_total) * 100)
    : 0

  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Activity className="h-4 w-4 text-emerald-500" />
          <span className="text-sm font-medium">Backend Status</span>
        </div>
        <span className="text-xs text-muted-foreground">
          Uptime: {metrics.uptime_human}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatCard
          icon={<Upload className="h-4 w-4" />}
          label="Total Uploads"
          value={metrics.trace_upload_requests_total || 0}
        />
        <StatCard
          icon={<CheckCircle2 className="h-4 w-4" />}
          label="Completed"
          value={metrics.trace_watermark_completed_total || 0}
          highlight
        />
        <StatCard
          icon={<XCircle className="h-4 w-4" />}
          label="Failed"
          value={metrics.trace_watermark_failed_total || 0}
          highlight="red"
        />
        <StatCard
          icon={<Clock className="h-4 w-4" />}
          label="Avg Time"
          value={metrics.trace_upload_duration_ms_avg 
            ? `${Math.round(metrics.trace_upload_duration_ms_avg)}ms` 
            : "N/A"}
        />
      </div>

      {metrics.trace_upload_requests_total > 0 && (
        <div className="mt-4">
          <div className="flex items-center justify-between text-xs text-muted-foreground mb-1">
            <span>Success Rate</span>
            <span>{successRate}%</span>
          </div>
          <div className="h-2 w-full rounded-full bg-muted">
            <div 
              className="h-2 rounded-full bg-emerald-500 transition-all"
              style={{ width: `${successRate}%` }}
            />
          </div>
        </div>
      )}
    </div>
  )
}

function StatCard({ 
  icon, 
  label, 
  value, 
  highlight,
  highlightColor = "emerald"
}: { 
  icon: React.ReactNode
  label: string
  value: number | string
  highlight?: boolean
  highlightColor?: "emerald" | "red"
}) {
  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center gap-1.5 text-muted-foreground">
        {icon}
        <span className="text-xs">{label}</span>
      </div>
      <span className={`text-lg font-semibold ${
        highlight 
          ? highlightColor === "red" ? "text-red-400" : "text-emerald-400"
          : "text-foreground"
      }`}>
        {value}
      </span>
    </div>
  )
}
