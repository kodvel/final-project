---
name: Executive Briefcase Design System
colors:
  surface: '#fcf8ff'
  surface-dim: '#dcd8e5'
  surface-bright: '#fcf8ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f5f2ff'
  surface-container: '#f0ecf9'
  surface-container-high: '#eae6f4'
  surface-container-highest: '#e4e1ee'
  on-surface: '#1b1b24'
  on-surface-variant: '#464555'
  inverse-surface: '#302f39'
  inverse-on-surface: '#f3effc'
  outline: '#777587'
  outline-variant: '#c7c4d8'
  surface-tint: '#4d44e3'
  primary: '#3525cd'
  on-primary: '#ffffff'
  primary-container: '#4f46e5'
  on-primary-container: '#dad7ff'
  inverse-primary: '#c3c0ff'
  secondary: '#545d80'
  on-secondary: '#ffffff'
  secondary-container: '#cdd5ff'
  on-secondary-container: '#535c7f'
  tertiary: '#7e3000'
  on-tertiary: '#ffffff'
  tertiary-container: '#a44100'
  on-tertiary-container: '#ffd2be'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#e2dfff'
  primary-fixed-dim: '#c3c0ff'
  on-primary-fixed: '#0f0069'
  on-primary-fixed-variant: '#3323cc'
  secondary-fixed: '#dce1ff'
  secondary-fixed-dim: '#bcc5ee'
  on-secondary-fixed: '#101939'
  on-secondary-fixed-variant: '#3d4567'
  tertiary-fixed: '#ffdbcc'
  tertiary-fixed-dim: '#ffb695'
  on-tertiary-fixed: '#351000'
  on-tertiary-fixed-variant: '#7b2f00'
  background: '#fcf8ff'
  on-background: '#1b1b24'
  surface-variant: '#e4e1ee'
  app-bg: '#F8F7FC'
  main-surface: '#FFFFFF'
  raised-surface: '#FBFAFF'
  sidebar-surface: '#F4F2FA'
  text-primary: '#151826'
  text-secondary: '#626A7C'
  text-muted: '#8A91A3'
  accent-indigo: '#4F46E5'
  accent-navy: '#111A3A'
  status-positive: '#0F9F8F'
  status-warning: '#D97706'
  status-critical: '#E11D48'
  status-processing: '#0284C7'
  border-subtle: '#E5E2F0'
typography:
  app-title:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '600'
    lineHeight: '1.2'
    letterSpacing: -0.02em
  section-title:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: '1.4'
  card-title:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '600'
    lineHeight: '1.4'
  body:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: '1.6'
  metadata:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '500'
    lineHeight: '1.4'
  badge:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '500'
    lineHeight: '1'
    letterSpacing: 0.01em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  base: 8px
  page-padding: 32px
  card-padding: 24px
  table-cell-y: 14px
  gutter: 24px
---

# DESIGN.md: Company Intelligence Copilot

## Purpose

This file is the UI/UX source of truth for Company Intelligence Copilot. Use it in Google Stitch to generate consistent desktop web screens.

The product is a chat-first company intelligence workspace. It helps founders, product leads, marketing teams, data analysts, and business teams turn uploaded company sources into strategic decisions.

Do not design this as a generic analytics dashboard. The app should feel like a strategic consultant workspace where company memory, evidence, insights, and decision briefs live together.

## Stitch Generation Rules

Use this file as the design system context before generating screens.

Generate one screen or one focused flow at a time. Keep the visual language consistent across all screens.

Every Stitch prompt should include:

1. **Anatomy**: desktop web layout, sidebar, content zones, cards, drawers, tables, or chat thread.
2. **Vibe**: Executive Briefcase, calm, strategic, premium, high-trust, modern B2B SaaS.
3. **Content**: realistic company intelligence data, source labels, citations, processing states, insight cards, and decision brief sections.

## Product Vibe

### Style Name

**Executive Briefcase**

### Description

A premium desktop workspace for strategic company decisions. It combines the clarity of an executive briefing, the speed of an AI copilot, and the structure of a company memory system.

The interface should feel:

- Strategic, not generic.
- Calm, not sleepy.
- Intelligent, not gimmicky.
- Premium, not decorative.
- Data-grounded, not dashboard-heavy.
- Editorial, not admin-like.

### Mental Model

The user is not operating a BI tool. The user is consulting with an AI Company Strategy Consultant that has access to uploaded company sources.

The app should make these ideas visible:

- Source data becomes company memory.
- Visualization data becomes curated understanding.
- Chat becomes strategic discussion.
- Decision Briefs become shareable decision artifacts.
- Sources, gaps, assumptions, and traces make the AI trustworthy.

