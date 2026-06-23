"use client"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ShieldCheck, ShieldAlert, ExternalLink, Play, Camera, Briefcase, Music2, Globe, Clock } from "lucide-react"

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

  return (
    <article className="rounded-lg border border-border bg-card p-5">
      <header className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h3 className="truncate text-base font-medium text-card-foreground text-pretty">{video.title}</h3>
          <div className="mt-1 flex items-center gap-1.5 text-sm text-muted-foreground">
            <Icon className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
            <span>{video.platform}</span>
          </div>
        </div>

        {isActive ? (
          <Badge className="shrink-0 gap-1 border-transparent bg-emerald-500/15 text-emerald-400 hover:bg-emerald-500/15">
            <ShieldCheck className="h-3.5 w-3.5" aria-hidden="true" />
            Active
          </Badge>
        ) : (
          <Badge className="shrink-0 gap-1 border-transparent bg-red-500/15 text-red-400 hover:bg-red-500/15">
            <ShieldAlert className="h-3.5 w-3.5" aria-hidden="true" />
            Failed
          </Badge>
        )}
      </header>

      {/* Monitoring meta: last scan, or failure reason when failed */}
      {isActive ? (
        <p className="mt-2 flex items-center gap-1.5 text-xs text-muted-foreground">
          <Clock className="h-3.5 w-3.5" aria-hidden="true" />
          Last scanned {video.lastScanned}
        </p>
      ) : (
        <p className="mt-2 rounded-md bg-red-500/10 px-2.5 py-1.5 text-xs text-red-400">
          {video.failureReason ?? "Monitoring failed. Please re-register this video."}
        </p>
      )}

      <div className="mt-5 border-t border-border pt-4">
        <h4 className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
          Infringing links{" "}
          {video.infringingLinks.length > 0 && (
            <span className="text-red-400">({video.infringingLinks.length})</span>
          )}
        </h4>

        {video.infringingLinks.length === 0 ? (
          <p className="mt-3 text-sm text-muted-foreground">No infringing links detected.</p>
        ) : (
          <ul className="mt-3 flex flex-col gap-2">
            {video.infringingLinks.map((link) => (
              <li
                key={link.id}
                className="flex items-center justify-between gap-3 rounded-md border border-border bg-muted/30 px-3 py-2"
              >
                <div className="min-w-0">
                  <a
                    href={link.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex min-w-0 items-center gap-1.5 text-sm text-foreground hover:underline"
                  >
                    <span className="truncate">{link.url}</span>
                    <ExternalLink className="h-3.5 w-3.5 shrink-0 text-muted-foreground" aria-hidden="true" />
                  </a>
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    <span className="font-medium text-amber-400">{link.confidence}% match</span> · detected{" "}
                    {link.detectedAt}
                  </p>
                </div>
                <Button size="sm" variant="destructive" className="shrink-0" asChild>
                  <a href={DMCA_URL[video.platform]} target="_blank" rel="noopener noreferrer">
                    DMCA
                  </a>
                </Button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </article>
  )
}
