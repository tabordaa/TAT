// Mirrors backend/app/schemas/holiday.py (HU-4.6).

/** A public holiday: its date (YYYY-MM-DD) and its name. */
export interface Holiday {
  day: string
  name: string
}