## Platform

Design for **desktop web only**.

Use responsive-aware spacing, but do not optimize for mobile screens. Prioritize wide layouts, long chat threads, dense source tables, charts, and right-side contextual drawers.

Recommended canvas width: 1440px.

## Theme

Default theme: **light premium with dark strategic accents**.

Use soft light surfaces for readability. Use dark slate, navy, and indigo-violet for authority. Use warm amber for risk or priority. Use teal for positive movement and validated insight.

Avoid full dark mode as the primary direction. Avoid loud neon AI aesthetics.

## Color System

Use semantic color roles, not random decorative colors.

### Core Palette

- **App Background**: warm white or very pale lavender, `#F8F7FC` or similar.
- **Main Surface**: white, `#FFFFFF`.
- **Raised Surface**: pale lavender-white, `#FBFAFF`.
- **Sidebar Surface**: near-white with subtle lavender tint, `#F4F2FA`.
- **Primary Text**: deep slate, `#151826`.
- **Secondary Text**: slate gray, `#626A7C`.
- **Muted Text**: cool gray, `#8A91A3`.
- **Primary Accent**: indigo-violet, `#4F46E5`.
- **Dark Strategic Accent**: navy, `#111A3A`.
- **Positive Insight**: teal, `#0F9F8F`.
- **Warning / Priority**: amber, `#D97706`.
- **Risk / Failed**: rose, `#E11D48`.
- **Processing**: sky blue, `#0284C7`.
- **Border**: soft lavender gray, `#E5E2F0`.

### Usage Rules

- Use indigo-violet for primary actions, active navigation, selected filters, and highlighted AI actions.
- Use navy for strong headings, executive emphasis, right drawer headers, Decision Brief headers, and optional dark sidebar accents.
- Use teal for ready states, positive metrics, confidence, and validated insights.
- Use amber for assumptions, warnings, priority, and "Validate First".
- Use rose only for failed processing, high risk, contradictions, and destructive actions.
- Keep backgrounds quiet. Let content hierarchy create interest.

## Typography

Use a clean, modern sans-serif system.

Recommended fonts:

- Primary: Inter, Geist, or a similar modern sans-serif.
- Numeric data: use tabular numerals where possible.

### Type Hierarchy

- **App title / page title**: 28-34px, semibold, tight line-height.
- **Section title**: 18-22px, semibold.
- **Card title**: 15-17px, semibold.
- **Body**: 14-15px, regular.
- **Small metadata**: 12-13px, medium.
- **Badges / chips**: 11-12px, medium.

Use strong hierarchy inside AI answers and Decision Briefs. These should scan like strategic memos, not chat bubbles.

## Spacing and Shape

- Use an 8px spacing rhythm.
- Page padding: 24-32px.
- Card padding: 18-24px.
- Dense table cells: 12-16px vertical rhythm.
- Main card radius: 18-24px.
- Small controls radius: 10-14px.
- Pills and chips: fully rounded or 999px radius.
- Shadows should be soft and rare.
- Prefer subtle borders plus light elevation over heavy shadows.

## Layout System

### Global Shell

Use a desktop app shell with:

1. **Collapsible slim left sidebar**.
2. **Top header inside main area**.
3. **Main content canvas**.
4. **Optional right drawer for contextual details**.

### Left Sidebar

The sidebar is the main navigation, but it must stay MVP-only and lightweight.

Use a quiet light sidebar by default. Use navy as an optional compact accent in the brand area, collapsed sidebar state, or active navigation marker so the shell feels strategic without becoming dark-mode heavy.

Expanded state:

- Brand mark and product name.
- Workspace switcher.
- Main nav with icon + label.
- Secondary items at bottom.

Collapsed state:

- Icon-only navigation.
- Tooltip on hover.
- Workspace shown as compact avatar or initials.

Main nav items only:

1. **Chat**
2. **Visualization Data**
3. **Source Data**

Secondary bottom items:

- Help
- Settings

Do not add these as primary nav items:

- Intelligence
- Briefs
- Observability
- Strategy
- Workspace

Workspace switching must remain lightweight. It can live near the top of the sidebar or header, but it must not become a dedicated page.

### Header

Each page should have a compact header with:

- Page title.
- Short context subtitle.
- Active workspace indicator.
- Optional global search.
- Optional utility icons.
- Primary action when needed.

Keep the header calm. Do not overload it with dashboard controls.

## Core Pages

### 1. Chat

Chat is the default page and the primary product surface.

#### Page Purpose

Let users discuss strategy with an AI Company Strategy Consultant grounded in uploaded sources.

