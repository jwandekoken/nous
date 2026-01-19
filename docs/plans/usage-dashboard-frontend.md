# Usage Dashboard Frontend

## Goal

Display token usage and cost data in the web app so tenants can:

- Monitor their LLM/embedding consumption
- Track costs over time
- Debug unexpected usage spikes
- Export data for reporting

---

## Current State

### Backend API (already implemented)

| Endpoint             | Purpose                                                                  |
| -------------------- | ------------------------------------------------------------------------ |
| `GET /usage/events`  | Paginated raw events with filters (operation, model, actor_type, status) |
| `GET /usage/summary` | Aggregates: total tokens/cost, by_day, by_operation                      |

### Frontend Stack

- **Framework**: Vue 3 (Composition API)
- **Router**: Vue Router
- **Styling**: Tailwind CSS
- **UI Components**: shadcn-vue
- **Patterns**: Pages in `pages/<feature>/views/`, services in `services/<feature>/`

---

## Access Control

- **Roles with access**: `tenant_admin`, `tenant_user`
- **Scope**: All users within a tenant can view all tenant usage (no per-user filtering enforced)

---

## Implementation Plan

### Phase 1: Simple Table-Based Dashboard (MVP)

#### File Structure

```
apps/web/src/
├── pages/usage/
│   └── views/
│       └── UsageDashboardView.vue
├── services/usage/
│   ├── types.ts
│   ├── usageApi.ts
│   └── index.ts
└── router/routes.ts  (add /usage route)
```

#### Components

1. **Summary Cards** — Total tokens, total cost (USD), period selector
2. **Events Table** — Paginated list with columns:
   - Date/Time
   - Operation
   - Model
   - Tokens (prompt/completion/total)
   - Cost (USD)
   - Status
3. **Filters** — Date range picker, operation dropdown, status toggle

#### UI Components from shadcn-vue

- `Card` for summary stats
- `Table`, `TableHeader`, `TableBody`, `TableRow`, `TableCell`
- `Select` for filters
- `Button` for actions
- `DatePicker` (or simple input[type="date"]) for date range
- `Pagination` for events list

---

### Phase 2: Charts & Visualizations (Future)

#### Chart Library Trade-offs

| Library           | Pros                                                   | Cons                                                | Bundle Size     |
| ----------------- | ------------------------------------------------------ | --------------------------------------------------- | --------------- |
| **Chart.js**      | Popular, good docs, Vue wrapper exists (`vue-chartjs`) | Canvas-based (not as crisp), moderate customization | ~60KB gzipped   |
| **ECharts**       | Feature-rich, beautiful defaults, great for dashboards | Large bundle, steeper learning curve                | ~200KB+ gzipped |
| **ApexCharts**    | Good Vue support, interactive, modern look             | Medium bundle, some features require pro license    | ~90KB gzipped   |
| **Recharts**      | React-focused (not ideal for Vue)                      | Requires React                                      | N/A for Vue     |
| **uPlot**         | Extremely fast, tiny bundle                            | Lower-level API, less out-of-box styling            | ~10KB gzipped   |
| **VueUse Charts** | Lightweight, composable                                | Limited chart types                                 | ~5KB gzipped    |

#### Recommendation

For a **Vue 3 + shadcn** stack with a focus on simplicity:

1. **Start with no charts** — Use summary cards and tables (Phase 1)
2. **Add Chart.js later** — If/when visual trends are needed
   - `npm install chart.js vue-chartjs`
   - Good balance of features, docs, and bundle size
   - Well-maintained Vue 3 wrapper

If the dashboard becomes more data-heavy:

- Consider **ECharts** for advanced visualizations
- Use dynamic imports to avoid bloating the main bundle

---

## Tasks

### Part 1 — Service Layer

- [x] Create `apps/web/src/services/usage/types.ts` with TypeScript types mirroring backend DTOs
- [x] Create `apps/web/src/services/usage/usageApi.ts` with fetch functions for `/usage/events` and `/usage/summary`
- [x] Create `apps/web/src/services/usage/index.ts` barrel export

### Part 2 — Page & Route

- [x] Create `apps/web/src/pages/usage/views/UsageDashboardView.vue`
- [x] Add route `/usage` in `routes.ts` with guards for `tenant_admin` and `tenant_user`

### Part 3 — Dashboard UI

- [x] Summary cards (total tokens, total cost, date range)
- [x] Date range picker (from/to inputs)
- [x] Events table with pagination
- [x] Loading and empty states
- [x] Error handling

### Part 4 — Polish

- [x] Add operation filter dropdown
- [x] Add status filter (ok/error)
- [x] Responsive design tweaks
- [ ] CSV export (nice-to-have)

---

## Design Notes

- Match existing admin pages (API Keys, Users) for consistency
- Use `Navigation` component for header
- Card-based layout for summary stats
- Table for detailed events list
- Keep it simple — avoid over-engineering for v1
