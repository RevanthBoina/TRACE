"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { Bell } from "lucide-react"
import { cn } from "@/lib/utils"

const links = [
  { href: "/", label: "Upload" },
  { href: "/dashboard", label: "Dashboard" },
]

// Unread match alerts surfaced in the nav
const ALERT_COUNT = 6

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
            aria-label={`${ALERT_COUNT} match alerts`}
            className="relative ml-1 rounded-md p-1.5 text-muted-foreground transition-colors hover:text-foreground"
          >
            <Bell className="size-4" aria-hidden="true" />
            {ALERT_COUNT > 0 && (
              <span className="absolute -right-0.5 -top-0.5 flex min-w-4 items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-semibold leading-4 text-white">
                {ALERT_COUNT}
              </span>
            )}
          </Link>
        </div>
      </div>
    </nav>
  )
}
