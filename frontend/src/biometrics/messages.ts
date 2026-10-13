import { ApiError } from "@/api/http";
import type { ChallengeAction, QualityIssue, RejectionReason } from "@/api/types";

export const ACTION_LABELS: Record<ChallengeAction, string> = {
  center: "Pozrite sa priamo do kamery",
  turn_left: "Otočte hlavu doľava",
  turn_right: "Otočte hlavu doprava",
  look_up: "Pozrite sa hore",
  look_down: "Pozrite sa dole",
};

const ACTION_NOUNS: Record<ChallengeAction, string> = {
  center: "pohľad do kamery",
  turn_left: "otočenie hlavy doľava",
  turn_right: "otočenie hlavy doprava",
  look_up: "pohľad hore",
  look_down: "pohľad dole",
};

export const QUALITY_HINTS: Record<QualityIssue, string> = {
  no_face: "Nevidíme vašu tvár",
  multiple_faces: "V zábere je viac ľudí",
  face_too_small: "Podíďte bližšie",
  too_blurry: "Obraz je rozmazaný",
  too_dark: "Je príliš tma",
  too_bright: "Je príliš svetla",
};

const REJECTION_MESSAGES: Record<RejectionReason, string> = {
  quality: "Tvár nebolo dobre vidieť. Skúste lepšie svetlo.",
  passive_spoof: "Vyzerá to na fotografiu alebo obrazovku, nie na živú tvár.",
  active_challenge_failed: "Pohyb hlavy sme nerozpoznali. Skúste to znova.",
  identity_inconsistent: "Počas snímania sa v zábere vymenila osoba.",
  no_match: "Tvár sa nezhoduje s účtom.",
  duplicate_face: "Táto tvár už má účet.",
};

const CODE_MESSAGES: Record<string, string> = {
  network_error: "Server neodpovedá. Skúste to o chvíľu.",
  too_many_requests: "Príliš veľa pokusov. Skúste to neskôr.",
  invalid_challenge: "Snímanie trvalo príliš dlho. Skúste to znova.",
  service_unavailable: "Služba sa práve spúšťa. Skúste to o chvíľu.",
  conflict: "Toto meno je už obsadené.",
  validation_error: "Skontrolujte zadané údaje.",
  payload_too_large: "Snímky sú príliš veľké.",
};

export function describeError(error: unknown): string {
  if (error instanceof ApiError) {
    const reason = error.reason as RejectionReason | undefined;
    const failed = error.details.failed_action as ChallengeAction | undefined;
    if (reason === "active_challenge_failed" && failed && failed in ACTION_NOUNS) {
      return `Nerozpoznali sme ${ACTION_NOUNS[failed]}. Skúste pohyb trochu výraznejšie.`;
    }
    if (reason && reason in REJECTION_MESSAGES) return REJECTION_MESSAGES[reason];
    return CODE_MESSAGES[error.code] ?? error.message;
  }
  return error instanceof Error ? error.message : "Neočakávaná chyba";
}

export function qualityHints(error: unknown): string[] {
  if (!(error instanceof ApiError)) return [];
  const issues = error.details.quality_issues as Partial<Record<QualityIssue, number>> | undefined;
  if (!issues) return [];
  return Object.entries(issues)
    .sort(([, a], [, b]) => (b ?? 0) - (a ?? 0))
    .map(([issue]) => QUALITY_HINTS[issue as QualityIssue])
    .filter(Boolean);
}
