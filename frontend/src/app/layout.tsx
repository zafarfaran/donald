import type { Metadata } from "next";
import "./globals.css";
import { FirebaseRoot } from "@/components/FirebaseRoot";

export const metadata: Metadata = {
  title: "Donald | Is Your Degree Cooked?",
  description:
    "AI is coming for your job. Donald researches your degree, checks AI replacement risk, and hits you with a voice reality check and receipts.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full">
        <FirebaseRoot />
        {children}
      </body>
    </html>
  );
}
