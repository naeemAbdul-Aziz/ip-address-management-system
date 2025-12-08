import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "IPAM System | Draka Labs",
  description: "Enterprise IP Address Management System",
  icons: {
    icon: "/icon.png",
  },
};

import AuthGuard from "../components/AuthGuard";
import { ToastProvider } from "../components/ui/Toast";

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <ToastProvider>
          <AuthGuard>
            {children}
          </AuthGuard>
        </ToastProvider>
      </body>
    </html>
  );
}