#### Layout

Use a three-zone chat workspace:

1. **Left sidebar**: app navigation. When Chat is active, it may show a compact chat session list below the main nav.
2. **Main center**: conversation thread and composer.
3. **Right context drawer**: Sources, Trace, Brief details, and Gaps.

The right drawer is collapsed by default. Show a narrow evidence rail on the right side of the conversation.

Evidence rail items:

- Sources used
- Trace
- Brief
- Gaps

Clicking an item opens the drawer.

#### Chat Thread

Use a GPT-style thread, but make assistant responses feel like consultant memo cards.

User messages can be simple chat bubbles. Assistant messages should be structured cards.

#### Assistant Response Card

Use this structure by default:

1. **Direct Answer**
2. **Evidence**
3. **Interpretation**
4. **Recommendation / Next Step**
5. **Confidence + Gaps**

Footer actions:

- View Sources
- View Trace
- Generate Decision Brief

Visual rules:

- Give each section a clear label.
- Use source citation chips inside Evidence.
- Use confidence as a badge or compact meter.
- Show gaps in amber or muted warning styling.
- Show contradictions in rose with a calm warning tone.

#### Composer

The composer sits at the bottom of the main chat column.

Include:

- Text input.
- Slash command hint: `/decision-brief`, `/sources`, `/trace`.
- Attachment/source context affordance if needed.
- Send button.

Placeholder examples:

- "Ask about feature prioritization, risks, or what changed this month..."
- "Type `/decision-brief` to turn this discussion into an executive memo..."

#### Right Drawer

Drawer modes:

1. **Sources Used**: list source files, labels, periods, quotes, artifacts, and confidence.
2. **Execution Trace**: Langfuse trace reference, tool calls, latency, model, status.
3. **Decision Brief Details**: brief metadata and approval status.
4. **Gaps & Assumptions**: missing data, unsupported assumptions, contradictions.

Do not show trace details persistently. The drawer should support trust without distracting from the conversation.

Use a navy-tinted drawer header or top border to make the drawer feel like a serious evidence layer, not a generic side panel.

#### Empty State

The empty Chat state should invite strategic work.

Include suggested prompts:

- "What changed this month?"
- "Which feature should we build next?"
- "What risks should we validate before launch?"
- "Generate a decision brief from the current evidence."

Also show a small source readiness summary:

- Ready sources
- Processing sources
- Latest uploaded source

### 2. Decision Brief in Chat

Decision Briefs are not separate pages. Render them as premium document cards inside the chat thread.

#### Visual Form

The Decision Brief should look like an executive memo embedded in the conversation.

Use a navy-tinted header band or left accent rule to separate the brief from normal assistant answers.

Header:

- Decision Title
- Recommendation status badge: Go, No-Go, or Validate First
- Approval status badge: Draft, Reviewed, Approved, or Rejected

Sections:

1. Context / Problem
2. Source Evidence
3. Strategic Interpretation
4. Recommendation
5. Alternatives Considered
6. Risks & Assumptions
7. Success Metrics
8. Next Steps

Footer actions:

- View Sources
- View Trace
- Copy Brief
- Update Status

#### Status Styling

- **Go**: teal.
- **No-Go**: rose.
- **Validate First**: amber.
- **Draft**: muted gray.
- **Reviewed**: indigo.
- **Approved**: teal.
- **Rejected**: rose.

Decision Briefs must feel shareable and polished, but still clearly AI-generated drafts.

### 3. Visualization Data

#### Page Name

Use the nav label **Visualization Data**.

The page itself can use the title **AI-Curated Insight Board**.

#### Page Purpose

Show automatically generated understanding from uploaded CSV and PDF sources.

This page is not a manual BI dashboard. It is a curated insight board.

#### Layout

Top area:

- Page title.
- Subtitle: "Automatically generated visual stories and document intelligence from ready sources."
- Filters: Team, Category, Period.
- Optional search.

Main area:

- Source-based card feed or grid.
- Each ready source becomes an insight board section.

#### CSV Visual Story

For CSV sources, show a visual story in this order:

1. **Executive Summary Cards**: row count, key metric, trend, anomaly count.
2. **Trend Explorer**: line or area chart when time columns exist.
3. **Segment Breakdown**: bar or stacked chart when category columns exist.
4. **Relationship View**: scatter or correlation-style panel when numeric columns exist.
5. **Anomaly Highlights**: spikes, drops, outliers.
6. **Auto Insight Cards**: plain-language explanations.

If a section is unsupported by the data, show a quiet unavailable state instead of forcing a chart.

Example unavailable copy:

