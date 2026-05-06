---
name: Intelligence Copilot Design System
colors:
  surface: '#13121b'
  surface-dim: '#13121b'
  surface-bright: '#393842'
  surface-container-lowest: '#0e0d16'
  surface-container-low: '#1b1b24'
  surface-container: '#1f1f28'
  surface-container-high: '#2a2933'
  surface-container-highest: '#35343e'
  on-surface: '#e4e1ee'
  on-surface-variant: '#c7c4d8'
  inverse-surface: '#e4e1ee'
  inverse-on-surface: '#302f39'
  outline: '#918fa1'
  outline-variant: '#464555'
  surface-tint: '#c3c0ff'
  primary: '#c3c0ff'
  on-primary: '#1d00a5'
  primary-container: '#4f46e5'
  on-primary-container: '#dad7ff'
  inverse-primary: '#4d44e3'
  secondary: '#c4c6d0'
  on-secondary: '#2d3038'
  secondary-container: '#464951'
  on-secondary-container: '#b6b8c2'
  tertiary: '#ffb695'
  on-tertiary: '#571f00'
  tertiary-container: '#a44100'
  on-tertiary-container: '#ffd2be'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#e2dfff'
  primary-fixed-dim: '#c3c0ff'
  on-primary-fixed: '#0f0069'
  on-primary-fixed-variant: '#3323cc'
  secondary-fixed: '#e0e2ec'
  secondary-fixed-dim: '#c4c6d0'
  on-secondary-fixed: '#191c23'
  on-secondary-fixed-variant: '#44474f'
  tertiary-fixed: '#ffdbcc'
  tertiary-fixed-dim: '#ffb695'
  on-tertiary-fixed: '#351000'
  on-tertiary-fixed-variant: '#7b2f00'
  background: '#13121b'
  on-background: '#e4e1ee'
  surface-variant: '#35343e'
  bg-root: '#12151C'
  surface-canvas: '#FFFFFF'
  border-subtle: '#E8EAEF'
  nav-inactive: '#8B95A8'
  nav-active: '#FFFFFF'
  primary-light: '#EEF2FF'
  success: '#16A34A'
  success-light: '#DCFCE7'
  warning: '#D97706'
  warning-light: '#FEF3C7'
  danger: '#DC2626'
  danger-light: '#FEE2E2'
  info: '#2563EB'
  info-light: '#DBEAFE'
  text-main: '#111827'
  text-muted: '#6B7280'
  text-hint: '#9CA3AF'
typography:
  display:
    fontFamily: Plus Jakarta Sans
    fontSize: 24px
    fontWeight: '700'
    lineHeight: '1.2'
  heading-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 20px
    fontWeight: '600'
    lineHeight: '1.4'
  body-main:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: '1.6'
  ui-label:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '500'
    lineHeight: '1'
  mono:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '400'
    lineHeight: '1.5'
  nav-item:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '500'
    lineHeight: '1.4'
  session-header:
    fontFamily: Inter
    fontSize: 10px
    fontWeight: '700'
    lineHeight: '1'
    letterSpacing: 0.05em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  canvas-margin: 24px
  internal-gap: 24px
  widget-padding: 16px
  nav-width: 260px
  sidebar-panel: 300px
---

# Company Intelligence Copilot — UI/UX Design Spec

## Layout Philosophy — CRITICAL

The entire screen background is **one dark color** (`#12151C`). There is no sidebar box or sidebar container. Navigation items sit directly on top of this dark background on the left side.

The main content is **one single large white rounded card** that floats on top of the dark background. This card has margin/padding on all sides so the dark background is visible around it — top, right, bottom. The left edge of the card starts after the nav items area.

The internal layout of this white card changes per page. Some pages split it internally into two columns, others use the full width.

```
+------------------------------------------------------------------+
|  DARK BACKGROUND #12151C  (full screen, edge to edge)            |
|                                                                  |
|  [avatar]                  +------------------------------+  gap |
|  [name]                    |                              |      |
|  [email]                   |   ONE BIG WHITE CARD         |  gap |
|                            |   border-radius: 24px        |      |
|  Dashboard                 |   box-shadow: large soft     |      |
|  Expenses  <-- active      |                              |      |
|  Wallets                   |   internal layout depends    |      |
|  Summary                   |   on active menu             |      |
|  Accounts                  |                              |      |
|  Settings                  +------------------------------+  gap |
|                                                                  |
+------------------------------------------------------------------+
```

### Key layout rules:
- `background: #12151C` on the root/body, full viewport
- Nav items: positioned on the left, no background container, no border, no box
- White card: `margin-top: 24px`, `margin-right: 24px`, `margin-bottom: 24px`, `margin-left: 0` (flush with nav area or small gap)
- White card `border-radius: 24px`
- White card fills the remaining height and width
- The dark background is visible as a "frame" around the card on top, right, and bottom edges

---

## Design System

### Colors

