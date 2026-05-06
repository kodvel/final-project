# Tailwind Token Mapping Plan

This document defines the first refactor pass for frontend Tailwind classes in `apps/web`.

Goal: replace repeated hardcoded color and font classes with semantic Tailwind tokens backed by CSS variables in `apps/web/src/app.css`.

## Scope

- Refactor only the frontend Tailwind app: `apps/web`.
- Refactor colors and fonts first.
- Do not refactor spacing, layout, sizing, or border radius yet.
- Preserve visual fidelity with the existing design references.

## Token strategy

Use semantic tokens in component and route class names.

Prefer:

```tsx
className="bg-primary text-primary-foreground border-border font-heading"
```

Avoid:

```tsx
className="bg-[#4F46E5] text-white border-[#E8EAEF] font-[family-name:var(--font-heading)]"
```

Keep Tailwind v4 CSS-first configuration. Define CSS variables in `:root` and expose them through `@theme inline` in `apps/web/src/app.css`.

## Existing semantic tokens

These tokens already exist in `apps/web/src/app.css` and should be used before adding new tokens.

| Current hardcoded class | Preferred class | CSS variable |
| --- | --- | --- |
| `bg-[#FFFFFF]`, `bg-white` | `bg-background`, `bg-card`, or `bg-popover` | `--background`, `--card`, `--popover` |
| `text-[#111827]` | `text-foreground` | `--foreground` |
| `text-[#6B7280]` | `text-muted-foreground` | `--muted-foreground` |
| `bg-[#4F46E5]` | `bg-primary` | `--primary` |
| `text-[#4F46E5]` | `text-primary` or `text-accent-foreground` | `--primary`, `--accent-foreground` |
| `text-white`, `text-[#FFFFFF]` on primary backgrounds | `text-primary-foreground` | `--primary-foreground` |
| `bg-[#EEF2FF]` | `bg-accent` | `--accent` |
| `text-[#DC2626]` | `text-destructive` | `--destructive` |
| `border-[#E8EAEF]` | `border-border` | `--border` |
| `ring-[#4F46E5]` | `ring-ring` | `--ring` |
| `bg-[#12151C]` | `bg-sidebar` | `--sidebar` |
| `text-[#8B95A8]` | `text-sidebar-foreground` | `--sidebar-foreground` |
| `bg-[#1f1f28]` | `bg-sidebar-accent` | `--sidebar-accent` |
| `text-[#FFFFFF]` inside sidebar active item | `text-sidebar-accent-foreground` | `--sidebar-accent-foreground` |

## Font mapping

Use the existing Tailwind font tokens.

| Current class | Preferred class | Token |
| --- | --- | --- |
| `font-[family-name:var(--font-heading)]` | `font-heading` | `--font-heading` |
| `font-[family-name:var(--font-body)]` | `font-body` | `--font-body` |
| `font-[family-name:var(--font-mono)]` | `font-mono` | `--font-mono` |

## Proposed new semantic tokens

Add these only when they replace repeated hardcoded values that do not map cleanly to existing shadcn tokens.

| Design value | Proposed CSS variable | Proposed Tailwind class | Use case |
| --- | --- | --- | --- |
| `#F9FAFB` | `--surface-subtle` | `bg-surface-subtle` | Light muted page sections, table rows, empty states |
| `#9CA3AF` | `--text-hint` | `text-text-hint` | Low-emphasis hints, timestamps, placeholder-like text |
| `#DCFCE7` | `--status-ready-bg` | `bg-status-ready` | Ready/success badge background |
| `#16A34A` | `--status-ready-fg` | `text-status-ready-foreground` | Ready/success badge text or icon |
| `#FEF3C7` | `--status-processing-bg` | `bg-status-processing` | Processing/warning badge background |
| `#D97706` | `--status-processing-fg` | `text-status-processing-foreground` | Processing/warning badge text or icon |
| `#FEE2E2` | `--status-failed-bg` | `bg-status-failed` | Failed/danger badge background |
| `#DC2626` | `--status-failed-fg` | `text-status-failed-foreground` | Failed/danger badge text or icon |
| `#DBEAFE` | `--status-info-bg` | `bg-status-info` | Info badge background |
| `#2563EB` | `--status-info-fg` | `text-status-info-foreground` | Info badge text or icon |

Implementation shape in `@theme inline`:

```css
--color-surface-subtle: var(--surface-subtle);
--color-text-hint: var(--text-hint);
--color-status-ready: var(--status-ready-bg);
--color-status-ready-foreground: var(--status-ready-fg);
```

Implementation shape in `:root`:

```css
--surface-subtle: #F9FAFB;
--text-hint: #9CA3AF;
--status-ready-bg: #DCFCE7;
--status-ready-fg: #16A34A;
```

## Refactor order

1. Update `apps/web/src/app.css` with missing semantic variables and `@theme inline` mappings.
2. Replace hardcoded color and font classes in `apps/web/src/components/layout/sidebar.tsx`.
3. Replace hardcoded color and font classes in `apps/web/src/routes/chat.tsx`.
4. Replace hardcoded color and font classes in `apps/web/src/routes/source-data.tsx`.
5. Replace hardcoded color and font classes in `apps/web/src/routes/visualization-data.tsx`.
6. Run frontend checks.
7. Do a quick visual review against the design references.

## Acceptance criteria

- Common hardcoded hex classes are removed from frontend routes and sidebar.
- Existing shadcn/ui classes keep working.
- Fonts use `font-heading`, `font-body`, and `font-mono` instead of arbitrary font-family classes.
- The UI looks the same after the refactor.
- A future color change can be made from `apps/web/src/app.css` instead of many component files.
