import { useEffect, useState } from 'react'

/**
 * Returns `value` only after it has stopped changing for `delayMs`.
 * Typing "ana" fires three changes but only the last one is published,
 * so the API gets one request instead of three.
 */
export function useDebouncedValue<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value)

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delayMs)
    // A new change (or unmount) cancels the pending update.
    return () => clearTimeout(timer)
  }, [value, delayMs])

  return debounced
}
