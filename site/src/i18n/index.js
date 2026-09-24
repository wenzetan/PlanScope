// Standard i18n: flat `key -> string` dictionaries, one namespace per page.
//
// Conventions:
//   - `zh` is the default language and the fallback for any missing key.
//   - Values may contain inline HTML (rendered with set:html by <T />).
//   - Placeholders use `{name}` and are filled from the `vars` argument.
//   - Attribute/option strings must stay plain text (no HTML).
//   - Currency-dependent labels use the `<key>.cny` / `<key>.usd` suffix pair
//     and are rendered by <Cur />; never hardcode a currency in a label.
import commonZh from "./zh/common.json";
import homeZh from "./zh/home.json";
import plansZh from "./zh/plans.json";
import pricingZh from "./zh/pricing.json";
import modelsZh from "./zh/models.json";
import windowsZh from "./zh/windows.json";
import providersZh from "./zh/providers.json";
import privacyZh from "./zh/privacy.json";
import reliabilityZh from "./zh/reliability.json";
import changesZh from "./zh/changes.json";
import sourcesZh from "./zh/sources.json";
import methodologyZh from "./zh/methodology.json";

import commonEn from "./en/common.json";
import homeEn from "./en/home.json";
import plansEn from "./en/plans.json";
import pricingEn from "./en/pricing.json";
import modelsEn from "./en/models.json";
import windowsEn from "./en/windows.json";
import providersEn from "./en/providers.json";
import privacyEn from "./en/privacy.json";
import reliabilityEn from "./en/reliability.json";
import changesEn from "./en/changes.json";
import sourcesEn from "./en/sources.json";
import methodologyEn from "./en/methodology.json";

export const dictionaries = {
  zh: {
    ...commonZh,
    ...homeZh,
    ...plansZh,
    ...pricingZh,
    ...modelsZh,
    ...windowsZh,
    ...providersZh,
    ...privacyZh,
    ...reliabilityZh,
    ...changesZh,
    ...sourcesZh,
    ...methodologyZh,
  },
  en: {
    ...commonEn,
    ...homeEn,
    ...plansEn,
    ...pricingEn,
    ...modelsEn,
    ...windowsEn,
    ...providersEn,
    ...privacyEn,
    ...reliabilityEn,
    ...changesEn,
    ...sourcesEn,
    ...methodologyEn,
  },
};

export const LANGS = ["zh", "en"];
export const DEFAULT_LANG = "zh";
export const DEFAULT_CURRENCY = { zh: "cny", en: "usd" };

function interpolate(value, vars) {
  if (!vars) return value;
  return String(value).replace(/\{(\w+)\}/g, (match, name) =>
    vars[name] === undefined || vars[name] === null ? match : String(vars[name])
  );
}

/** Translate `key` into `lang`, falling back to the default language. */
export function t(lang, key, vars) {
  const dict = dictionaries[lang] || dictionaries[DEFAULT_LANG];
  let value = dict[key];
  if (value === undefined || value === null) value = dictionaries[DEFAULT_LANG][key];
  if (value === undefined || value === null) return key;
  return interpolate(value, vars);
}
