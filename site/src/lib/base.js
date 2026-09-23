// Base-path aware links: the site must work under /<repository-name>/
// as well as at the domain root, without hardcoding a hostname.
export const base = (() => {
  const value = import.meta.env.BASE_URL || "/";
  return value.endsWith("/") ? value : `${value}/`;
})();

export function href(path = "") {
  return base + String(path).replace(/^\//, "");
}
