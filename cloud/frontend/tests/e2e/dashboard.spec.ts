import { expect, test, type APIRequestContext } from "@playwright/test";

interface SeededVerdicts {
  passShotId: string;
  failShotId: string;
  passId: string;
  failId: string;
}

test("dashboard lists uploaded verdict and shows evidence sections", async ({
  page,
  request,
}, testInfo) => {
  const seeded = await seedVerdicts(request, testInfo.workerIndex);
  const expectedShotId = seeded?.failShotId ?? "e2e_gemma_public_001";
  const expectedFailures = seeded ? "Failures (1)" : "Failures (9)";

  await page.goto("/dashboard");

  await expect(page.getByRole("heading", { name: "Verdicts" })).toBeVisible();
  await expect(page.getByText(/verdicts? uploaded/)).toBeVisible();
  await expect(page.getByText(expectedShotId)).toBeVisible();
  await expect(page.getByText("FAIL").first()).toBeVisible();

  await page.getByText(expectedShotId).click();

  await expect(page.getByText(expectedShotId).first()).toBeVisible();
  await expect(page.getByText("confidence 82%")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Evidence-based answer" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Facts" }).first()).toBeVisible();
  await expect(page.getByRole("heading", { name: "Assumptions" }).first()).toBeVisible();
  await expect(page.getByRole("heading", { name: "Unknowns" }).first()).toBeVisible();
  await expect(page.getByRole("heading", { name: "Evidence" }).first()).toBeVisible();
  await expect(page.getByText(expectedFailures)).toBeVisible();

  await page.getByRole("button", { name: "Red Team Mode" }).click();
  await expect(page.getByRole("heading", { name: "Hostile red-team review" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Risks" }).first()).toBeVisible();
  await expect(page.getByRole("heading", { name: "Counterarguments" }).first()).toBeVisible();

  await page.getByRole("link", { name: "Access" }).click();
  await expect(page.getByRole("heading", { name: "Access" })).toBeVisible();
  await expect(page.getByText("All Slate features are free.")).toBeVisible();
});

test("compare shows side-by-side verdict deltas", async ({ page, request }, testInfo) => {
  const seeded = await seedVerdicts(request, testInfo.workerIndex);
  if (!seeded) {
    test.skip(true, "requires SLATE_E2E_AUTH_TOKEN and PLAYWRIGHT_API_URL");
    return;
  }

  await page.goto(
    `/dashboard/compare?left=${seeded.failId}&right=${seeded.passId}`,
  );

  await expect(page.getByRole("heading", { name: "Compare verdicts" })).toBeVisible();
  await expect(page.getByText(seeded.failShotId).first()).toBeVisible();
  await expect(page.getByText(seeded.passShotId).first()).toBeVisible();
  await expect(page.getByRole("heading", { name: "Failure delta" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Quality score delta" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Response quality" })).toBeVisible();
  await expect(page.getByText("character_visible")).toBeVisible();
  await expect(page.getByText("-1.00")).toBeVisible();
});

async function seedVerdicts(
  request: APIRequestContext,
  workerIndex: number,
): Promise<SeededVerdicts | null> {
  const token = process.env.SLATE_E2E_AUTH_TOKEN;
  const apiUrl = process.env.PLAYWRIGHT_API_URL ?? process.env.NEXT_PUBLIC_API_URL;
  if (!token || !apiUrl) return null;

  const runId = `${Date.now()}_${workerIndex}`;
  const passShotId = `e2e_compare_pass_${runId}`;
  const failShotId = `e2e_compare_fail_${runId}`;
  const headers = { Authorization: `Bearer ${token}` };

  const seededIds: Partial<Pick<SeededVerdicts, "passId" | "failId">> = {};
  const payloads = [
    { key: "passId" as const, payload: makeVerdict(passShotId, "PASS", 4, []) },
    {
      key: "failId" as const,
      payload: makeVerdict(failShotId, "FAIL", 5, [
        {
          signal: "character_visible",
          value: false,
          frame: "frame_0000.png",
          provider: "e2e",
          model: "fixture",
          description: "Fixture failure for comparison.",
        },
      ]),
    },
  ];

  for (const { key, payload } of payloads) {
    const response = await request.post(`${apiUrl}/verdicts`, {
      headers,
      data: { payload },
    });
    expect(response.status()).toBe(201);
    const created = (await response.json()) as { id?: string };
    expect(created.id).toBeTruthy();
    seededIds[key] = created.id;
  }

  return {
    passShotId,
    failShotId,
    passId: seededIds.passId!,
    failId: seededIds.failId!,
  };
}

function makeVerdict(
  shotId: string,
  status: "PASS" | "FAIL",
  lightingQuality: number,
  failures: {
    signal: string;
    value: boolean;
    frame: string;
    provider: string;
    model: string;
    description: string;
  }[],
) {
  return {
    status,
    shot_id: shotId,
    slate_version: "0.1.0-e2e",
    started_at: "2026-06-17T00:00:00Z",
    finished_at: "2026-06-17T00:00:01Z",
    duration_seconds: 1,
    providers_consulted: ["e2e"],
    frames_analyzed: ["frame_0000.png"],
    failures,
    frame_analyses: [],
    quality_scores_aggregated: {
      lighting_quality: lightingQuality,
      composition_quality: 4,
    },
    response_quality: {
      facts: [`Slate status is ${status}.`],
      assumptions: ["The E2E fixture payload is representative of a saved verdict."],
      unknowns: ["The fixture does not include original frame pixels."],
      confidence_score: status === "PASS" ? 0.78 : 0.82,
      evidence: ["Playwright seeded verdict payload."],
      risks: ["Fixture data proves dashboard behavior, not model accuracy."],
      counterarguments: ["Live provider certification is tracked separately."],
      recommendation:
        status === "PASS"
          ? "Use as a comparison baseline only."
          : "Use as a comparison failure case only.",
      tradeoffs: ["Fixture-backed E2E is deterministic but not provider proof."],
      what_would_change_recommendation: [
        "A live provider run with materially different findings.",
      ],
    },
  };
}