| Token | Value | Usage |
|---|---|---|
| `--bg` | `#12151C` | Full screen background |
| `--card` | `#FFFFFF` | The floating white card |
| `--border` | `#E8EAEF` | Internal card borders, dividers |
| `--nav-text` | `#8B95A8` | Inactive nav label |
| `--nav-text-active` | `#FFFFFF` | Active nav label |
| `--primary` | `#4F46E5` | Buttons, active elements, links |
| `--primary-light` | `#EEF2FF` | Primary tinted backgrounds |
| `--green` | `#16A34A` | Ready, Go, success |
| `--green-light` | `#DCFCE7` | Green tinted backgrounds |
| `--amber` | `#D97706` | Processing, Validate First |
| `--amber-light` | `#FEF3C7` | Amber tinted backgrounds |
| `--red` | `#DC2626` | Failed, No-Go, risks |
| `--red-light` | `#FEE2E2` | Red tinted backgrounds |
| `--blue` | `#2563EB` | Uploaded, info |
| `--blue-light` | `#DBEAFE` | Blue tinted backgrounds |
| `--text-primary` | `#111827` | Body text inside card |
| `--text-secondary` | `#6B7280` | Muted labels |
| `--text-tertiary` | `#9CA3AF` | Hints, timestamps |

### Typography

- **Headings**: `DM Sans` — page titles, card headings
- **Body / UI**: `Inter` — body text, labels, inputs, table
- **Mono**: `JetBrains Mono` — filenames, trace IDs, slash commands

### Shape

- White card border-radius: `24px`
- Inner card/widget radius: `12px`
- Button radius: `8px`
- Badge radius: `999px`
- White card shadow: `0 8px 40px rgba(0,0,0,0.25)`

---

## Navigation (left side, on dark background)

```
[square icon]  Intelligence
               Copilot
               Strategic Workspace    <- muted small subtitle

[chat icon]    Chat                   <- active: white, bold
[chart icon]   Visualization Data    <- inactive: muted gray
[folder icon]  Source Data

               -- RECENT SESSIONS --  <- only when Chat active, 10px uppercase muted
               Market Strategy...
               Q2 Feature Plan
               Competitor Anal...

[+ Add New Source]                    <- ghost outline button

- - - - - - - - - - - - - -

[gear icon]    Settings
[? icon]       Support
[avatar]       User Name             <- bottom of screen
               workspace label
```

- No background, no container, no box — all items sit directly on `#12151C`
- Active nav item: white text + bold weight. Optional: small indigo left accent bar `2px`
- Inactive nav item: `--nav-text` muted gray
- Avatar/user profile at very bottom left

---

## White Card — Internal Layouts Per Page

### Chat Page — internal 2-column split

The white card is split internally into two columns. There is a vertical divider line inside the card separating them.

```
+--------------------------------------------------------------+
|  WHITE CARD                                                  |
|  +-------------------------------+---+---------------------+ |
|  |  CHAT AREA (flex-1)          | | |  SOURCES PANEL      | |
|  |                              | | |  (~300px)           | |
|  |  [session timestamp]         | | |  Sources Used       | |
|  |                              | | |  [source card 1]    | |
|  |  [user bubble - right]       | | |  [source card 2]    | |
|  |                              | | |                     | |
|  |  [AI response card]          | | |  Trace Reference >  | |
|  |                              | | |  Drafted Briefs  >  | |
|  |  [input bar - pinned bottom] | | |                     | |
|  +-------------------------------+---+---------------------+ |
+--------------------------------------------------------------+
```

### Source Data Page — internal full width

The white card uses its full internal width. No column split.

```
+--------------------------------------------------------------+
|  WHITE CARD                                                  |
|  [page header + Add New Data button]                         |
|  [stats cards row]                                           |
|  [filter bar]                                                |
|  [table full width]                                          |
|  [pagination]                                                |
+--------------------------------------------------------------+
```

### Visualization Data Page — internal full width

```
+--------------------------------------------------------------+
|  WHITE CARD                                                  |
|  [page header + filter dropdowns]                            |
|  [KPI cards row]                                             |
|  [chart full width]                                          |
|  [PDF insight cards]                                         |
+--------------------------------------------------------------+
```

---

## Page 1: Chat

**White card internal layout**: chat area (left, flex-1) + sources panel (right, ~300px), divided by a `1px` internal border.

### Chat Area

**Session timestamp** — centered, muted:
`Session started: Oct 24, 09:41 AM`

**User message bubble:**
- Right-aligned
- Background: `#E8E8F8` (light lavender)
- Max-width: 65%, padding `16px 20px`
- Border-radius: `16px 16px 4px 16px`

**Assistant message card:**

```
+----------------------------------------------------------+
|  [AI icon]  Analysis & Proposed Enterprise Strategy      |
|                                                          |
|  [Main answer paragraph]                                 |
|                                                          |
|  +------------------------------------------------------+|
|  |  CITED EVIDENCE                                      ||
|  |  [Q2-Revenue.csv]  [Enterprise_Feedback.pdf]        ||
|  +------------------------------------------------------+|
|                                                          |
|  INTERPRETATION                                          |
|  [paragraph]                                             |
|                                                          |
|  +------------------------------------------------------+|
|  |  [bulb] RECOMMENDED ACTION           (indigo tint)  ||
|  |  [paragraph]                                        ||
|  +------------------------------------------------------+|
|                                                          |
|  [View Sources]  [View Trace]  [Generate Decision Brief] |
+----------------------------------------------------------+
```

