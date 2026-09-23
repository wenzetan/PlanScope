export function display(value, fallback = "—") {
  if (value === null || value === undefined || value === "") return fallback;
  if (typeof value === "boolean") return value ? "yes" : "no";
  if (Array.isArray(value)) return value.length ? value.join(", ") : fallback;
  return String(value);
}

const SYMBOL = { CNY: "¥", USD: "$" };

export function fmtMoney(amount, currency) {
  if (amount === null || amount === undefined || !currency) return "—";
  const rounded = Math.round(Number(amount) * 100) / 100;
  const symbol = SYMBOL[String(currency).toUpperCase()];
  const body = rounded.toLocaleString("en-US", { maximumFractionDigits: 2 });
  return symbol ? `${symbol}${body}` : `${currency} ${body}`;
}

/** Original-currency price, unchanged by the currency toggle. */
export function money(amount, currency) {
  if (amount === null || amount === undefined) return "—";
  return fmtMoney(amount, currency);
}

/** Backwards-compatible CNY formatter (used where a CNY-only figure is meant). */
export function cny(value) {
  return fmtMoney(value, "CNY");
}

/**
 * Derive the two comparable currencies from an original amount.
 * The original currency is never overwritten: if it is neither CNY nor USD
 * (or no FX rate is available) the missing side stays null.
 */
export function convert(amount, currency, rate) {
  if (amount === null || amount === undefined || !currency) return { cny: null, usd: null };
  const c = String(currency).toUpperCase();
  if (c === "CNY") return { cny: amount, usd: rate ? amount / rate : null };
  if (c === "USD") return { cny: rate ? amount * rate : null, usd: amount };
  return { cny: null, usd: null };
}

export function when(value) {
  if (!value) return "—";
  return String(value).slice(0, 10);
}

export function statusBadge(status) {
  const known = ["active", "beta", "invite_only", "legacy", "deprecated", "discontinued", "unknown",
    "full", "officially_supported", "partial", "unofficial", "unsupported", "unsupported_by_plan"];
  const cls = known.includes(status) ? status : "unknown";
  return { cls, label: (status || "unknown").replace(/_/g, " ") };
}
