"use client"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ShieldCheck, ShieldAlert, ExternalLink, Play, Camera } from "lucide-react"

export type InfringingLink = {
  id: string
  url: string
  detectedAt: string
}

export type RegisteredVideo = {
  id: string
  title: string
  platform: "YouTube" | "Instagram"
  status: "Active" | "Failed"
  infringingLinks: InfringingLink[]
}

function PlatformIcon({ platform }: { platform: RegisteredVideo["platform"] }) {
  if (platform === "YouTube") {
    return <Play className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
  }
  return <Camera className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
}

export function VideoCard({ video }: { video: RegisteredVideo }) {
  const isActive = video.status === "Active"

  return (
    <article className="rounded-lg border border-border bg-card p-5">
      <header className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h3 className="truncate text-base font-medium text-card-foreground text-pretty">{video.title}</h3>
          <div className="mt-1 flex items-center gap-1.5 text-sm text-muted-foreground">
            <PlatformIcon platform={video.platform} />
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
                <a
                  href={link.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex min-w-0 items-center gap-1.5 text-sm text-foreground hover:underline"
                >
                  <span className="truncate">{link.url}</span>
                  <ExternalLink className="h-3.5 w-3.5 shrink-0 text-muted-foreground" aria-hidden="true" />
                </a>
                <Button size="sm" variant="destructive" className="shrink-0">
                  DMCA
                </Button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </article>
  )
}
