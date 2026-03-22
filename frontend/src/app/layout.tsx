import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "YeyoOS — Neural Hub",
  description: "AI-native operating system",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es" className="h-full antialiased">
      <body className="min-h-full flex flex-col bg-[#0a0a0f]">{children}</body>
    </html>
  );
}
