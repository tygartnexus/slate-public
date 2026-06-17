import { redirect } from "next/navigation";
import Link from "next/link";
import { UserButton } from "@clerk/nextjs";
import { getDashboardAuth } from "@/lib/auth";

export default async function DashboardLayout({ children }: { children: React.ReactNode }) {
  const { userId, isE2EBypass } = await getDashboardAuth();
  if (!userId) redirect("/");

  return (
    <div className="min-h-screen">
      <nav className="border-b border-zinc-800 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-6">
          <Link href="/dashboard" className="font-mono text-lg">
            slate
          </Link>
          <Link href="/dashboard" className="text-zinc-400 hover:text-zinc-100">
            Verdicts
          </Link>
          <Link
            href="/dashboard/compare"
            className="text-zinc-400 hover:text-zinc-100"
          >
            Compare
          </Link>
          <Link
            href="/dashboard/license"
            className="text-zinc-400 hover:text-zinc-100"
          >
            Access
          </Link>
        </div>
        {isE2EBypass ? (
          <div className="text-sm text-zinc-500">E2E</div>
        ) : (
          <UserButton />
        )}
      </nav>
      <main className="px-6 py-8 max-w-6xl mx-auto">{children}</main>
    </div>
  );
}
