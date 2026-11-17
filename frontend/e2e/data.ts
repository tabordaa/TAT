import { randomInt } from 'node:crypto'

// Realistic people for the records the specs create. Kevin uses the development
// database for the demo, so there is no "test" prefix: what makes each record
// unique is a random document number and email.

const FIRST_NAMES = [
  'Valentina', 'Santiago', 'Mariana', 'Sebastián', 'Daniela', 'Alejandro', 'Camila',
  'Juan Esteban', 'Isabella', 'Mateo', 'Sara', 'Nicolás', 'Paula Andrea', 'Samuel',
  'Luisa Fernanda', 'Felipe', 'Manuela', 'Julián', 'Natalia', 'Carlos Andrés',
]

const LAST_NAMES = [
  'Restrepo', 'Gómez', 'Ramírez', 'Zapata', 'Arango', 'Montoya', 'Vélez', 'Londoño',
  'Henao', 'Castaño', 'Giraldo', 'Ochoa', 'Correa', 'Echeverri', 'Muñoz', 'Rendón',
  'Agudelo', 'Betancur', 'Quintero', 'Salazar',
]

const JOBS: ReadonlyArray<{ position: string; area: string; salary: number }> = [
  { position: 'Analista de nómina', area: 'Talento Humano', salary: 4_200_000 },
  { position: 'Auxiliar contable', area: 'Contabilidad', salary: 2_300_000 },
  { position: 'Desarrolladora de software', area: 'Tecnología', salary: 6_800_000 },
  { position: 'Coordinador de bodega', area: 'Logística', salary: 3_500_000 },
  { position: 'Ejecutiva comercial', area: 'Ventas', salary: 3_900_000 },
  { position: 'Asistente administrativo', area: 'Administración', salary: 2_100_000 },
  { position: 'Analista de compras', area: 'Compras', salary: 3_600_000 },
  { position: 'Técnico de soporte', area: 'Tecnología', salary: 2_900_000 },
]

export interface Person {
  firstNames: string
  lastNames: string
  documentNumber: string
  email: string
  phone: string
  position: string
  area: string
  salary: string
}

function pick<T>(items: ReadonlyArray<T>): T {
  const item = items[randomInt(items.length)]
  if (item === undefined) throw new Error('empty list')
  return item
}

function forEmail(text: string): string {
  return text
    .normalize('NFD')
    .replace(/\p{Diacritic}/gu, '')
    .toLowerCase()
    .replace(/[^a-z]+/g, '')
}

export function randomPerson(): Person {
  const firstNames = pick(FIRST_NAMES)
  const first = pick(LAST_NAMES)
  let second = pick(LAST_NAMES)
  while (second === first) second = pick(LAST_NAMES)
  const job = pick(JOBS)
  // A 10-digit cédula starting with 10 or 11, like the ones issued since 2000.
  const documentNumber = `1${randomInt(0, 2)}${String(randomInt(0, 100_000_000)).padStart(8, '0')}`
  const handle = `${forEmail(firstNames.split(' ')[0] ?? firstNames)}.${forEmail(first)}${randomInt(10, 10_000)}`
  return {
    firstNames,
    lastNames: `${first} ${second}`,
    documentNumber,
    // example.com is reserved (RFC 2606): no mail can ever reach these addresses.
    email: `${handle}@empresa.example.com`,
    phone: `+57 3${randomInt(0, 3)}${randomInt(0, 10)} ${randomInt(100, 1000)} ${randomInt(1000, 10_000)}`,
    position: job.position,
    area: job.area,
    salary: String(job.salary),
  }
}

export function fullName(person: Pick<Person, 'firstNames' | 'lastNames'>): string {
  return `${person.firstNames} ${person.lastNames}`
}

/** A strong password for a test-created account. Never printed. */
export function randomPassword(): string {
  const alphabet = 'abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789'
  return Array.from({ length: 20 }, () => alphabet[randomInt(alphabet.length)]).join('')
}

const bogota = new Intl.DateTimeFormat('en-CA', {
  timeZone: 'America/Bogota',
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
})

/** The business date (Colombia, UTC-5) plus `days`, as YYYY-MM-DD. Same as app.core.clock. */
export function businessDate(days = 0): string {
  const today = bogota.format(new Date()) // "2026-11-17"
  const date = new Date(`${today}T12:00:00Z`)
  date.setUTCDate(date.getUTCDate() + days)
  return date.toISOString().slice(0, 10)
}

/** A future Monday in Colombia, `weeksAhead` weeks from now (1 = the next one). */
export function nextMonday(weeksAhead = 1): string {
  const today = new Date(`${businessDate()}T12:00:00Z`)
  const toMonday = (8 - today.getUTCDay()) % 7 || 7 // Sunday is 0: one day ahead
  return businessDate(toMonday + 7 * (weeksAhead - 1))
}

/** `days` after a "YYYY-MM-DD" date. */
export function addDays(value: string, days: number): string {
  const date = new Date(`${value}T12:00:00Z`)
  date.setUTCDate(date.getUTCDate() + days)
  return date.toISOString().slice(0, 10)
}
