"use client"

import { useEffect, useRef } from "react"

const INACTIVITY_MS = 30 * 60 * 1000 // 30 minutes
const POLL_INTERVAL_MS = 15_000       // poll every 15s while DB is starting
export const QUEUE_KEY = "trace_upload_queue"

async function rdsAction(action: "start" | "stop" | "check") {
    const res = await fetch("/api/rds", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action }),
    })
    return res.json()
}

async function drainQueue() {
    const raw = localStorage.getItem(QUEUE_KEY)
    if (!raw) return
    const queue: { fileName: string; dataUrl: string }[] = JSON.parse(raw)
    if (!queue.length) return

    const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

    for (const item of queue) {
        try {
            const blob = await fetch(item.dataUrl).then((r) => r.blob())
            const form = new FormData()
            form.append("file", blob, item.fileName)
            await fetch(`${API_BASE}/upload`, { method: "POST", body: form })
        } catch {
            // keep in queue on failure — will retry next session
            return
        }
    }
    localStorage.removeItem(QUEUE_KEY)
}

export function RDSProvider() {
    const stopTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
    const pollTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

    function resetInactivityTimer() {
        if (stopTimer.current) clearTimeout(stopTimer.current)
        stopTimer.current = setTimeout(() => {
            rdsAction("stop")
        }, INACTIVITY_MS)
    }

    async function pollUntilReady() {
        const { status } = await rdsAction("check")
        if (status === "available") {
            await drainQueue()
        } else if (status === "starting") {
            pollTimer.current = setTimeout(pollUntilReady, POLL_INTERVAL_MS)
        }
        // stopped / other — do nothing, EventBridge will start it on schedule
    }

    async function init() {
        const { status } = await rdsAction("check")

        if (status === "available") {
            resetInactivityTimer()
            await drainQueue()
            return
        }

        // If there's a queued upload, wake the DB
        const queue = localStorage.getItem(QUEUE_KEY)
        if (queue && JSON.parse(queue).length > 0) {
            if (status === "stopped") await rdsAction("start")
            pollTimer.current = setTimeout(pollUntilReady, POLL_INTERVAL_MS)
        }
    }

    useEffect(() => {
        init()

        const events = ["mousemove", "keydown", "pointerdown", "scroll"]
        events.forEach((e) => window.addEventListener(e, resetInactivityTimer, { passive: true }))

        return () => {
            events.forEach((e) => window.removeEventListener(e, resetInactivityTimer))
            if (stopTimer.current) clearTimeout(stopTimer.current)
            if (pollTimer.current) clearTimeout(pollTimer.current)
        }
    }, [])

    return null
}
