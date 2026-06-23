"use client"

import type React from "react"

import { useState } from "react"
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

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    console.log("[v0] Registering link:", { link, platform })
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
        />
      </div>

      <div className="flex flex-col gap-2 sm:flex-row">
        <Select value={platform} onValueChange={setPlatform}>
          <SelectTrigger className="sm:w-44">
            <SelectValue placeholder="Select platform" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="youtube">YouTube</SelectItem>
            <SelectItem value="instagram">Instagram</SelectItem>
          </SelectContent>
        </Select>
        <Button type="submit" className="flex-1">
          Register
        </Button>
      </div>
    </form>
  )
}
