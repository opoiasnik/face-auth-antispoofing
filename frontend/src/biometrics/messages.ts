import { ApiError } from "@/api/http";
import type { ChallengeAction, QualityIssue, RejectionReason } from "@/api/types";

// The preview is mirrored, so "doľava" means the user's own left side –
// this matches the direction they see on screen.
export const ACTION_LABELS: Record<ChallengeAction, { text: string; icon: string }> = {
  center: { text: "Pozerajte priamo do kamery", icon: "●" },
  turn_left: { text: "Pomaly otočte hlavu doľava", icon: "←" },
  turn_right: { text: "Pomaly otočte hlavu doprava", icon: "→" },
  look_up: { text: "Zdvihnite bradu – pozrite sa hore", icon: "↑" },
  look_down: { text: "Skloňte hlavu – pozrite sa dole", icon: "↓" },
};

export const QUALITY_HINTS: Record<QualityIssue, string> = {
  no_face: "Tvár nie je v zábere",
  multiple_faces: "V zábere je viac tvárí",
  face_too_small: "Priblížte sa ku kamere",
  too_blurry: "Obraz je rozmazaný – nehýbte sa a očistite kameru",
  too_dark: "Príliš tma – zlepšite osvetlenie tváre",
  too_bright: "Príliš svetla – vyhnite sa protisvetlu",
};

const REJECTION_MESSAGES: Record<RejectionReason, string> = {
  quality: "Tvár sa nepodarilo zachytiť v dostatočnej kvalite.",
  passive_spoof: "Bol zistený pokus o podvrh (fotografia, displej alebo maska).",
  active_challenge_failed: "Pohyby hlavy nezodpovedali výzve. Skúste to znova a sledujte pokyny.",
  identity_inconsistent: "Počas snímania sa zmenila osoba v zábere.",
  no_match: "Overenie zlyhalo – tvár sa nezhoduje.",
  duplicate_face: "Táto tvár je už zaregistrovaná pod iným účtom.",
};

const CODE_MESSAGES: Record<string, string> = {
  network_error: "Server je nedostupný. Skontrolujte pripojenie.",
  too_many_requests: "Príliš veľa pokusov. Skúste to neskôr.",
  invalid_challenge: "Výzva vypršala alebo už bola použitá. Skúste to znova.",
  service_unavailable: "Biometrická služba je dočasne nedostupná.",
  conflict: "Používateľské meno je už obsadené.",
  validation_error: "Neplatné údaje vo formulári.",
  payload_too_large: "Snímky sú príliš veľké.",
};

export function describeError(error: unknown): string {
  if (error instanceof ApiError) {
    const reason = error.reason as RejectionReason | undefined;
    if (reason && reason in REJECTION_MESSAGES) return REJECTION_MESSAGES[reason];
    return CODE_MESSAGES[error.code] ?? error.message;
  }
  return error instanceof Error ? error.message : "Neočakávaná chyba";
}

/** Quality issues reported with a rejected session, most frequent first. */
export function qualityHints(error: unknown): string[] {
  if (!(error instanceof ApiError)) return [];
  const issues = error.details.quality_issues as Partial<Record<QualityIssue, number>> | undefined;
  if (!issues) return [];
  return Object.entries(issues)
    .sort(([, a], [, b]) => (b ?? 0) - (a ?? 0))
    .map(([issue]) => QUALITY_HINTS[issue as QualityIssue])
    .filter(Boolean);
}
