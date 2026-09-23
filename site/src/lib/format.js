export function display(value, fallback = "—") {
  if (value === null || value === undefined || value === "") return fallback;
  if (typeof value === "boolean") return value ? "yes" : "no";
  if (Array.isArray(value)) return value.length ? value.join(", ") : fallback;
  return String(value);
}

export function money(amount, currency) {
  if (amount === null || amount === undefined) return "—";
  return `${currency ?? "?"} ${amount}`;
}

export function cny(value) {
  if (value === null || value === undefined) return "—";
  const rounded = Math.round(value * 100) / 100;
  return `¥${rounded.toLocaleString("en-US")}`;
}

export function when(value) {
  if (!value) return "—";
  return String(value).slice(0, 10);
}

export function statusBadge(status) {
  const known = ["active", "beta", "invite_only", "deprecated", "discontinued", "unknown"];
  const cls = known.includes(status) ? status : "unknown";
  return { cls, label: (status || "unknown").replace(/_/g, " ") };
}
