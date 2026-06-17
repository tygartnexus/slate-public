import fs from "node:fs";
import path from "node:path";

const root = path.resolve(process.cwd(), "..");
const workspace = path.resolve(root, "..");

const candidateFiles = [
  path.join(root, "README.md"),
  path.join(root, "docs", "launch", "LAUNCH_COPY.md"),
  path.join(root, "frontend", "app", "page.tsx"),
  path.join(root, "frontend", "app", "pricing", "page.tsx"),
  path.join(workspace, "Slate", "README.md"),
  path.join(workspace, "SlatePro", "README.md"),
].filter((file) => fs.existsSync(file));

const banned = [
  {
    pattern: /\bThrawn\b/i,
    reason: "public copy should use Panel naming; thrawn is legacy JSON compatibility only",
  },
  {
    pattern: /frames never leave/i,
    reason: "frame privacy must be provider-scoped, not absolute",
  },
  {
    pattern: /Core is on PyPI now/i,
    reason: "PyPI release must be verified before launch copy says it is live",
  },
  {
    pattern: /Slate Core|Slate Pro/i,
    reason: "public copy should present one Slate product, not multiple Slate levels",
  },
  {
    pattern: /\$\s*(29|149|290|1,490|5K)|Start Pro|Start Studio|Buy at|Stripe Checkout|customer portal|pricing tier/i,
    reason: "public copy should not advertise paid Slate plans",
  },
  {
    pattern: /chains?-of-thought/i,
    reason: "evidence copy should promise persona reports, not chain-of-thought",
  },
  {
    pattern: /self-hosted\s*\+\s*SSO\s*\+\s*SLA/i,
    reason: "Enterprise paid-tier claims should not remain in public copy",
  },
  {
    pattern: /license[- ]gated|valid license key|purchase a plan/i,
    reason: "Slate features are free and must not require activation or purchase",
  },
];

const failures = [];
for (const file of candidateFiles) {
  const text = fs.readFileSync(file, "utf8");
  for (const rule of banned) {
    if (rule.pattern.test(text)) {
      failures.push(`${path.relative(workspace, file)}: ${rule.reason}`);
    }
  }
}

if (failures.length) {
  console.error("Content claim check failed:");
  for (const failure of failures) {
    console.error(`- ${failure}`);
  }
  process.exit(1);
}

console.log(`Content claim check passed (${candidateFiles.length} files scanned).`);
