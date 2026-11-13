# LOCUS Frontend

**LOCUS — Place where knowledge lives. Train, embed, retrieve your files into RAG.**

Built with Next.js 14 (App Router), TypeScript, Tailwind CSS, Framer Motion, and Lucide React.

- **Brand**: LOCUS
- **Tagline**: TRAIN &bull; EMBED &bull; RETRIEVE
- **Color System**: Background `#080808`, White `#FFFFFF`, Lime Accent `#C8F432`

---

## 1. Quick Start

### Prerequisites
- Node.js &ge; 18.x
- Running LOCUS Backend (`http://127.0.0.1:8000`)

### Installation & Run
```bash
# Navigate to frontend directory
cd frontend

# Install pinned dependencies
npm install

# Start development server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 2. Environment & Proxy Architecture

The frontend uses Next.js server rewrites (`next.config.js`) to proxy all `/api/*` browser calls to the backend without requiring backend CORS modifications:

```
Browser (localhost:3000)
    │
    ▼
/api/*  (Next.js Proxy Rewrite)
    │
    ▼
FastAPI Backend (http://127.0.0.1:8000/*)
```

### Environment Variables (`.env.local`)
Create `.env.local` from `.env.local.example`:
```bash
cp .env.local.example .env.local
```

| Variable | Default | Purpose |
| :--- | :--- | :--- |
| `BACKEND_URL` | `http://127.0.0.1:8000` | Backend target URL for Next.js proxy rewrites |

---

## 3. Design System & Tokens

Adheres strictly to the Trustify/Sift Dark Theme design system (`docs/design.md`):

| Token | Hex | Role |
| :--- | :--- | :--- |
| `obsidian` | `#09090B` | Deep background |
| `carbon` | `#111113` | Elevated cards & modals |
| `slate` | `#18181B` | Hover states & sub-containers |
| `graphite` | `#2A2A2E` | Subtle borders & dividers |
| `electric` | `#3B82F6` | Accent color, CTAs, focus rings |
| `emerald` | `#22C55E` | Verified, cited, success states only |
| `amber` | `#F59E0B` | Pending proposals, warnings, mock LLM alerts |
| `crimson` | `#EF4444` | Quarantined rows, critical severity, errors |
| `muted` | `#A1A1AA` | Secondary text & labels |
| `fg` | `#FAFAFA` | Primary high-contrast typography |

**Typography**:
- Headings: `Sora` (600, 700)
- Body: `Inter` (400, 500, 600)
- Code / IDs / Hashes: `JetBrains Mono`

---

## 4. Screens & Capabilities

- **Sources (`/sources`)**: Drag-and-drop file upload with 20 MB limits, URL crawl ingest with SSRF protections, sources list, and actionable toasts to Data Health.
- **Source Detail (`/sources/[id]`)**: Persistent Trust Strip with active/quarantined counts and pending critical proposals; 5 tabs: Data Health (completeness bars, inconsistencies), Cleaning (roles editor, proposal approvals, version apply), Versions (timeline, quarantined row tables), Documents (freshness buckets, override editor), and Indexing (trigger runs, chunk browser).
- **Ask (`/ask`)**: Evidence-gated RAG query interface, config selector, strategy selector, citations drawer, computed SQL aggregation specs, and introspectable trace timelines.
- **Compare (`/compare`)**: Side-by-side 4-column qualitative inspection across Dense, Lexical, Hybrid, and Hybrid+Rerank retrieval strategies.
- **Pipeline (`/pipeline`)**: Strategy recommender evaluating R1–R12 heuristic priors, field-by-field config diff with rule attributions, approval lifecycle, and interactive Mermaid architecture diagrams.

