export interface SkeletonLineProps {
  width?: string
  height?: string
  className?: string
}

export function SkeletonLine({ width = '100%', height, className }: SkeletonLineProps) {
  return (
    <span
      className={className !== undefined ? `skeleton-line ${className}` : 'skeleton-line'}
      style={{ width, height }}
      aria-hidden="true"
    />
  )
}

const HEADER_WIDTHS = ['58%', '48%', '64%', '46%', '54%', '50%', '42%']
const CELL_WIDTHS = ['78%', '62%', '86%', '54%', '70%', '66%', '48%']

function pickWidth(widths: readonly string[], index: number): string {
  return widths[index % widths.length] ?? '70%'
}

export interface SkeletonTableProps {
  rows?: number
  columns: number
  label?: string
}

export function SkeletonTable({ rows = 5, columns, label = 'Cargando…' }: SkeletonTableProps) {
  return (
    <div className="table-wrap skeleton-status" role="status">
      <span className="sr-only">{label}</span>
      <table className="table skeleton-table" aria-hidden="true">
        <thead>
          <tr>
            {Array.from({ length: columns }, (_, colIndex) => (
              <th key={colIndex} scope="col">
                <SkeletonLine width={pickWidth(HEADER_WIDTHS, colIndex)} height="0.72rem" />
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {Array.from({ length: rows }, (_, rowIndex) => (
            <tr key={rowIndex}>
              {Array.from({ length: columns }, (_, colIndex) => (
                <td key={colIndex}>
                  <SkeletonLine
                    width={pickWidth(CELL_WIDTHS, rowIndex * 3 + colIndex)}
                    height="0.95rem"
                  />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

const CARD_LINE_WIDTHS = ['92%', '78%', '85%', '64%', '88%', '72%', '80%']

export type SkeletonCardVariant = 'lines' | 'detail' | 'balance' | 'stat' | 'calendar' | 'header'

export interface SkeletonCardProps {
  lines?: number
  label?: string
  /** Omits outer card chrome when placed inside an existing card container. */
  bare?: boolean
  variant?: SkeletonCardVariant
  className?: string
}

function SkeletonCardContent({ variant, lines }: { variant: SkeletonCardVariant; lines: number }) {
  if (variant === 'header') {
    return (
      <div className="detail-header" aria-hidden="true">
        <span className="skeleton-circle" />
        <div className="detail-header-text skeleton-header-text">
          <SkeletonLine width="min(16rem, 75%)" height="1.65rem" />
          <SkeletonLine width="min(12rem, 55%)" height="0.95rem" />
        </div>
      </div>
    )
  }

  if (variant === 'stat') {
    return (
      <>
        <span className="skeleton-icon" aria-hidden="true" />
        <div className="skeleton-stat-body" aria-hidden="true">
          <SkeletonLine width="min(9.5rem, 80%)" height="0.82rem" />
          <SkeletonLine width="4.25rem" height="1.85rem" />
        </div>
      </>
    )
  }

  if (variant === 'balance') {
    return (
      <div className="skeleton-stack" aria-hidden="true">
        <SkeletonLine width="min(12rem, 65%)" height="2rem" />
        <div className="detail-grid">
          {Array.from({ length: 4 }, (_, index) => (
            <div key={index} className="detail-item skeleton-item">
              <SkeletonLine width={pickWidth(HEADER_WIDTHS, index)} height="0.72rem" />
              <SkeletonLine width="3.5rem" height="1rem" />
            </div>
          ))}
        </div>
        <SkeletonLine width="min(26rem, 90%)" height="0.82rem" />
      </div>
    )
  }

  if (variant === 'detail') {
    return (
      <div className="skeleton-stack" aria-hidden="true">
        <SkeletonLine width="9.5rem" height="0.75rem" />
        <div className="detail-grid">
          {Array.from({ length: lines }, (_, index) => (
            <div key={index} className="detail-item skeleton-item">
              <SkeletonLine width={pickWidth(HEADER_WIDTHS, index)} height="0.72rem" />
              <SkeletonLine width={pickWidth(CARD_LINE_WIDTHS, index)} height="1rem" />
            </div>
          ))}
        </div>
      </div>
    )
  }

  if (variant === 'calendar') {
    return (
      <div className="skeleton-stack" aria-hidden="true">
        <div className="calendar">
          <div className="calendar-row">
            {Array.from({ length: 7 }, (_, index) => (
              <div key={index} className="calendar-weekday">
                <SkeletonLine width="2rem" height="0.72rem" className="skeleton-center" />
              </div>
            ))}
          </div>
          <div className="calendar-days">
            {Array.from({ length: 35 }, (_, index) => (
              <div key={index} className="skeleton-calendar-day" />
            ))}
          </div>
        </div>
        <SkeletonLine width="min(32rem, 95%)" height="0.82rem" />
        <SkeletonLine width="9rem" height="0.75rem" />
        <SkeletonLine width="min(20rem, 75%)" height="0.95rem" />
      </div>
    )
  }

  return (
    <div className="skeleton-stack" aria-hidden="true">
      <SkeletonLine width="42%" height="1.05rem" />
      {Array.from({ length: lines }, (_, index) => (
        <SkeletonLine key={index} width={pickWidth(CARD_LINE_WIDTHS, index)} height="0.92rem" />
      ))}
    </div>
  )
}

export function SkeletonCard({
  lines = 4,
  label,
  bare = false,
  variant = 'lines',
  className,
}: SkeletonCardProps) {
  const baseClass =
    bare || variant === 'header'
      ? ''
      : variant === 'stat'
        ? 'card stat-card'
        : variant === 'detail' || variant === 'balance'
          ? 'card detail-section'
          : 'card'

  const classes = [baseClass, label !== undefined ? 'skeleton-status' : '', className ?? '']
    .filter((part) => part !== '')
    .join(' ')

  return (
    <div
      className={classes || undefined}
      role={label !== undefined ? 'status' : undefined}
      aria-hidden={label === undefined ? true : undefined}
    >
      {label !== undefined && <span className="sr-only">{label}</span>}
      <SkeletonCardContent variant={variant} lines={lines} />
    </div>
  )
}
