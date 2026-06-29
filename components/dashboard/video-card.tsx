"use client"

import { Badge } from "@/components/ui/badge"
import { buttonVariants } from "@/components/ui/button"
import { ShieldCheck, ShieldAlert, ExternalLink, Play, Camera, Briefcase, Music2, Globe } from "lucide-react"
import { cn } from "@/lib/utils"

export type Platform = "YouTube" | "Instagram" | "LinkedIn" | "TikTok" | "Other"

export type InfringingLink = {
  id: string
  url: string
  detectedAt: string
  confidence: number
}

export type RegisteredVideo = {
  id: string
  title: string
  platform: Platform
  status: "Active" | "Failed"
  lastScanned: string
  alreadyProtected?: boolean
  failureReason?: string
  infringingLinks: InfringingLink[]
}

const PLATFORM_ICON: Record<Platform, typeof Play> = {
  YouTube: Play,
  Instagram: Camera,
  LinkedIn: Briefcase,
  TikTok: Music2,
  Other: Globe,
}

// Pre-filled takedown destination per platform
const DMCA_URL: Record<Platform, string> = {
  YouTube: "https://www.youtube.com/copyright_complaint_form",
  Instagram: "https://help.instagram.com/contact/372592039493026",
  LinkedIn: "https://www.linkedin.com/help/linkedin/ask/TS-NCEMI",
  TikTok: "https://www.tiktok.com/legal/report/Copyright",
  Other: "https://www.dmca.com/takedowns.aspx",
}

export function VideoCard({ video }: { video: RegisteredVideo }) {
  const isActive = video.status === "Active"
  const Icon = PLATFORM_ICON[video.platform]

  const handleFileDMCA = async (linkId: string, dmcaUrl: string) => {
    try {
      await fetch(`/api/dashboard/dmca/${linkId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          link_id: linkId,
          platform: video.platform,
          dmca_url: dmcaUrl,
        }),
      })
      // Open the external DMCA form in a new tab
      window.open(dmcaUrl, "_blank", "noopener,noreferrer")
    } catch (err) {
      console.error("Failed to record DMCA filing:", err)
    }
  }

  return (
    <article className="flex flex-col gap-4 rounded-lg border border-border bg-card p-5">
      {/* Already-protected banner */}
      {video.alreadyProtected && (
        <div className="flex items-center gap-2 rounded-md border border-teal-500/30 bg-teal-500/10 px-3 py-2 text-xs text-teal-200">
          <ShieldCheck className="size-3.5 shrink-0 text-teal-400" aria-hidden="true" />
          Already protected by TRACE
        </div>
      )}

      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
            <Icon className="size-4" aria-hidden="true" />
            <span>{video.platform}</span>
          </div>
          <p className="mt-1 truncate text-base font-medium text-card-foreground text-pretty">{video.title}</p>
          <p className="mt-0.5 text-xs text-muted-foreground">Last scanned {video.lastScanned}</p>
        </div>

        {isActive ? (
          <Badge className="shrink-0 gap-1 border-transparent bg-emerald-500/15 text-emerald-400 hover:bg-emerald-500/15">
            <ShieldCheck className="size-3.5" aria-hidden="true" />
            Active
          </Badge>
        ) : (
          <Badge className="shrink-0 gap-1 border-transparent bg-red-500/15 text-red-400 hover:bg-red-500/15">
            <ShieldAlert className="size-3.5" aria-hidden="true" />
            Failed
          </Badge>
        )}
      </div>

      {/* Inline infringing links: URL · confidence + date · DMCA */}
      {video.infringingLinks.length > 0 && (
        <ul className="flex flex-col divide-y divide-border border-t border-border">
          {video.infringingLinks.map((link) => (
            <li key={link.id} className="flex items-center gap-3 py-3">
              <a
                href={link.url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex min-w-0 flex-1 items-center gap-1.5 text-sm text-foreground hover:underline"
              >
                <span className="truncate">{link.url}</span>
                <ExternalLink className="size-3.5 shrink-0 text-muted-foreground" aria-hidden="true" />
              </a>
              <div className="shrink-0 text-right text-xs">
                <span className="font-medium text-amber-400">{link.confidence}% match</span>
                <span className="block text-muted-foreground">{link.detectedAt}</span>
              </div>
              <button
                onClick={() => handleFileDMCA(link.id, DMCA_URL[video.platform])}
                className={cn(buttonVariants({ variant: "destructive", size: "sm" }), "shrink-0")}
              >
                File DMCA
              </button>
            </li>
          ))}
        </ul>
      )}

      {/* Failure reason with resubmit affordance */}
      {!isActive && (
        <div className="border-t border-border pt-3">
          <p className="text-xs text-red-400">
            {video.failureReason ?? "Monitoring failed. Please re-register this video."}{" "}
            <button type="button" className="font-medium text-foreground underline underline-offset-2">
              Resubmit link
            </button>
          </p>
        </div>
      )}
    </article>
  )
}