"No time column detected, so trend analysis is unavailable for this source."

#### PDF Document Intelligence Board

For PDF sources, do not force charts. Show a document intelligence board with:

1. Document Summary
2. Key Findings
3. Assumptions
4. Risks
5. Opportunities
6. Source Quotes

Use quote cards with page numbers when available.

#### Card Style

Cards should feel like curated intelligence artifacts.

Use:

- Clear title.
- Source metadata chips.
- Period chip.
- Team chip.
- Category chips.
- Confidence or freshness metadata when relevant.
- Small action: Ask in Chat.

Avoid dense chart dashboards with many competing widgets.

### 4. Source Data

#### Page Name

Use the nav label **Source Data**.

The page title should be **Source Library**.

Subtitle:

"Single source of truth for company context."

#### Page Purpose

Let users upload, label, inspect, and manage company source files.

#### Layout

Header:

- Title: Source Library
- Subtitle

Primary action:

- Add New Data

Summary cards:

- Total Sources
- Processing
- Ready
- Failed

Filter/search row:

- Search sources
- Team filter
- Category filter
- Period filter
- Type filter
- Status filter

Table columns:

- File
- Team
- Categories
- Period
- Type
- Status
- Uploaded
- Actions

#### Status Badges

- Uploaded: muted gray or soft indigo.
- Processing: sky blue with subtle motion or progress.
- Ready: teal.
- Failed: rose.

Failed row actions:

- Retry
- Replace

#### Add New Data Dialog

Use a focused modal or side sheet.

Fields:

- File upload: CSV or PDF only.
- Title.
- Team label: Marketing, Product, Data Analysis, Business.
- Category labels: multi-select.
- Period start.
- Period end.
- Period label.

Category options:

- Analytics / Metrics
- Market Research
- Product / Feature
- Customer Insight
- Business Model
- Competitor Analysis
- Revenue / Sales

Upload interaction:

- Drag and drop zone.
- File type hint.
- Clear validation errors.
- Submit button: Add Data.

After upload, show Uploaded status and processing progress in the table.

## Components

### Cards

Use cards as the main content container.

Card types:

- Consultant answer card.
- Decision Brief card.
- Insight card.
- Chart card.
- PDF quote card.
- Source summary card.
- Status metric card.

Cards should use white or pale lavender surfaces, subtle borders, rounded corners, and restrained elevation.

### Chips and Badges

Use chips for source metadata:

- Team
- Category
- Period
- File type
- Source title
- Status
- Confidence

Chips should be compact and readable. Avoid bright saturated backgrounds.

### Tables

Tables should be clean and calm.

Use:

- Sticky or clear table header.
- Soft row dividers.
- Status badges.
- Truncated filenames with hover or tooltip.
- Row actions on the right.

Avoid heavy grid lines.

### Charts

Charts must support storytelling.

Use:

- Clear chart title.
- Plain-language insight near the chart.
- Highlighted anomaly points.
- Muted axes and grid lines.
- Minimal color palette.

Do not use charts as decoration. If the data does not support a chart, show a clear unsupported state.

### Drawers

Use drawers for contextual detail, not primary navigation.

Drawer types:

- Source details.
- Trace details.
- Evidence list.
- Gaps and assumptions.

Drawers should slide from the right and keep the user in context.

### Empty States

Empty states should guide the next action.

Examples:

- Chat: suggested strategic prompts.
- Visualization: "Upload CSV or PDF sources to generate your first insight board."
- Source Data: "Add your first company source to start building company memory."

### Loading and Processing States

Show progress without overpromising.

Use:

- Processing badge.
- Skeleton cards.
- Small progress indicator.
- Plain-language status copy.

Example copy:

- "Extracting PDF insights..."
- "Profiling CSV columns..."
- "Indexing source for chat retrieval..."

### Error States

Errors should be calm and actionable.

For failed processing, show:

- What failed.
- Why, when known.
- Retry action.
- Replace file action.

Example copy:

"Processing failed because the file could not be parsed. Retry or replace the source with a valid CSV/PDF."

## Interaction Principles

### Chat First

The app should always make it easy to return to Chat. Chat is where users ask, compare, challenge, and decide.

### Source Grounding

AI answers must show their basis.

Always include visible access to:

- Sources used.
- Citations or quotes.
- Confidence.
- Gaps.
- Trace reference.

### Scope Override

Users can override source scope in natural language. The UI should support this with subtle reminders and source chips.

Examples:

- "Using all relevant sources"
- "Scoped to Product · Q3 2024"
- "Scoped to Market Research + Competitor Analysis"

### No Manual BI Builder

