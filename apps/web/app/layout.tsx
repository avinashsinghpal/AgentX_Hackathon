import React from "react"
import type { Metadata } from 'next'
import { Instrument_Sans, Instrument_Serif, JetBrains_Mono } from 'next/font/google'
import './globals.css'

const instrumentSans = Instrument_Sans({ 
  subsets: ["latin"],
  variable: '--font-instrument'
});

const instrumentSerif = Instrument_Serif({ 
  subsets: ["latin"],
  weight: "400",
  variable: '--font-instrument-serif'
});

const jetbrainsMono = JetBrains_Mono({ 
  subsets: ["latin"],
  variable: '--font-jetbrains'
});

export const metadata: Metadata = {
  title: 'SellerResolve - Autonomous Support Agent for Online Sellers',
  description: 'Investigate. Decide. Act. Verify. Autonomous, policy-aware customer support for small online sellers.',
  openGraph: {
    title: 'SellerResolve - Autonomous Support Agent for Online Sellers',
    description: 'Investigate. Decide. Act. Verify. Autonomous, policy-aware customer support for small online sellers.',
    type: 'website',
    locale: 'en_US',
    siteName: 'SellerResolve',
  },
  icons: {
    icon: '/favicon.svg',
  },
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en">
      <body className={`${instrumentSans.variable} ${instrumentSerif.variable} ${jetbrainsMono.variable} font-sans antialiased`}>
        {children}
      </body>
    </html>
  )
}
