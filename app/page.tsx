"use client"

import { useState } from "react"
import { VideoUploader } from "@/components/video-uploader"
import { RegistrationPanel } from "@/components/registration-panel"

export default function Home() {
  const [registered, setRegistered] = useState(false)

  return (
    <main className="flex min-h-[calc(100svh-57px)] items-center justify-center px-4 py-12 font-sans">
      <div className="flex w-full max-w-md flex-col gap-8">
        <header className="flex flex-col gap-1">
          <span className="text-xs font-medium uppercase tracking-[0.2em] text-muted-foreground">Trace</span>
          <h1 className="text-balance text-2xl font-semibold tracking-tight text-foreground">Upload a video</h1>
          <p className="text-pretty text-sm text-muted-foreground">
            Drop a file to watermark and fingerprint it, then register where it lives to start monitoring.
          </p>
        </header>

        <VideoUploader onDownloaded={() => setRegistered(true)} />

        {registered && (
          <>
            <div className="h-px bg-border" aria-hidden="true" />
            <RegistrationPanel />
          </>
        )}
      </div>
    </main>
  )
}