**Input bar (pinned to bottom of chat area):**

```
+----------------------------------------------------------+
|  [clip] [mic]  Ask a strategic question or type '/'  [^] |
|  [/decision-brief]  [/sources]  [/trace]                 |
+----------------------------------------------------------+
  Copilot can make mistakes. Consider verifying.
```

### Sources Panel (right, inside white card)

```
+---------------------+
|  Sources Used       |
|                     |
|  +---------------+ ||
|  | [pdf] Q3_Fin. | ||
|  |  Finance  [1] | ||
|  |  "quote..."   | ||
|  +---------------+ ||
|                     |
|  +---------------+ ||
|  | [csv] CRM_Pi. | ||
|  |  Sales   [2]  | ||
|  |  "quote..."   | ||
|  +---------------+ ||
|                     |
|  Trace Reference > ||
|  Drafted Briefs  > ||
+---------------------+
```

---

## Page 2: Source Data

**White card internal layout**: full width, no column split.

### Inside the white card:

**Header row:**
```
Source Library                          [+ Add New Data]
Single source of truth for company context
```

**Stats cards row — 4 cards:**
```
+---------------+  +---------------+  +---------------+  +---------------+
| Total Sources |  | Ready         |  | Processing    |  | Failed        |
|  1,248        |  |  1,192        |  |  45           |  |  11           |
| (no accent)   |  | (blue left bar|  |(amber left bar|  |(red left bar) |
+---------------+  +---------------+  +---------------+  +---------------+
```
Each stat card: white bg inner card with `12px` radius, `4px` colored left accent bar.

**Filter bar:**
```
[search sources...]  [Team v]  [Category v]  [Period v]  [Type v]  [Status v]
```

**Table:**
```
File                          Team          Category    Period    Status    Actions
Q3_Marketing_Perf.pdf         Marketing     Campaigns   Q3 2023   * Ready   [...]
User_Engagement_Metrics.csv   Product       Analytics   Oct 2023  ~ Process
Competitor_Analysis.pdf       Business      Strategy    Q3 2023   x Failed
Financial_Forecast.csv        Data Anal.    Finance     FY24      ^ Upload
```
Pagination: `Showing 1 to 4 of 1,248 sources`   `< Page 1 of 312 >`

---

## Page 3: Visualization Data

**White card internal layout**: full width, no column split.

### Inside the white card:

**Header row:**
```
AI-Curated Insight Board    [Team: Executive v] [Category v] [Period: YTD 2023 v]
Synthesized intelligence from connected CSV and PDF data sources.
```

**KPI cards — 3 in a row:**
```
+----------------------+  +----------------------+  +----------------------+
|  TOTAL REVENUE       |  |  OPERATING MARGIN    |  |  NET RETENTION       |
|  $42.8M  ^ +12.4%   |  |  24.2%   v -1.1%    |  |  118%    ^ +3.0%    |
|  [description text]  |  |  [description text]  |  |  [description text]  |
|  [source] [Ask Chat] |  |  [source] [Ask Chat] |  |  [source] [Ask Chat] |
+----------------------+  +----------------------+  +----------------------+
```

**Revenue Growth Chart — full width:**
```
+----------------------------------------------------------------------+
|  Revenue Growth Trajectory                      [download] [expand]  |
|  Monthly actuals vs projected baseline                               |
|  [bar + line combo chart, indigo colors]                             |
|  [bulb] Key Insight: ...                            [Ask in Chat ->] |
+----------------------------------------------------------------------+
```

**PDF Insight Board card:**
```
+----------------------------------------------------------------------+
| (indigo 3px left border)                                             |
|  [pdf] Strategic Analysis Summary               SOURCE: FILE.PDF     |
|                                                                      |
|  KEY FINDINGS                                                        |
|  * finding 1                                                         |
|  * finding 2                                                         |
|                                                                      |
|  [x IDENTIFIED RISKS — red tinted box]                               |
|  [* OPPORTUNITIES — green tinted box]                                |
+----------------------------------------------------------------------+
```

---

## Status Badge Reference

| Status | Background | Text | Icon |
|---|---|---|---|
| Ready | `#DCFCE7` | `#16A34A` | filled circle |
| Processing | `#FEF3C7` | `#D97706` | spinner |
| Uploaded | `#DBEAFE` | `#2563EB` | upload arrow |
| Failed | `#FEE2E2` | `#DC2626` | cancel circle |

## Decision Brief Badges

| Recommendation | Color |
|---|---|
| Go | Green filled pill |
| No-Go | Red filled pill |
| Validate First | Amber filled pill |

Approval status: segmented group — `Draft` · `Reviewed` · `Approved` · `Rejected`
