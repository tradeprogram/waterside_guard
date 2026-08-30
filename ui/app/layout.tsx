import type { Metadata } from "next";
import { Geist, Geist_Mono, Noto_Sans_KR } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

// 화면이 거의 전부 한글이라 본문 폰트를 한글 기준으로 잡는다 — Geist는 라틴 전용이라
// 지금까지 한글은 브라우저 기본 폰트로 떨어지고 있었다(굵기·자간이 OS마다 달라짐).
const notoSansKR = Noto_Sans_KR({
  variable: "--font-noto-sans-kr",
  subsets: ["latin"],
  weight: ["400", "500", "700"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "수변가드 AI — 수변녹지 점검 우선순위 지원시스템",
  description: "한강수계 매수토지·수변녹지의 위성 변화탐지 기반 현장점검 우선순위 지원시스템",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="ko"
      className={`${geistSans.variable} ${geistMono.variable} ${notoSansKR.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
