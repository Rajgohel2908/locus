import type { Metadata } from "next";
import "./globals.css";
import AppShell from "@/components/AppShell";

export const metadata: Metadata = {
  title: "LOCUS — Train, Embed, Retrieve",
  description:
    "LOCUS — Place where knowledge lives. Train, embed, retrieve your files into RAG.",
  keywords: [
    "LOCUS",
    "RAG",
    "Vector Database",
    "Embedding",
    "Retrieval",
    "Knowledge Engine",
    "Qdrant",
  ],
  authors: [{ name: "LOCUS Team" }],
  icons: {
    icon: [
      { url: "/favicon.ico" },
      { url: "/favicon-16x16.png", sizes: "16x16", type: "image/png" },
      { url: "/favicon-32x32.png", sizes: "32x32", type: "image/png" },
      { url: "/locus-icon.svg", type: "image/svg+xml" },
    ],
    apple: [{ url: "/apple-touch-icon.png", sizes: "180x180" }],
  },
  manifest: "/site.webmanifest",
  openGraph: {
    title: "LOCUS — Train, Embed, Retrieve",
    description:
      "LOCUS — Place where knowledge lives. Train, embed, retrieve your files into RAG.",
    url: "https://locus.ai",
    siteName: "LOCUS",
    images: [
      {
        url: "/apple-touch-icon.png",
        width: 180,
        height: 180,
        alt: "LOCUS Logo",
      },
    ],
    locale: "en_US",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "LOCUS — Train, Embed, Retrieve",
    description:
      "LOCUS — Place where knowledge lives. Train, embed, retrieve your files into RAG.",
    images: ["/apple-touch-icon.png"],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark scroll-smooth">
      <head>
        <link rel="preconnect" href="https://api.fontshare.com" />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://api.fontshare.com/v2/css?f[]=satoshi@300,400,500&display=swap"
          rel="stylesheet"
        />
        <link
          href="https://fonts.googleapis.com/css2?family=Niconne&display=swap"
          rel="stylesheet"
        />
        <link
          href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@1&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="font-body bg-[#080808] text-fg min-h-screen antialiased selection:bg-[#C8F432] selection:text-black">
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
