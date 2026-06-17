import { auth } from "@clerk/nextjs/server";
import { notFound } from "next/navigation";
import { getVerdict } from "@/lib/api";
import { VerdictDetail } from "@/components/verdict-detail";

interface PageProps {
  params: { id: string };
}

export default async function VerdictDetailPage({ params }: PageProps) {
  const { getToken } = await auth();
  const token = await getToken();
  if (!token) notFound();
  const verdict = await getVerdict(token, params.id);
  if (!verdict) notFound();
  return <VerdictDetail verdict={verdict} />;
}
