// HU-4.7: the sidebar counters refresh when a page changes vacation requests.
// A DOM event keeps the pages and the layout decoupled: no shared store needed.

const VACATIONS_CHANGED = 'tat:vacations-changed'

/** Call after approving, rejecting, cancelling or marking decisions as seen. */
export function notifyVacationsChanged(): void {
  window.dispatchEvent(new Event(VACATIONS_CHANGED))
}

/** Runs `listener` on every change; returns the function that stops listening. */
export function onVacationsChanged(listener: () => void): () => void {
  window.addEventListener(VACATIONS_CHANGED, listener)
  return () => window.removeEventListener(VACATIONS_CHANGED, listener)
}
