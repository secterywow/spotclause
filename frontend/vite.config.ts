import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import Sitemap from 'vite-plugin-sitemap'

const PUBLIC_ROUTES = [
  '/',
  '/compare',
  '/pricing',
  '/privacy',
  '/terms',
  '/refund',
  '/disclaimer',
]

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    Sitemap({
      hostname: 'https://spotclause.app',
      generateRobotsTxt: false,
      extensions: [],
      dynamicRoutes: PUBLIC_ROUTES,
      priority: {
        '/': 1.0,
        '/compare': 0.8,
        '/pricing': 0.8,
        '/privacy': 0.3,
        '/terms': 0.3,
        '/refund': 0.3,
        '/disclaimer': 0.3,
      },
      changefreq: {
        '/': 'daily',
        '/compare': 'daily',
        '/pricing': 'weekly',
        '/privacy': 'monthly',
        '/terms': 'monthly',
        '/refund': 'monthly',
        '/disclaimer': 'monthly',
      },
    }),
  ],
})
