import { VideoCard, type RegisteredVideo } from "@/components/dashboard/video-card"

const videos: RegisteredVideo[] = [
  {
    id: "1",
    title: "How I Edit My Travel Videos — Full Workflow",
    platform: "YouTube",
    status: "Active",
    infringingLinks: [
      { id: "a", url: "https://stream-mirror.example/watch/4821", detectedAt: "2026-06-20" },
      { id: "b", url: "https://freevids.example/v/travel-workflow", detectedAt: "2026-06-21" },
    ],
  },
  {
    id: "2",
    title: "30 Second Recipe: Garlic Butter Pasta",
    platform: "Instagram",
    status: "Active",
    infringingLinks: [],
  },
  {
    id: "3",
    title: "Studio Session — Acoustic Cover",
    platform: "YouTube",
    status: "Failed",
    infringingLinks: [{ id: "c", url: "https://repost-hub.example/clip/9920", detectedAt: "2026-06-22" }],
  },
  {
    id: "4",
    title: "Behind the Scenes: Product Launch",
    platform: "Instagram",
    status: "Active",
    infringingLinks: [
      { id: "d", url: "https://copycat.example/reel/launch", detectedAt: "2026-06-19" },
      { id: "e", url: "https://mirror-feed.example/p/launch-bts", detectedAt: "2026-06-22" },
      { id: "f", url: "https://grabber.example/i/8841", detectedAt: "2026-06-23" },
    ],
  },
]

export default function DashboardPage() {
  const activeCount = videos.filter((v) => v.status === "Active").length
  const infringingCount = videos.reduce((sum, v) => sum + v.infringingLinks.length, 0)

  return (
    <main className="min-h-svh bg-background px-4 py-10">
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

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {videos.map((video) => (
            <VideoCard key={video.id} video={video} />
          ))}
        </div>
      </div>
    </main>
  )
}
