import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI Timebox - Cognitive Calendar",
  description: "A scheduler that protects mental energy, absorbs chaos, and quietly thinks for you.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
