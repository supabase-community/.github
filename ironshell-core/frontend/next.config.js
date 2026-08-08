/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Enable experimental features for better performance
  experimental: {
    // Server Actions for form handling
    serverActions: true,
  },
  // Environment variables exposed to the browser
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
    NEXT_PUBLIC_SUPABASE_URL: process.env.NEXT_PUBLIC_SUPABASE_URL || '',
    NEXT_PUBLIC_SUPABASE_ANON_KEY: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || '',
  },
}

module.exports = nextConfig
