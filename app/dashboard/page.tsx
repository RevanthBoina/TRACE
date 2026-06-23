import Link from "next/link"
import type { Metadata } from "next"
import { VideoCard, type RegisteredVideo } from "@/components/dashboard/video-card"
import { Button } from "@/components/ui/button"
import { UploadCloud } from "lucide-react"

export const metadata: Metadata = {
  title: "TRACE — Dashboard",
  description: "Monitor your registered videos and act on infringing copies.",
}

const videos: RegisteredVideo[] = [
  {
    id: "1",
    title: "How I Edit My Travel Videos — Full Workflow",
    platform: "YouTube",
    status: "Active",
    lastScanned: "3 hours ago",
    infringingLinks: [
      { id: "a", url: "https://stream-mirror.example/watch/4821", detectedAt: "Jun 20, 2026", confidence: 98 },
      { id: "b", url: "https://freevids.example/v/travel-workflow", detectedAt: "Jun 21, 2026", confidence: 91 },
    ],
  },
  {
    id: "2",
    title: "30 Second Recipe: Garlic Butter Pasta",
    platform: "Instagram",
    status: "Active",
    lastScanned: "1 hour ago",
    infringingLinks: [],
  },
  {
    id: "3",
    title: "Studio Session — Acoustic Cover",
    platform: "YouTube",
    status: "Failed",
    lastScanned: "2 days ago",
    failureReason: "Fingerprint generation failed — source video resolution below 480p.",
    infringingLinks: [
      { id: "c", url: "https://repost-hub.example/clip/9920", detectedAt: "Jun 22, 2026", confidence: 87 },
    ],
  },
  {
    id: "4",
    title: "Behind the Scenes: Product Launch",
    platform: "Instagram",
    status: "Active",
    lastScanned: "20 minutes ago",
    infringingLinks: [
      { id: "d", url: "https://copycat.example/reel/launch", detectedAt: "Jun 19, 2026", confidence: 95 },
      { id: "e", url: "https://mirror-feed.example/p/launch-bts", detectedAt: "Jun 22, 2026", confidence: 82 },
      { id: "f", url: "https://grabber.example/i/8841", detectedAt: "Jun 23, 2026", confidence: 76 },
    ],
  },
]

export default function DashboardPage() {
  const activeCount = videos.filter((v) => v.status === "Active").length
  const infringingCount = videos.reduce((sum, v) => sum + v.infringingLinks.length, 0)

  return (
    <main className="min-h-[calc(100svh-57px)] bg-background px-4 py-10">
      <div className="mx-auto w-full max-w-4xl">
        <header className="mb-8">
          <p className="text-sm font-medium tracking-widest text-muted-foreground">TRACE</p>
          <h1 className="mt-1 text-2xl font-semibold text-foreground text-balance">Your registered videos</h1>
          <div className="mt-3 flex flex-wrap gap-x-6 gap-y-1 text-sm text-muted-foreground">
            <span>
              <span className="font-medium text-foreground">{videos.length}</span> videos monitored
            </span>
            <span>
              <span className="font-medium text-emerald-400">{activeCount}</span> active
            </span>
            <span>
              <span className="font-medium text-red-400">{infringingCount}</span> infringing links found
            </span>
          </div>
        </header>

        {videos.length === 0 ? (
          <div className="flex flex-col items-center justify-center gap-4 rounded-xl border border-dashed border-border bg-muted/20 px-6 py-16 text-center">
            <div className="flex size-12 items-center justify-center rounded-full bg-muted">
              <UploadCloud className="size-6 text-muted-foreground" aria-hidden="true" />
            </div>
            <div className="flex flex-col gap-1">
              <p className="text-sm font-medium text-foreground">No videos registered yet</p>
              <p className="text-sm text-muted-foreground">Upload your first video to start monitoring.</p>
            </div>
            <Button asChild>
              <Link href="/">Upload a video</Link>
            </Button>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            {videos.map((video) => (
              <VideoCard key={video.id} video={video} />
            ))}
          </div>
        )}
      </div>
    </main>
  )
}
