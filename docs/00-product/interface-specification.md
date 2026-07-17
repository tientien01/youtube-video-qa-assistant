---
id: PRODUCT-UI-001
document_status: approved
implementation_status: verified
normative: true
last_verified: 2026-07-16
reference: user-approved video workspace mock, 2026-07-16
---

# Local V1 Interface Specification

## Authority and intent

This document translates the approved desktop mock into an implementation
contract that remains usable when an AI coding agent cannot see the original
conversation. It defines the target information architecture, behavior, and
visual hierarchy. Current frontend code is not a visual authority.

The target is a polished local-first video learning workspace, not a generic
dashboard and not a collection of unrelated cards. Implementations MUST preserve
the hierarchy and interactions below. Exact copy and video content MAY differ.

The approved mock image SHOULD be committed later as
`docs/00-product/assets/video-workspace-reference.png` when the original binary
is available. Absence of that binary does not weaken this textual contract.

## Product shell

The desktop application uses a fixed three-part shell:

```text
+----------------------+-------------------------------------------------------+
|                      | top bar: history, breadcrumb, search, language, health|
| left navigation      +--------------------------------+----------------------+
|                      | video                          | ask this video       |
| product identity     |                                |                      |
| primary destinations +--------------------------------+                      |
|                      | transcript                     +----------------------+
| local runtime cards  |                                | evidence             |
| collapse             |                                |                      |
+----------------------+--------------------------------+----------------------+
```

At a reference viewport of 1680x960:

- The navigation rail is approximately 246px wide and spans the viewport.
- The top bar is approximately 68px high and remains visible.
- Workspace padding is 16-20px; major panel gaps are 16-20px.
- The content area is split approximately 62% left and 38% right.
- The left column contains a 16:9 player followed by the transcript panel.
- The right column contains conversation followed by evidence.
- The workspace uses the available viewport height; panels scroll internally
  instead of turning the entire page into an excessively long dashboard.

## Navigation and route ownership

| Destination | Route | Local V1 behavior |
|---|---|---|
| Home | `/` | Ingest entry, recent videos, interrupted/failed job recovery |
| Library | `/library` | Searchable video library and ingest status |
| Video workspace | `/library/:videoId` | Player, transcript, chat, and evidence; primary mock screen |
| Learning | `/learning` | Entry to summaries and study workflows |
| Notes | `/notes` | Saved/generated notes grouped by video |
| Quizzes | `/quizzes` | Generated quizzes and attempts |
| Flashcards | `/flashcards` | Study-card view when backed by persisted data; otherwise clearly marked planned |
| Activity | `/activity` | Local ingest/generation history when backed by persisted events; no fabricated events |
| Developer | `/developer` | Retrieval diagnostics and evaluation tools, visually separated from learner flows |
| Settings | `/settings` | Local provider, model, language, and storage configuration |

Navigation items MUST NOT imply completed features without working routes and
data. A planned destination MAY be visible but disabled with an explicit
`Coming later` label. It MUST NOT lead to an empty, broken, or fake page.

The active destination uses an indigo-tinted background, indigo icon/text, and a
3px left indicator. The collapsed rail retains icons and accessible tooltips.

## Top bar

The top bar contains, from left to right:

1. back and forward navigation controls;
2. breadcrumb (`Library > current video title`);
3. centered command/search field with a visible `Cmd/Ctrl+K` shortcut;
4. Vietnamese/English selector;
5. system-health summary and expandable details.

The command field searches or navigates across videos, transcript text, and
available destinations. If global search is not implemented yet, it MUST be
labelled as unavailable rather than behaving like a decorative input.

System health is derived from real checks. `Operational` MUST NOT be shown when
required local dependencies are unavailable. Health details distinguish at
least API, SQLite, vector index, and configured LLM provider.

## Left navigation runtime cards

The bottom of the navigation rail contains compact runtime cards:

- LLM runtime: provider, configured model, and actual availability. The mock's
  `Ollama / llama3:8b / Running` is illustrative, not hard-coded product data.
- Storage: used/capacity information only when the operating system or backend
  provides reliable values. Otherwise show database size and label it precisely.

Green status indicators represent a successful live health check, not merely a
configured provider. Cards link to Settings or health details.

## Video workspace

### Video player

The player is the visual anchor of the workspace. It MUST:

- render the selected YouTube video through a supported embedded player;
- expose current time, duration, play/pause, volume, captions, settings where
  supported, and fullscreen behavior;
- accept seek commands from transcript rows and evidence citations;
- update transcript highlighting as playback time changes;
- use a dark media surface with a subtle border and 12-16px radius.

The product MUST NOT draw controls that do not work. When YouTube iframe policy
or browser limitations prevent a custom control, use the real embedded control
and preserve the mock's surrounding layout.

### Transcript panel

The transcript panel header contains:

- title `Transcript`;
- source-language selector (`VI / EN` in the mock);
- transcript search;
- filter/settings control for transcript display options.

Each row contains a clickable timestamp, original text, and optional translated
text in a quieter style. Rows preserve canonical segment identity and exact
timestamps. The currently playing or selected row uses a pale indigo surface and
play indicator. Hover/focus reveals a compact action menu without shifting text.

Required interactions:

- clicking a timestamp or row seeks and plays the corresponding segment;
- transcript search highlights matches and moves between results;
- playback follows the active row without stealing keyboard focus;
- selecting evidence scrolls to and highlights its source transcript range;
- translation never replaces or mutates original source text.

Virtualization SHOULD be used for long transcripts. Loading, no-transcript,
provider failure, and retry states MUST appear inside this panel.

### Ask this video panel

The right conversation panel contains:

