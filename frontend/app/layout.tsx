import type { ReactNode } from "react";
import type { Metadata } from "next";

import "@/app/globals.css";
import { SiteBrand } from "@/shared/ui/site-brand";

export const metadata: Metadata = {
  title: "treeroute",
  description:
    "A tree pollen-aware routing experience for allergy-sensitive New Yorkers.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        {children}
        <SiteBrand />
      </body>
    </html>
  );
}
