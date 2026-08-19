import type { Metadata } from "next";
import Link from "next/link";
import "maplibre-gl/dist/maplibre-gl.css";
import "./globals.css";

export const metadata: Metadata = {
  title: "Mireye Acquisition Intelligence",
  description: "Evidence-first agricultural acquisition investigations",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <header className="nav">
          <Link className="brand" href="/">
            <span className="mark">M</span> Mireye Intelligence
          </Link>
          <nav>
            <Link href="/">Investigate</Link>
            <Link href="/history">History</Link>
            <Link href="/profile">Buyer profile</Link>
          </nav>
        </header>
        <main>{children}</main>
        <footer>
          Independent evidence for agricultural acquisition decisions · Physical
          data does not establish legal rights.
        </footer>
      </body>
    </html>
  );
}
