import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ArchitectAI — Software architecture workspace",
  description: "Design software systems, keep project context close, and review proposed code before it is written.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    // Extensions such as LanguageTool add root attributes before React hydrates.
    <html lang="en" suppressHydrationWarning>
      <body>{children}</body>
    </html>
  );
}

