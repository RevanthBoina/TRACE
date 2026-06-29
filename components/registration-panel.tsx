"use client"

import type React from "react"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

export function RegistrationPanel() {
  const [link, setLink] = useState("")
  const [platform, setPlatform] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)
  const router = useRouter()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!link || !platform) {
      setError("Please enter a link and select a platform")
      return
    }
    setError(null)
    setLoading(true)
    try {
      const res = await fetch("/api/dashboard/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ link, platform }),
      })
      if (!res.ok) throw new Error("Failed to register")
      setSuccess(true)
      setLink("")
      setPlatform("")
      // Refresh the dashboard
      router.refresh()
      // Hide success message after 3 seconds
      setTimeout(() => setSuccess(false), 3000)
    } catch (err) {
      setError("Failed to register link. Please try again.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="flex flex-col gap-4 rounded-xl border border-border bg-muted/20 p-5"
    >
      <div className="flex flex-col gap-1">
        <h2 className="text-sm font-medium text-foreground">Register a link</h2>
        <p className="text-xs text-muted-foreground">Add an existing video from a supported platform.</p>
      </div>

      {success && (
        <p className="text-sm text-emerald-400">Link registered successfully!</p>
      )}

      {error && (
        <p className="text-sm text-red-400">{error}</p>
      )}

      <div className="flex flex-col gap-2">
        <Label htmlFor="video-link" className="sr-only">
          Video link
        </Label>
        <Input
          id="video-link"
          type="url"
          value={link}
          onChange={(e) => setLink(e.target.value)}
          placeholder="Paste your YouTube or Instagram link here"
          disabled={loading}
        />
      </div>

      <div className="flex flex-col gap-2 sm:flex-row">
        <Select value={platform} onValueChange={setPlatform} disabled={loading}>
          <SelectTrigger className="sm:w-44">
            <SelectValue placeholder="Select platform" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="youtube">YouTube</SelectItem>
            <SelectItem value="instagram">Instagram</SelectItem>
            <SelectItem value="linkedin">LinkedIn</SelectItem>
            <SelectItem value="tiktok">TikTok</SelectItem>
            <SelectItem value="other">Other</SelectItem>
          </SelectContent>
        </Select>
        <Button type="submit" className="flex-1" disabled={loading}>
          {loading ? "Registering..." : "Register"}
        </Button>
      </div>
    </form>
  )
}
