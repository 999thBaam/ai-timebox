import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI Timebox",
  description: "Cognitive Calendar - Human-state aware time orchestration",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">
        {children}
      </body>
    </html>
  );
}
