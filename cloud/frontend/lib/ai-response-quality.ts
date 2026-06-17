export type ReviewMode =
  | "standard"
  | "accuracy"
  | "red_team"
  | "ceo"
  | "technical"
  | "legal";

export interface ResponseQuality {
  facts?: string[];
  assumptions?: string[];
  unknowns?: string[];
  confidence_score?: number;
  evidence?: string[];
  risks?: string[];
  counterarguments?: string[];
  recommendation?: string;
  tradeoffs?: string[];
  what_would_change_recommendation?: string[];
}

export const RESPONSE_QUALITY_SECTIONS = [
  "Facts",
  "Assumptions",
  "Unknowns",
  "Confidence score",
  "Evidence / citations",
  "Risks",
  "Counterarguments",
  "Recommendation",
  "Tradeoffs",
  "What would change the recommendation",
] as const;

export const REVIEW_MODES: { id: ReviewMode; label: string }[] = [
  { id: "standard", label: "Standard Answer" },
  { id: "accuracy", label: "Accuracy Mode" },
  { id: "red_team", label: "Red Team Mode" },
  { id: "ceo", label: "CEO Review Mode" },
  { id: "technical", label: "Technical Review Mode" },
  { id: "legal", label: "Legal Risk Review Mode" },
];

export function modeTitle(mode: ReviewMode): string {
  if (mode === "standard") return "Standard answer";
  if (mode === "red_team") return "Hostile red-team review";
  if (mode === "ceo") return "Executive decision memo";
  if (mode === "technical") return "Technical review";
  if (mode === "legal") return "Legal risk review";
  return "Evidence-based answer";
}

export function formatConfidence(value?: number): string {
  if (typeof value !== "number") return "not provided";
  return `${Math.round(value * 100)}%`;
}
