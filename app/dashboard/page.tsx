import type { Metadata } from "next"
import { type RegisteredVideo } from "@/components/dashboard/video-card"
import { DashboardClient } from "@/components/dashboard/dashboard-client"
import { BackendStats } from "@/components/dashboard/backend-stats"

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
    alreadyProtected: true,
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
  return (
    <main className="min-h-[calc(100svh-57px)] bg-background px-4 py-10">
      <div className="mx-auto w-full max-w-4xl">
        <header className="mb-6">
          <p className="text-sm font-medium tracking-widest text-muted-foreground">TRACE</p>
          <h1 className="mt-1 text-2xl font-semibold text-foreground text-balance">Your registered videos</h1>
        </header>

        {/* Backend Analytics Stats */}
        <BackendStats />

        <div className="mt-6">
          <DashboardClient videos={videos} />
        </div>
      </div>
    </main>
  )
}
