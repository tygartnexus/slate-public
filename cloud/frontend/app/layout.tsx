import "./globals.css";
import type { Metadata } from "next";
import { ClerkProvider } from "@clerk/nextjs";
import { isE2EAuthBypassEnabled } from "@/lib/auth";

export const metadata: Metadata = {
  title: "Slate — don't ship broken AI animation",
  description:
    "Multi-VLM verdict and adversarial persona ensemble for rendered animation frames.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const body = (
    <html lang="en">
      <body>{children}</body>
    </html>
  );

  if (isE2EAuthBypassEnabled()) {
    return body;
  }

  return (
    <ClerkProvider>
      {body}
    </ClerkProvider>
  );
}
