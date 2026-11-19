import { api } from './client'
import type { Holiday } from '../types/holiday'

/** GET /holidays?year= (any session): the holidays of a year, ordered by date. */
export async function getHolidays(year: number, signal?: AbortSignal): Promise<Holiday[]> {
  const { data } = await api.get<Holiday[]>('/holidays', { params: { year }, signal })
  return data
}

/** Holidays of several years in one map, day → name. */
export async function getHolidayMap(
  years: number[],
  signal?: AbortSignal,
): Promise<Map<string, string>> {
  const lists = await Promise.all(years.map((year) => getHolidays(year, signal)))
  return new Map(lists.flat().map((holiday) => [holiday.day, holiday.name]))
}

/** POST /holidays (ADMIN). */
export async function addHoliday(holiday: Holiday): Promise<Holiday> {
  const { data } = await api.post<Holiday>('/holidays', holiday)
  return data
}

/** DELETE /holidays/{day} (ADMIN). */
export async function removeHoliday(day: string): Promise<void> {
  await api.delete(`/holidays/${encodeURIComponent(day)}`)
}
