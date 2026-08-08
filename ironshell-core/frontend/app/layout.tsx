/**
 * ╔══════════════════════════════════════════════════════════════════════════════╗
 * ║                    IRONSHELL ROOT LAYOUT                                     ║
 * ╚══════════════════════════════════════════════════════════════════════════════╝
 */

import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import { Toaster } from 'react-hot-toast'
import './globals.css'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'IronShell - Defensible AI Trading Journal',
  description: 'Build your competitive moat through intelligent trade analysis and learning',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={`${inter.className} bg-iron-950 text-gray-100 min-h-screen`}>
        {/* Toast notifications */}
        <Toaster
          position="top-right"
          toastOptions={{
            duration: 4000,
            style: {
              background: '#343b47',
              color: '#fff',
              border: '1px solid #444f62',
            },
            success: {
              iconTheme: {
                primary: '#22c55e',
                secondary: '#fff',
              },
            },
            error: {
              iconTheme: {
                primary: '#ef4444',
                secondary: '#fff',
              },
            },
          }}
        />

        {/* Main content */}
        {children}
      </body>
    </html>
  )
}
