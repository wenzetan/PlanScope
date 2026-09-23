// Derived build data — NOT a source of truth.
// Produced by `planscope export-site-data` from data/**/*.yaml before the build.
// If missing, the site still builds with an empty dataset (structure first).
import fs from "node:fs";
import path from "node:path";

const EMPTY = {
  generated_at: null,
  site: {
    title: "PlanScope",
    tagline_en: "AI Coding / Token / Agent Plan Intelligence",
    tagline_zh: "AI Coding / Token / Agent 套餐持续追踪与横向对比",
  },
  exchange_rate: { usd_cny: null },
  stats: {
    generated_at: null,
    providers: 0,
    plans: 0,
    models: 0,
    privacy_records: 0,
    community_reports: 0,
    benchmarks: 0,
    usd_cny: null,
  },
  providers: [],
  plans: [],
  models: [],
  privacy: [],
  benchmarks: [],
  community: [],
  changes: [],
  sources: [],
};

function load() {
  const file = path.join(process.cwd(), "src", "generated", "site_data.json");
  try {
    const parsed = JSON.parse(fs.readFileSync(file, "utf8"));
    return { ...EMPTY, ...parsed };
  } catch {
    return EMPTY;
  }
}

export const data = load();
