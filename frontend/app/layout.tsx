import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "読解支援システム",
  description: "情報科学論文の理解を支援するシステム",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ja">
      <body>{children}</body>
    </html>
  );
}
