const dateFormat = new Intl.DateTimeFormat("sk-SK", { dateStyle: "short", timeStyle: "medium" });

export function formatDate(iso: string): string {
  // the backend stores UTC; SQLite drops the offset, so treat naive timestamps as UTC
  const normalized = /[zZ]|[+-]\d\d:\d\d$/.test(iso) ? iso : `${iso}Z`;
  return dateFormat.format(new Date(normalized));
}

export function formatScore(value: number | null | undefined, digits = 3): string {
  return value === null || value === undefined ? "–" : value.toFixed(digits);
}

export const MODE_LABELS: Record<string, string> = {
  enroll: "Registrácia",
  reenroll: "Aktualizácia vzoru",
  verify: "Overenie 1:1",
  identify: "Identifikácia 1:N",
};

export const REASON_LABELS: Record<string, string> = {
  quality: "Nízka kvalita",
  passive_spoof: "Podvrh (pasívna detekcia)",
  active_challenge_failed: "Nesplnená výzva",
  identity_inconsistent: "Zmena osoby",
  no_match: "Nezhoda tváre",
  duplicate_face: "Duplicitná tvár",
  too_many_requests: "Zablokované",
  invalid_challenge: "Neplatná výzva",
  invalid_image: "Neplatný obrázok",
  conflict: "Konflikt",
};
