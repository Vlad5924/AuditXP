// Форматирование чисел, дат и сумм для интерфейса
const nf = new Intl.NumberFormat("ru-RU");

export function formatNumber(value: number): string {
  return nf.format(value).replace(/\u00a0/g, " ");
}

export function formatMoney(value: number, short = false): string {
  if (short && Math.abs(value) >= 1_000_000) {
    return `${(value / 1_000_000).toFixed(1).replace(".", ",")} млн BYN`;
  }
  if (short && Math.abs(value) >= 1_000) {
    return `${Math.round(value / 1_000)} тыс. BYN`;
  }
  const text = new Intl.NumberFormat("ru-RU", {
    minimumFractionDigits: 2, maximumFractionDigits: 2,
  }).format(value);
  return `${text.replace(/\u00a0/g, " ")} BYN`;
}

export function formatScore(value: number): string {
  return value.toFixed(2).replace(".", ",");
}

function parse(value: string): Date {
  return new Date(/[zZ+]/.test(value.slice(10)) ? value : `${value}Z`);
}

export function formatDate(value: string | null): string {
  if (!value) return "–";
  const [y, m, d] = value.slice(0, 10).split("-");
  return `${d}.${m}.${y}`;
}

export function formatDateTime(value: string | null, utc = true): string {
  if (!value) return "–";
  const date = utc ? parse(value) : new Date(value);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(date.getDate())}.${pad(date.getMonth() + 1)}.` +
    `${date.getFullYear()} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

const MONTHS = ["январь", "февраль", "март", "апрель", "май", "июнь", "июль",
  "август", "сентябрь", "октябрь", "ноябрь", "декабрь"];

export function monthTitle(isoDate: string): string {
  const [y, m] = isoDate.split("-").map(Number);
  return `${MONTHS[m - 1]} ${y}`;
}

export function monthPeriod(year: number, month: number) {
  const last = new Date(Date.UTC(year, month, 0)).getUTCDate();
  const mm = String(month).padStart(2, "0");
  return { date_from: `${year}-${mm}-01`, date_to: `${year}-${mm}-${last}` };
}

export function initials(fullName: string): string {
  const [last = "", first = ""] = fullName.split(/\s+/);
  return (first.charAt(0) + last.charAt(0)).toUpperCase();
}