- heading with product mark and overflow actions;
- user question bubbles using a quiet indigo tint;
- assistant answers optimized for readable structured text;
- inline timestamp citations styled as small cyan/teal outlined links;
- message actions such as copy and feedback;
- a composer fixed to the bottom of the panel when conversation scrolls.

Assistant answers MUST render validated structured content safely. Citation
clicks seek the player, select the source transcript range, and focus the matching
evidence card. Unsupported citation IDs MUST never appear as successful links.

The panel supports empty, generating, provider-unavailable, insufficient-
evidence, success, and retry states. Provider failure MUST NOT be presented as
an empty answer. Vietnamese and English text must remain equally readable.

### Evidence panel

Evidence is always visible beside or directly after the answer; it is not hidden
inside a developer-only drawer. Its header shows the real source count and a
collapse control.

Each evidence card contains:

- stable ordinal marker;
- timestamp range;
- concise source excerpt;
- `Play segment` action;
- `View transcript` action;
- selected/active state synchronized with the answer and player.

Evidence order follows the validated answer citations when an answer exists and
retrieval rank otherwise. Scores and internal chunk metadata belong in Developer
mode, not the default learner card.

## Ingest and non-workspace states

The Home and Library flows MUST use the persistent ingest job API. They render
real stages rather than timers or invented percentages:

```text
pending -> fetching metadata -> fetching transcript -> normalize/validate
-> chunk -> embed -> commit -> ready
```

The interface provides retry for retryable failures, cancellation for active
jobs, and recovery messaging for jobs interrupted by a local restart. The prior
ready video remains available while a rebuild fails.

Before a video is selected, the workspace shows a deliberate empty state with a
YouTube URL action and recent-library choices; it MUST NOT show fake transcript,
chat, evidence, model health, or storage values.

## Visual language

### Character

The visual direction is calm, precise, technical, and study-oriented. It uses
light neutral surfaces, strong typographic hierarchy, restrained indigo accents,
and teal citation accents. Avoid neon gradients, glassmorphism, oversized hero
marketing, heavy shadows, and excessive card nesting.

### Baseline tokens

Implement tokens as CSS custom properties or theme values rather than scattered
literal colors:

| Token | Target role |
|---|---|
| `--color-bg` | Cool off-white application background, near `#F7F8FC` |
| `--color-surface` | Primary panel surface, near white |
| `--color-border` | Cool subtle divider, near `#E3E7F0` |
| `--color-text` | Navy-charcoal primary text, near `#182033` |
| `--color-muted` | Secondary text, near `#707991` |
| `--color-primary` | Indigo action/selection, near `#5B61E6` |
| `--color-primary-soft` | Pale indigo selected surface |
| `--color-citation` | Teal/cyan timestamps and evidence markers |
| `--color-success` | Runtime healthy state only |
| `--color-danger` | Failure/destructive action |

- Use a modern UI sans-serif such as Inter with a system fallback.
- Default body text is 14-16px with at least 1.45 line height.
- Major panel radii are 12-16px; compact controls use 8-10px.
- Borders establish most separation. Shadows remain subtle and sparse.
- Icons MUST come from one consistent outline icon family.
- Animations are 120-220ms and respect `prefers-reduced-motion`.

## Responsive behavior

| Width | Required behavior |
|---|---|
| `>= 1280px` | Full rail, top bar, two-column workspace matching the mock |
| `900-1279px` | Collapsed rail; player/transcript and chat/evidence remain usable without horizontal scroll |
| `600-899px` | Single workspace column; Chat and Evidence become an accessible tab/section switcher |
| `< 600px` | Drawer or compact bottom navigation, stacked player/transcript/chat, touch targets at least 44px |

Mobile does not need to resemble a shrunk desktop screenshot, but feature order,
source traceability, and state semantics MUST remain intact.

## Accessibility and localization

- Keyboard operation covers navigation, transcript search/results, timestamps,
  citation links, evidence actions, and chat composer.
- Focus indicators are visible and are not removed for aesthetics.
- Text and interactive controls meet WCAG 2.2 AA contrast targets.
- Color is never the only status signal.
- Icon-only buttons have accessible names and tooltips where useful.
- Player/transcript synchronization uses non-disruptive live announcements.
- Layout supports Vietnamese expansion and later localization without fixed text
  widths. Product UI may migrate incrementally, but transcript retrieval and
  answers treat Vietnamese and English as first-class now.

## Frontend ownership boundaries

Target feature modules:

```text
frontend/src/
  app/                 router, shell, providers, global error boundary
  pages/               route composition only
  features/
    ingest/
    library/
    player/
    transcript/
    chat/
    evidence/
    learning/
    notes/
    quizzes/
    runtime-health/
  shared/
    api/                generated contracts and request client
    ui/                 reusable primitives and design tokens
    utils/
```

Pages compose features; they MUST NOT duplicate API calls or domain state. The
chat answer and Evidence panel share one citation selection model. The player and
transcript share one playback-time source. Server data uses a query/cache layer;
ephemeral view state stays local. Do not create a global store without a concrete
cross-feature ownership need.

## Visual acceptance

TASK-013 is complete only when:

- the 1680x960 video-workspace screenshot preserves the mock's shell, column
  proportions, visual hierarchy, and information density;
- browser tests cover timestamp seek, transcript selection, citation-to-evidence
  synchronization, navigation, job states, and provider-unavailable behavior;
- screenshots exist for ready desktop, ingesting, failed/retryable, empty, and
  narrow mobile states;
- no placeholder control, fabricated health value, fake percentage, or dead
  navigation destination is presented as functional;
- frontend lint, tests, production build, keyboard review, and contrast review pass.
