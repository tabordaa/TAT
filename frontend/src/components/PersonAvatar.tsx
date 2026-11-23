import { useState } from 'react'

// White text on each of these meets WCAG AA (4.5:1).
const PALETTE = ['#1d4ed8', '#047857', '#b45309', '#7c3aed', '#be123c', '#0e7490', '#4338ca', '#a21caf'] as const

const SIZES = { xs: 24, sm: 32, md: 36, lg: 64 } as const
export type AvatarSize = keyof typeof SIZES

/** Same person, same color everywhere: derived from the id, which never changes. */
export function avatarColor(id: string): string {
  let hash = 0
  for (const char of id) {
    hash = (hash * 31 + char.charCodeAt(0)) | 0
  }
  return PALETTE[Math.abs(hash) % PALETTE.length] ?? PALETTE[0]
}

/**
 * Initials from a full Spanish name. Most names are "first [second] last [second last]":
 * with 4+ words the first last name is the 3rd word; with 2 or 3, the 2nd.
 */
export function initialsOf(fullName: string): string {
  const words = fullName.trim().split(/\s+/).filter((word) => word !== '')
  const first = words[0]?.charAt(0) ?? ''
  const last = (words.length >= 4 ? words[2] : words[1])?.charAt(0) ?? ''
  return `${first}${last}`.toUpperCase()
}

interface PersonAvatarProps {
  /** Employee id: picks the color and, by default, the photo URL. */
  id: string
  /** Full name ("first names last names"): gives the initials. */
  name: string
  hasPhoto: boolean
  /** When first and last names are known apart, pass the exact initials instead of guessing. */
  initials?: string
  size?: AvatarSize
  /** Overrides the photo URL (an employee sees their own photo through /me). */
  photoUrl?: string
  /** Shows the name on hover; the avatar stays hidden from screen readers either way. */
  showTitle?: boolean
  className?: string
}

/** A person's photo, served by the API, or colored initials if there is none or it fails. */
export function PersonAvatar({
  id,
  name,
  hasPhoto,
  initials,
  size = 'md',
  photoUrl,
  showTitle = false,
  className,
}: PersonAvatarProps) {
  const url = photoUrl ?? `/api/employees/${id}/photo`
  const [failedUrl, setFailedUrl] = useState<string | null>(null)
  const classes = ['avatar', `avatar-${size}`, className].filter(Boolean).join(' ')
  const title = showTitle ? name : undefined

  if (!hasPhoto || failedUrl === url) {
    return (
      <span className={classes} style={{ background: avatarColor(id) }} title={title} aria-hidden="true">
        {initials ?? initialsOf(name)}
      </span>
    )
  }
  return (
    <img
      className={`${classes} avatar-photo`}
      src={url}
      alt=""
      title={title}
      loading="lazy"
      decoding="async"
      onError={() => setFailedUrl(url)}
    />
  )
}
