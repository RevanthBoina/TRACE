"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { Bell } from "lucide-react"
import { cn } from "@/lib/utils"

const links = [
  { href: "/", label: "Upload" },
  { href: "/dashboard", label: "Dashboard" },
]

// Whether there are unread infringement matches
const HAS_UNREAD_MATCHES = true

export function SiteNav() {
  const pathname = usePathname()

  return (
    <nav className="sticky top-0 z-10 border-b border-border bg-background/80 backdrop-blur">
      <div className="mx-auto flex w-full max-w-4xl items-center justify-between px-4 py-3">
        <Link href="/" className="text-sm font-semibold tracking-[0.2em] text-foreground">
          TRACE
        </Link>
        <div className="flex items-center gap-1">
          {links.map(({ href, label }) => (
            <Link
              key={href}
              href={href}
              className={cn(
                "rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
                pathname === href
                  ? "bg-secondary text-foreground"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              {label}
            </Link>
          ))}
          <Link
            href="/dashboard"
            aria-label={HAS_UNREAD_MATCHES ? "Unread infringement matches" : "Notifications"}
            className="relative ml-1 rounded-md p-1.5 text-muted-foreground transition-colors hover:text-foreground"
          >
            <Bell className="size-4" aria-hidden="true" />
            {HAS_UNREAD_MATCHES && (
              <span className="absolute right-1 top-1 size-2 rounded-full bg-red-500 ring-2 ring-background" />
            )}
          </Link>
        </div>
      </div>
    </nav>
  )
}
