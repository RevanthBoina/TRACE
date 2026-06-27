import type { Metadata } from "next"
import { DashboardClient } from "@/components/dashboard/dashboard-client"
import { BackendStats } from "@/components/dashboard/backend-stats"
import type { RegisteredVideo } from "@/components/dashboard/video-card"

export const metadata: Metadata = {
  title: "TRACE — Dashboard",
  description: "Monitor your registered videos and act on infringing copies.",
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

async function getVideos(): Promise<RegisteredVideo[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/dashboard`, { next: { revalidate: 30 } })
    if (!res.ok) return []
    const data = await res.json()
    return data.map((v: {
      id: string
      title: string
      platform: string
      status: string
      last_scanned: string | null
      failure_reason: string | null
      infringing_links: { id: string; url: string; confidence: number; detected_at: string; dmca_filed: boolean }[]
    }) => ({
      id: v.id,
      title: v.title,
      platform: v.platform,
      status: v.status === "active" ? "Active" : "Failed",
      lastScanned: v.last_scanned ? new Date(v.last_scanned).toLocaleString() : "Never",
      failureReason: v.failure_reason ?? undefined,
      infringingLinks: v.infringing_links.map((l) => ({
        id: l.id,
        url: l.url,
        confidence: l.confidence,
        detectedAt: new Date(l.detected_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }),
        dmcaFiled: l.dmca_filed,
      })),
    }))
  } catch {
    return []
  }
}

export default async function DashboardPage() {
  const videos = await getVideos()

  return (
    <main className="min-h-[calc(100svh-57px)] bg-background px-4 py-10">
      <div className="mx-auto w-full max-w-4xl">
        <header className="mb-6">
          <p className="text-sm font-medium tracking-widest text-muted-foreground">TRACE</p>
          <h1 className="mt-1 text-2xl font-semibold text-foreground text-balance">Infringement Detection Dashboard</h1>
          <p className="mt-1 text-sm text-muted-foreground">Monitor your registered videos and act on infringing copies.</p>
        </header>

        <BackendStats />

        <div className="mt-6">
          <DashboardClient videos={videos} />
        </div>
      </div>
    </main>
  )
}
