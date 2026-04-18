import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { PWARegister } from "@/components/pwa-register";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  metadataBase: new URL(
    process.env.NEXT_PUBLIC_APP_URL || "https://pnp.example.com"
  ),
  title: "PNP Maritime Services - Ferry Ticketing | Gateway of India to Mandwa",
  description:
    "Book catamaran ferry tickets from Gateway of India to Mandwa Jetty. AC and Main Deck seating. Includes free bus to Alibag. 7 daily sailings.",
  manifest: "/manifest.json",
  icons: {
    icon: [
      { url: "/favicon-16x16.png", sizes: "16x16", type: "image/png" },
      { url: "/favicon-32x32.png", sizes: "32x32", type: "image/png" },
    ],
    apple: "/apple-touch-icon.png",
  },
  appleWebApp: {
    capable: true,
    statusBarStyle: "default",
    title: "PNP Ferry",
  },
  openGraph: {
    title: "PNP Maritime Services",
    description:
      "Gateway of India to Mandwa Jetty catamaran ferry. Includes free bus to Alibag.",
    images: [{ url: "/og-image.png", width: 1200, height: 630 }],
  },
};

export const viewport: Viewport = {
  themeColor: "#1e3a5f",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${inter.variable} antialiased`}
      >
        {children}
        <PWARegister />
      </body>
    </html>
  );
}