Users do not build dashboards. The system generates visual stories and insight boards automatically.

### Transparency Without Clutter

Observability matters for the demo, but it should not dominate the interface. Trace details should live in a drawer or popover triggered by View Trace.

## UX Copy Tone

Use concise, confident, plain language.

Tone:

- Strategic
- Clear
- Evidence-aware
- Calm
- Non-hype

Avoid:

- Overly playful copy.
- Generic AI hype.
- Vague promises.
- Enterprise jargon overload.

Good examples:

- "Proceed with caution. The evidence supports demand, but operational readiness is weak."
- "No customer insight source was available for this period. Treat this as an assumption."
- "3 sources used"
- "View trace"
- "Generate Decision Brief"

## Screen-Specific Stitch Prompts

Use these prompts after loading this DESIGN.md into Stitch.

### Prompt: Chat Screen

Design the desktop web Chat screen for Company Intelligence Copilot using the Executive Briefcase design system. Create a strategic consultant workspace, not a generic chatbot. Use a collapsible slim left sidebar with only Chat, Visualization Data, and Source Data. Chat is active. The main center area shows a conversation with user messages and structured assistant answer cards. Assistant cards include Direct Answer, Evidence, Interpretation, Recommendation / Next Step, and Confidence + Gaps. Add citation chips, View Sources, View Trace, and Generate Decision Brief actions. On the far right, show a collapsed evidence rail with Sources used, Trace, Brief, and Gaps. Include a bottom composer with slash command hints for `/decision-brief`, `/sources`, and `/trace`. Use light premium surfaces, slate/navy text, indigo-violet primary accents, amber warning chips, and teal confidence states.

### Prompt: Decision Brief in Chat

Design a desktop web chat state where the AI has generated a Decision Brief as a premium document card inside the chat thread. Keep the same Executive Briefcase layout. The brief card should look like a polished executive memo with a Decision Title, Go / No-Go / Validate First recommendation badge, Draft / Reviewed / Approved / Rejected approval badge, and sections for Context / Problem, Source Evidence, Strategic Interpretation, Recommendation, Alternatives Considered, Risks & Assumptions, Success Metrics, and Next Steps. Include footer actions for View Sources, View Trace, Copy Brief, and Update Status. Show the right evidence rail collapsed.

### Prompt: Visualization Data Screen

Design the desktop web Visualization Data screen as an AI-Curated Insight Board, not a BI dashboard. Use the Executive Briefcase design system with a collapsible left sidebar and light premium surfaces. The page has filters for Team, Category, and Period. Show source-based insight sections. Include one CSV Visual Story with executive summary cards, trend explorer, segment breakdown, anomaly highlights, and auto insight cards. Include one PDF Document Intelligence Board with summary, key findings, assumptions, risks, opportunities, and source quote cards. Use metadata chips for team, category, period, and source type. Add small Ask in Chat actions on insight cards.

### Prompt: Source Data Screen

Design the desktop web Source Data screen as Source Library. Subtitle: "Single source of truth for company context." Use the Executive Briefcase design system. Include a collapsible slim left sidebar with Source Data active. The page header includes an Add New Data primary button. Add summary cards for Total Sources, Processing, Ready, and Failed. Add search and filters for team, category, period, type, and status. Show a clean source table with columns File, Team, Categories, Period, Type, Status, Uploaded, and Actions. Use badges for Uploaded, Processing, Ready, and Failed. Failed rows should show Retry and Replace actions.

### Prompt: Add New Data Dialog

Design the Add New Data dialog or side sheet for Source Library. It should feel focused and lightweight. Include a drag-and-drop upload area for CSV or PDF, title field, team label selector, multi-select category labels, period start, period end, period label, and Add Data button. Include validation hints and file type guidance. Use the same light premium Executive Briefcase design system.

## Do and Do Not

### Do

- Make Chat the default and strongest surface.
- Use the left sidebar, but keep it slim, collapsible, and MVP-only.
- Make AI answers structured and scannable.
- Make sources and trace visible through actions and drawers.
- Make Visualization Data feel curated by AI.
- Make Source Data feel like a reliable library.
- Use realistic business/product/marketing/data labels.
- Include processing, ready, failed, empty, and unsupported states.

### Do Not

- Do not make the app look like a generic analytics dashboard.
- Do not add extra primary nav items outside Chat, Visualization Data, and Source Data.
- Do not make Observability or Strategy separate primary pages.
- Do not make Decision Briefs a separate MVP page.
- Do not force PDF data into charts.
- Do not use neon AI visuals, excessive gradients, or decorative 3D illustrations.
- Do not hide source grounding behind vague copy.
