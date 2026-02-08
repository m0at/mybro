# mybro — Frontend

## Stack Rules

| Need | Use | Never |
|------|-----|-------|
| Web frontend | Next.js or Vite | CRA, Webpack |
| Styling | Tailwind CSS | raw CSS at scale |
| Components | shadcn/ui | jQuery |
| Desktop | Tauri or native Swift | Electron |
| Mobile | Expo + NativeWind | — |
| Animation | Framer Motion | — |

## Production Templates

### 1. sqlite-browser (from TCGCC)
- React + Vite
- Client-side SQLite via WASM (offline-first)
- REST API query builder, export/import
- Handles 100k+ records

### 2. monitor-dashboard (from U200)
- HTML/JavaScript/WebSocket
- Real-time process + GPU monitoring
- Chart.js visualizations
- Large display optimized

### 3. disk-visualizer (from MacDirStat)
- React + Node.js/Express
- D3.js treemap visualization
- File search across millions of entries

### 4. multi-agent-chat (from Trio)
- Python Flask + Claude API frontend
- Multi-agent personas, real-time chat
- Conversation export

### 5. stripe-registration (from Gold)
- JavaScript + Stripe Elements
- Checkout sessions, subscription management
- Webhook handling

### 6. interactive-header (new)
- React/TypeScript canvas API
- Particle animation with mouse interaction
- Wave animations, responsive

```tsx
<InteractiveHeader
  logoText="YOUR APP"
  navItems={[
    { path: '/features', label: 'Features', icon: Sparkles },
    { path: '/pricing', label: 'Pricing', icon: CreditCard },
  ]}
/>
```

## Instant Stacks (Copy-Paste Ready)

| Pattern | Stack |
|---------|-------|
| Landing Page | Next.js + Tailwind + Framer Motion |
| SaaS Dashboard | Next.js + shadcn/ui + Supabase + Stripe |
| E-commerce | Next.js + Commerce.js |
| Mobile | Expo + NativeWind |
| Chrome Extension | Plasmo |
| Documentation | Nextra |
| Real-time | Liveblocks / Partykit |
| AI Chat | Vercel AI SDK |
| Blog | Astro + MDX |

## Decision Logic

### SSR vs Static vs Client-Side
- **SSR**: Dynamic content, SEO-critical pages, personalized data
- **Static**: Marketing pages, docs, blogs — pre-render at build
- **Client-Side**: Dashboards, internal tools, heavy interactivity

### State Management
- Server state → React Query / SWR
- Client state → Zustand (simple) or Jotai (atomic)
- Form state → React Hook Form + Zod
- URL state → nuqs or native searchParams

### Testing
- Unit → Vitest
- Component → Testing Library
- E2E → Playwright

## Status Dashboard

The pipeline exposes a real-time status dashboard on port 7777 via WebSocket. It shows:
- Current pipeline state
- Action counter and performance metrics
- Error tracking
- System resource usage
