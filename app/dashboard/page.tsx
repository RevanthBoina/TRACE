import type { Metadata } from "next"
import { type RegisteredVideo } from "@/components/dashboard/video-card"
import { DashboardClient } from "@/components/dashboard/dashboard-client"

export const metadata: Metadata = {
  title: "TRACE — Dashboard",
  description: "Monitor your registered videos and act on infringing copies.",
}

export default function DashboardPage() {
  return (
    <main className="min-h-[calc(100svh-57px)] bg-background px-4 py-10">
      <div className="mx-auto w-full max-w-4xl">
        <header className="mb-6">
          <p className="text-sm font-medium tracking-widest text-muted-foreground">TRACE</p>
          <h1 className="mt-1 text-2xl font-semibold text-foreground text-balance">Your registered videos</h1>
        </header>

        <DashboardClient />
      </div>
    </main>
  )
}
