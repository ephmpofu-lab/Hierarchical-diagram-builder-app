# Design Brief: ARCHITEQ

Per `~/.claude/frameworks/universal-prd-framework.md` Section 2 and `rules/principles/
ui-design.md`. Values below are pulled directly from `static/css/style.css`'s real custom
properties, not re-invented for this document — this is a description of the shipped
system, not a new proposal.

---

## 1. Look & Feel

Dark graphite/charcoal by default, deliberately neutral rather than blue-black (the
stylesheet's own stated intent). A light theme exists as a full parallel token set, not an
inverted default. One accent hue (blue) carries every interactive/selected state; semantic
colors (success/warning/danger/info) are separate from the accent and never reused for
emphasis.

## 2. Color Palette

### Dark (default)

| Token | Value | Use |
|---|---|---|
| `--bg` | `#161616` | Page background |
| `--surface` | `#1e1e1e` | Card/panel background |
| `--surface-hover` | `#2a2a2a` | Hover state on surfaces |
| `--surface-2` | `#1a1a1a` | Secondary surface (nested panels) |
| `--border` | `#3a3a3a` | All hairline borders |
| `--text` | `#f2f2f2` | Primary text |
| `--text-muted` | `#9a9a9a` | Secondary/caption text |
| `--accent` | `#2563eb` | Primary actions, selected state, links |
| `--accent-hover` | `#1d4ed8` | Accent hover |
| `--success` | `#059669` | Passed validation, completed state |
| `--warning` | `#f59e0b` | In-progress, needs-attention state |
| `--danger` | `#dc2626` | Validation violations, destructive actions |
| `--info` | `#475569` | Neutral informational badges |

### Light (`:root[data-theme="light"]`)

| Token | Value |
|---|---|
| `--bg` | `#f8fafc` |
| `--surface` | `#ffffff` |
| `--border` | `#e2e8f0` |
| `--text` | `#0f172a` |
| `--text-muted` | `#64748b` |
| `--accent` | `#2563eb` (unchanged) |
| `--success` / `--warning` / `--danger` | same hues, foreground/background pairs re-tuned for light contrast |

Every color-bearing component reads from these tokens, never a hardcoded hex — this is what
lets the whole app re-theme by toggling `data-theme` on the root element, and is a standing
constraint (`ui-design.md`), not just current styling.

## 3. Typography

- **Body/UI face:** Inter, falling back to `-apple-system, "Segoe UI", Roboto, Helvetica,
  Arial, sans-serif`. One face across the whole app — no separate display face; hierarchy
  comes from size/weight, not a second typeface.
- **Scale:** headings and node labels sit visibly larger/bolder than body text; code
  snippets (Python render output) use the browser's monospace stack, distinct from the UI
  face, so rendered code is never confused with UI chrome.

## 4. Components

Reused, named idioms — not one-off styling per screen:

- **`.reasoning-node-card`** — the card visual language for "a card representing one node,"
  reused verbatim from the legacy Reasoning journey rather than inventing new card styling
  for the Engineering Decomposition UI.
- **Tree diagram node** (`.decompose-tree-node`, per-level classes `level-layer` /
  `level-sub-task` / `level-atomic-step`) — distinct box size and border color per C4 level:
  Layer boxes largest with an accent border, Sub-task medium, Atomic step smallest. All
  three read from the same theme tokens above, differing only in size/emphasis, not palette.
- **Node detail drawer** (`.node-detail-drawer`) — fixed-position slide-in panel,
  transform-based, backdrop-dimmed; canvas stays visible behind it (a panel, never a
  full-screen takeover). Escape/backdrop-click dismiss.
- **Refine bar** — small, persistent, pinned input, always visible on the canvas state;
  visually secondary to the tree itself (this app's equivalent of an embedded assistant
  input, per the UI directive's own Railway-dashboard precedent).
- **Planning-artifact hub-and-spoke diagram** (`.decompose-hub-diagram`, UI12/DP11) — one
  central hub card (icon, title, filename, description) with up to six satellite spoke
  cards in fixed three-left/three-right positions, connected by dashed curves measured from
  real card positions at render time. The hub icon is a small glyph badge
  (`.decompose-hub-icon`) reading from the same `--surface-2` token used elsewhere for icon
  badges, not a new color. Filename/code text in this component uses `var(--font-mono)`
  (headed by JetBrains Mono), matching the app's one standing named monospace stack rather
  than a component-local font choice.

## 5. Screen Style

- **Home/Canvas (empty state)**: centered intent input, generous whitespace, history list
  (if any) directly below — no hero imagery, no marketing copy; this is a tool, not a
  landing page.
- **Canvas (populated state)**: the tree diagram is the dominant visual element; the mode
  toggle and output section sit below it, never competing for the same visual weight as the
  tree itself.
- **Settings (hidden)**: plain, utilitarian raw-JSON panels — deliberately undesigned
  relative to the primary screens, since it is an admin/debug surface, not a user-facing one.
