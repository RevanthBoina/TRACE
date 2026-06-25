"use client"

import { useMemo, useState } from "react"
import Link from "next/link"
import { VideoCard, type RegisteredVideo } from "@/components/dashboard/video-card"
import { buttonVariants } from "@/components/ui/button"
import { UploadCloud } from "lucide-react"
import { cn } from "@/lib/utils"

type Filter = "All" | "Active" | "Matches" | "Failed"

const FILTERS: Filter[] = ["All", "Active", "Matches", "Failed"]

export function DashboardClient({ videos }: { videos: RegisteredVideo[] }) {
  const [filter, setFilter] = useState<Filter>("All")

  const activeCount = videos.filter((v) => v.status === "Active").length
  const infringingCount = videos.reduce((sum, v) => sum + v.infringingLinks.length, 0)

  const filtered = useMemo(() => {
    switch (filter) {
      case "Active":
        return videos.filter((v) => v.status === "Active")
      case "Matches":
        return videos.filter((v) => v.infringingLinks.length > 0)
      case "Failed":
        return videos.filter((v) => v.status === "Failed")
      default:
        return videos
    }
  }, [videos, filter])

  const metrics = [
    { label: "Videos monitored", value: videos.length, tone: "text-foreground" },
    { label: "Active", value: activeCount, tone: "text-emerald-400" },
    { label: "Infringing copies", value: infringingCount, tone: "text-red-400" },
  ]

  return (
    <div className="flex flex-col gap-6">
      {/* Metric cards */}
      <div className="grid grid-cols-3 gap-3">
        {metrics.map((m) => (
          <div key={m.label} className="rounded-lg border border-border bg-card p-4">
            <p className={cn("text-2xl font-semibold tabular-nums", m.tone)}>{m.value}</p>
            <p className="mt-1 text-xs text-muted-foreground">{m.label}</p>
          </div>
        ))}
      </div>

      {/* Filter pills */}
      <div className="flex flex-wrap gap-2">
        {FILTERS.map((f) => (
          <button
            key={f}
            type="button"
            onClick={() => setFilter(f)}
            className={cn(
              "rounded-full px-3.5 py-1.5 text-sm font-medium transition-colors",
              filter === f
                ? "bg-foreground text-background"
                : "bg-secondary text-muted-foreground hover:text-foreground",
            )}
          >
            {f}
          </button>
        ))}
      </div>

      {filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center gap-4 rounded-xl border border-dashed border-border bg-muted/20 px-6 py-16 text-center">
          <div className="flex size-12 items-center justify-center rounded-full bg-muted">
            <UploadCloud className="size-6 text-muted-foreground" aria-hidden="true" />
          </div>
          <div className="flex flex-col gap-1">
            <p className="text-sm font-medium text-foreground">Nothing here yet</p>
            <p className="text-sm text-muted-foreground">No videos match this filter.</p>
          </div>
          <Link href="/" className={buttonVariants()}>
            Upload a video
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {filtered.map((video) => (
            <VideoCard key={video.id} video={video} />
          ))}
        </div>
      )}
    </div>
  )
}
