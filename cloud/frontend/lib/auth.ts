import { auth } from "@clerk/nextjs/server";

export interface DashboardAuth {
  userId: string | null;
  token: string | null;
  isE2EBypass: boolean;
}

export function isE2EAuthBypassEnabled(): boolean {
  return process.env.SLATE_E2E_AUTH_BYPASS === "true";
}

export async function getDashboardAuth(): Promise<DashboardAuth> {
  if (isE2EAuthBypassEnabled()) {
    return {
      userId: "slate-e2e-user",
      token: process.env.SLATE_E2E_AUTH_TOKEN ?? null,
      isE2EBypass: true,
    };
  }

  const session = await auth();
  return {
    userId: session.userId,
    token: await session.getToken(),
    isE2EBypass: false,
  };
}
