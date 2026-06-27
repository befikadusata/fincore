# FinCore UI Design System

> **Version**: 1.0 | **Status**: Implementation-Ready | **Stack**: Next.js + Tailwind CSS + CSS Variables

---

## 1. Design Philosophy

### 1.1 Visual Identity

FinCore serves credit officers, loan administrators, and tenant admins inside African fintech businesses. The interface must project **institutional trust** — not startup minimalism — while remaining fast enough for a solo developer to implement correctly the first time.

**Four guiding principles:**

**Precision over decoration.** Financial data demands clarity. Every visual element earns its place by making numbers, statuses, and actions faster to parse — not by expressing brand personality.

**Status is the product.** In a loan management platform, every entity — a loan, a repayment, a workflow step — lives in a state. The design system treats status rendering as a first-class concern: colour, badge, and icon work together so a user can scan a list and grasp portfolio health in seconds.

**Progressive disclosure.** Dense data is unavoidable. Reveal it in layers: summary cards → list rows → detail drawers → full pages. Never dump everything on one screen.

**Dark mode by design, not by patch.** Dark mode is architected with semantic tokens so it is not an afterthought layer of colour overrides. Both modes share identical spacing, type, and component shapes — only the colour layer switches.

### 1.2 Aesthetic Direction

**Palette origin:** The palette is drawn from traditional Ethiopian printed ledgers — ink-dense midnight columns, warm cream paper, a ochre-amber accent for urgency. This grounds the product in its geographic and financial context rather than borrowing from Silicon Valley SaaS defaults.

**Typography:** A precise geometric sans (`Inter`) for all interface text paired with a tabular monospace (`JetBrains Mono`) for every number, ID, and amount. This is the signature choice: numbers that align perfectly in tables, always instantly legible, without switching to a serif "financial" face.

**Signature element:** The **Status Rail** — a 3px left border on every card and list row, coloured by entity status. It creates instant visual rhythm across dashboards without icons or badges competing for attention.

---

## 2. Token Architecture

Tokens are structured in three layers. You override only the layer you need.

```
Base Tokens         →  raw values (hex, px, rem, ms)
  ↓
Semantic Tokens     →  purpose-mapped aliases (use these in components)
  ↓
Component Tokens    →  per-component overrides (rarely needed)
```

**Rule:** Components reference semantic tokens only — never base tokens directly. This makes theme switching and white-labelling trivial.

---

## 3. Color System

### 3.1 Base Palette (raw values)

```css
/* Neutrals — Midnight Ink scale */
--base-neutral-0:   #FFFFFF;
--base-neutral-50:  #F8F9FA;
--base-neutral-100: #F1F3F5;
--base-neutral-200: #E9ECEF;
--base-neutral-300: #DEE2E6;
--base-neutral-400: #CED4DA;
--base-neutral-500: #ADB5BD;
--base-neutral-600: #6C757D;
--base-neutral-700: #495057;
--base-neutral-800: #343A40;
--base-neutral-900: #212529;
--base-neutral-950: #141618;

/* Brand — Amber Ledger */
--base-amber-100: #FFF3CD;
--base-amber-200: #FFE69C;
--base-amber-400: #FFC107;
--base-amber-500: #E6AC00;
--base-amber-600: #CC9A00;
--base-amber-800: #7D5F00;

/* Status palette */
--base-green-100: #D1FAE5;
--base-green-500: #10B981;
--base-green-700: #047857;

--base-blue-100:  #DBEAFE;
--base-blue-500:  #3B82F6;
--base-blue-700:  #1D4ED8;

--base-orange-100: #FFEDD5;
--base-orange-500: #F97316;
--base-orange-700: #C2410C;

--base-red-100:  #FEE2E2;
--base-red-500:  #EF4444;
--base-red-700:  #B91C1C;

--base-purple-100: #EDE9FE;
--base-purple-500: #8B5CF6;
--base-purple-700: #6D28D9;

--base-gray-100: #F3F4F6;
--base-gray-400: #9CA3AF;
--base-gray-600: #4B5563;
```

### 3.2 Semantic Tokens — Light Mode

```css
:root {
  /* === Surfaces === */
  --color-bg-page:         var(--base-neutral-50);
  --color-bg-surface:      var(--base-neutral-0);
  --color-bg-elevated:     var(--base-neutral-0);
  --color-bg-sunken:       var(--base-neutral-100);
  --color-bg-overlay:      rgba(0, 0, 0, 0.45);

  /* === Borders === */
  --color-border-default:  var(--base-neutral-200);
  --color-border-strong:   var(--base-neutral-300);
  --color-border-focus:    var(--base-amber-500);

  /* === Text === */
  --color-text-primary:    var(--base-neutral-900);
  --color-text-secondary:  var(--base-neutral-600);
  --color-text-tertiary:   var(--base-neutral-500);
  --color-text-disabled:   var(--base-neutral-400);
  --color-text-inverse:    var(--base-neutral-0);
  --color-text-link:       var(--base-blue-700);
  --color-text-link-hover: var(--base-blue-500);

  /* === Brand / Interactive === */
  --color-brand-default:   var(--base-amber-500);
  --color-brand-hover:     var(--base-amber-600);
  --color-brand-subtle:    var(--base-amber-100);
  --color-brand-text:      var(--base-amber-800);

  /* === Feedback === */
  --color-success-bg:      var(--base-green-100);
  --color-success-border:  var(--base-green-500);
  --color-success-text:    var(--base-green-700);
  --color-success-rail:    var(--base-green-500);

  --color-info-bg:         var(--base-blue-100);
  --color-info-border:     var(--base-blue-500);
  --color-info-text:       var(--base-blue-700);
  --color-info-rail:       var(--base-blue-500);

  --color-warning-bg:      var(--base-orange-100);
  --color-warning-border:  var(--base-orange-500);
  --color-warning-text:    var(--base-orange-700);
  --color-warning-rail:    var(--base-orange-500);

  --color-danger-bg:       var(--base-red-100);
  --color-danger-border:   var(--base-red-500);
  --color-danger-text:     var(--base-red-700);
  --color-danger-rail:     var(--base-red-500);

  --color-neutral-bg:      var(--base-gray-100);
  --color-neutral-border:  var(--base-gray-400);
  --color-neutral-text:    var(--base-gray-600);
  --color-neutral-rail:    var(--base-gray-400);

  --color-purple-bg:       var(--base-purple-100);
  --color-purple-border:   var(--base-purple-500);
  --color-purple-text:     var(--base-purple-700);
  --color-purple-rail:     var(--base-purple-500);
}
```

### 3.3 Semantic Tokens — Dark Mode

```css
[data-theme="dark"] {
  --color-bg-page:         var(--base-neutral-950);
  --color-bg-surface:      var(--base-neutral-900);
  --color-bg-elevated:     var(--base-neutral-800);
  --color-bg-sunken:       var(--base-neutral-950);
  --color-bg-overlay:      rgba(0, 0, 0, 0.65);

  --color-border-default:  var(--base-neutral-800);
  --color-border-strong:   var(--base-neutral-700);
  --color-border-focus:    var(--base-amber-400);

  --color-text-primary:    var(--base-neutral-50);
  --color-text-secondary:  var(--base-neutral-400);
  --color-text-tertiary:   var(--base-neutral-500);
  --color-text-disabled:   var(--base-neutral-700);
  --color-text-inverse:    var(--base-neutral-900);
  --color-text-link:       var(--base-blue-500);
  --color-text-link-hover: var(--base-blue-100);

  --color-brand-default:   var(--base-amber-400);
  --color-brand-hover:     var(--base-amber-500);
  --color-brand-subtle:    rgba(255, 193, 7, 0.12);
  --color-brand-text:      var(--base-amber-200);

  --color-success-bg:      rgba(16, 185, 129, 0.12);
  --color-success-border:  var(--base-green-500);
  --color-success-text:    var(--base-green-500);
  --color-success-rail:    var(--base-green-500);

  --color-info-bg:         rgba(59, 130, 246, 0.12);
  --color-info-border:     var(--base-blue-500);
  --color-info-text:       var(--base-blue-500);
  --color-info-rail:       var(--base-blue-500);

  --color-warning-bg:      rgba(249, 115, 22, 0.12);
  --color-warning-border:  var(--base-orange-500);
  --color-warning-text:    var(--base-orange-500);
  --color-warning-rail:    var(--base-orange-500);

  --color-danger-bg:       rgba(239, 68, 68, 0.12);
  --color-danger-border:   var(--base-red-500);
  --color-danger-text:     var(--base-red-500);
  --color-danger-rail:     var(--base-red-500);

  --color-neutral-bg:      rgba(156, 163, 175, 0.10);
  --color-neutral-border:  var(--base-gray-600);
  --color-neutral-text:    var(--base-gray-400);
  --color-neutral-rail:    var(--base-gray-600);

  --color-purple-bg:       rgba(139, 92, 246, 0.12);
  --color-purple-border:   var(--base-purple-500);
  --color-purple-text:     var(--base-purple-500);
  --color-purple-rail:     var(--base-purple-500);
}
```

### 3.4 Loan Status → Color Mapping

This is the most-used semantic mapping in the entire product. Apply consistently across badges, rails, and status columns.

| Status | Rail / Badge Color | Semantic Token |
|---|---|---|
| `CREATED` | Neutral gray | `--color-neutral-*` |
| `SUBMITTED` | Blue (info) | `--color-info-*` |
| `UNDER_REVIEW` | Purple | `--color-purple-*` |
| `APPROVED` | Green | `--color-success-*` |
| `DISBURSED` | Green (bold) | `--color-success-*` |
| `ACTIVE` | Green | `--color-success-*` |
| `COMPLETED` | Neutral (muted) | `--color-neutral-*` |
| `REJECTED` | Red | `--color-danger-*` |
| `DEFAULTED` | Red (bold) | `--color-danger-*` |
| `OVERDUE` | Orange | `--color-warning-*` |

---

## 4. Typography

### 4.1 Type Scale Tokens

```css
:root {
  /* Font families */
  --font-sans:  'Inter', system-ui, -apple-system, sans-serif;
  --font-mono:  'JetBrains Mono', 'Fira Code', 'Consolas', monospace;

  /* Scale (Major Third — 1.250 ratio) */
  --text-xs:   0.64rem;   /* 10.24px — labels, captions */
  --text-sm:   0.8rem;    /* 12.8px  — helper text, timestamps */
  --text-base: 0.875rem;  /* 14px    — body, table cells */
  --text-md:   1rem;      /* 16px    — primary body */
  --text-lg:   1.125rem;  /* 18px    — section titles */
  --text-xl:   1.25rem;   /* 20px    — card headings */
  --text-2xl:  1.5rem;    /* 24px    — page headings */
  --text-3xl:  1.875rem;  /* 30px    — KPI numbers */
  --text-4xl:  2.25rem;   /* 36px    — hero KPIs */

  /* Weights */
  --font-normal:   400;
  --font-medium:   500;
  --font-semibold: 600;
  --font-bold:     700;

  /* Line heights */
  --leading-tight:  1.25;
  --leading-snug:   1.375;
  --leading-normal: 1.5;
  --leading-relaxed: 1.625;

  /* Tracking */
  --tracking-tight:  -0.025em;
  --tracking-normal:  0em;
  --tracking-wide:    0.05em;
  --tracking-widest:  0.1em;
}
```

### 4.2 Typographic Roles

| Role | Font | Size | Weight | Notes |
|---|---|---|---|---|
| Page heading | sans | `2xl` | semibold | e.g. "Loans", "Dashboard" |
| Section heading | sans | `xl` | semibold | Card titles, drawer headers |
| Body | sans | `base` | normal | Default prose, labels |
| Body strong | sans | `base` | semibold | Table column headers |
| Caption | sans | `sm` | normal | Timestamps, helper text |
| Badge label | sans | `xs` | semibold | Status badges, tags |
| **Amount** | **mono** | **md–3xl** | **semibold** | All currency values |
| **ID / Reference** | **mono** | **sm** | **normal** | Loan IDs, txn refs, UUIDs |
| **Tabular data** | **mono** | **base** | **normal** | Dates, rates, counts in tables |

> **Rule:** Any number that might be compared, summed, or copied uses `--font-mono`. No exceptions.

### 4.3 Tailwind Config

```js
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      fontSize: {
        xs:   ['0.64rem',  { lineHeight: '1.25' }],
        sm:   ['0.8rem',   { lineHeight: '1.375' }],
        base: ['0.875rem', { lineHeight: '1.5' }],
        md:   ['1rem',     { lineHeight: '1.5' }],
        lg:   ['1.125rem', { lineHeight: '1.375' }],
        xl:   ['1.25rem',  { lineHeight: '1.375' }],
        '2xl':['1.5rem',   { lineHeight: '1.25' }],
        '3xl':['1.875rem', { lineHeight: '1.25' }],
        '4xl':['2.25rem',  { lineHeight: '1.1' }],
      },
    },
  },
};
```

---

## 5. Spacing & Layout

### 5.1 Spacing Scale

Uses a base-4 scale (4px grid). All spacing tokens are multiples.

```css
:root {
  --space-0:   0px;
  --space-0-5: 2px;
  --space-1:   4px;
  --space-1-5: 6px;
  --space-2:   8px;
  --space-3:   12px;
  --space-4:   16px;
  --space-5:   20px;
  --space-6:   24px;
  --space-8:   32px;
  --space-10:  40px;
  --space-12:  48px;
  --space-16:  64px;
  --space-20:  80px;
  --space-24:  96px;
}
```

### 5.2 Layout Tokens

```css
:root {
  /* Sidebar */
  --sidebar-width-collapsed: 56px;
  --sidebar-width-expanded:  240px;

  /* Content */
  --content-max-width:   1280px;
  --content-padding-x:  var(--space-6);

  /* Header */
  --header-height: 56px;

  /* Breakpoints (reference only — use Tailwind classes) */
  /* sm: 640px | md: 768px | lg: 1024px | xl: 1280px */

  /* Border radius */
  --radius-sm:   4px;
  --radius-md:   6px;
  --radius-lg:   8px;
  --radius-xl:   12px;
  --radius-full: 9999px;

  /* Shadows */
  --shadow-sm:  0 1px 2px rgba(0,0,0,0.06), 0 1px 3px rgba(0,0,0,0.10);
  --shadow-md:  0 4px 6px rgba(0,0,0,0.07), 0 2px 4px rgba(0,0,0,0.06);
  --shadow-lg:  0 10px 15px rgba(0,0,0,0.10), 0 4px 6px rgba(0,0,0,0.06);
  --shadow-xl:  0 20px 25px rgba(0,0,0,0.10), 0 8px 10px rgba(0,0,0,0.04);

  /* Z-index layers */
  --z-base:    0;
  --z-raised:  10;
  --z-dropdown: 100;
  --z-sticky:  200;
  --z-overlay: 300;
  --z-modal:   400;
  --z-toast:   500;
  --z-tooltip: 600;

  /* Motion */
  --duration-fast:   100ms;
  --duration-normal: 150ms;
  --duration-slow:   250ms;
  --ease-default:    cubic-bezier(0.16, 1, 0.3, 1);
}
```

### 5.3 Page Layout Pattern

```
┌─────────────────────────────────────────────────────────┐
│  HEADER (height: 56px, sticky)                          │
│  [Logo] [Tenant Switcher]         [Notif] [Avatar]      │
├──────────┬──────────────────────────────────────────────┤
│  SIDEBAR │  PAGE CONTENT                                │
│ 240px    │  padding: 24px                               │
│          │                                               │
│ [Nav]    │  ┌──────────────────────────────────────┐    │
│          │  │ PAGE HEADER                          │    │
│          │  │ h1 + actions + breadcrumb            │    │
│          │  └──────────────────────────────────────┘    │
│          │                                               │
│          │  ┌──────────────────────────────────────┐    │
│          │  │ KPI CARDS (3–4 col grid)              │    │
│          │  └──────────────────────────────────────┘    │
│          │                                               │
│          │  ┌──────────────────────────────────────┐    │
│          │  │ DATA TABLE / CONTENT                  │    │
│          │  └──────────────────────────────────────┘    │
│          │                                               │
├──────────┴──────────────────────────────────────────────┤
│  (No footer — infinite scroll or pagination in table)   │
└─────────────────────────────────────────────────────────┘
```

**Mobile (< 768px):** Sidebar collapses to bottom tab bar (5 items max). Content fills full width with 16px horizontal padding.

---

## 6. Component Library

### 6.1 Button

**Variants, sizes, and states:**

```css
/* Component tokens */
.btn {
  --btn-font:        var(--font-sans);
  --btn-font-size:   var(--text-sm);
  --btn-font-weight: var(--font-semibold);
  --btn-radius:      var(--radius-md);
  --btn-transition:  background-color var(--duration-fast) var(--ease-default),
                     box-shadow var(--duration-fast) var(--ease-default);

  display:          inline-flex;
  align-items:      center;
  gap:              var(--space-1-5);
  border-radius:    var(--btn-radius);
  font-family:      var(--btn-font);
  font-size:        var(--btn-font-size);
  font-weight:      var(--btn-font-weight);
  transition:       var(--btn-transition);
  cursor:           pointer;
  border:           1px solid transparent;
  white-space:      nowrap;
}

/* Sizes */
.btn-sm  { padding: var(--space-1-5) var(--space-3); font-size: var(--text-xs); }
.btn-md  { padding: var(--space-2) var(--space-4); }
.btn-lg  { padding: var(--space-3) var(--space-6); font-size: var(--text-md); }

/* Primary — brand amber, dark text */
.btn-primary {
  background: var(--color-brand-default);
  color:      var(--color-text-inverse);
  border-color: var(--color-brand-default);
}
.btn-primary:hover { background: var(--color-brand-hover); }

/* Secondary — outline */
.btn-secondary {
  background:   transparent;
  color:        var(--color-text-primary);
  border-color: var(--color-border-strong);
}
.btn-secondary:hover { background: var(--color-bg-sunken); }

/* Danger */
.btn-danger {
  background: var(--color-danger-bg);
  color:      var(--color-danger-text);
  border-color: var(--color-danger-border);
}
.btn-danger:hover { background: var(--base-red-500); color: white; }

/* Ghost */
.btn-ghost {
  background: transparent;
  color: var(--color-text-secondary);
  border-color: transparent;
}
.btn-ghost:hover { background: var(--color-bg-sunken); color: var(--color-text-primary); }

/* All variants — disabled */
.btn:disabled {
  opacity: 0.45;
  pointer-events: none;
}

/* Focus (accessibility) */
.btn:focus-visible {
  outline: 2px solid var(--color-border-focus);
  outline-offset: 2px;
}
```

**Usage guidance:**
- One `btn-primary` per view. Subsequent primary actions use `btn-secondary`.
- Destructive actions (Reject, Delete) use `btn-danger`, always behind a confirmation dialog.
- Loading state: replace label with spinner + "Processing…", disable the button.

### 6.2 Input & Form Fields

```css
.field {
  display:        flex;
  flex-direction: column;
  gap:            var(--space-1-5);
}

.field-label {
  font-size:   var(--text-sm);
  font-weight: var(--font-medium);
  color:       var(--color-text-primary);
}
.field-label-required::after {
  content: ' *';
  color:   var(--color-danger-text);
}

.input {
  width:         100%;
  padding:       var(--space-2) var(--space-3);
  border:        1px solid var(--color-border-default);
  border-radius: var(--radius-md);
  font-size:     var(--text-base);
  font-family:   var(--font-sans);
  color:         var(--color-text-primary);
  background:    var(--color-bg-surface);
  transition:    border-color var(--duration-fast);
}
.input:hover  { border-color: var(--color-border-strong); }
.input:focus  { outline: none; border-color: var(--color-border-focus);
                box-shadow: 0 0 0 3px rgba(230, 172, 0, 0.18); }
.input.error  { border-color: var(--color-danger-border); }
.input:disabled { background: var(--color-bg-sunken); color: var(--color-text-disabled); }

/* Amount input — mono font + currency prefix */
.input-amount {
  font-family: var(--font-mono);
  font-size:   var(--text-md);
  font-weight: var(--font-semibold);
  text-align:  right;
  padding-right: var(--space-3);
}

.field-hint  { font-size: var(--text-sm); color: var(--color-text-tertiary); }
.field-error { font-size: var(--text-sm); color: var(--color-danger-text); }
```

**Select:** Use a native `<select>` styled to match the input. For multi-select or search, use a headless combobox (e.g., Headless UI `Combobox`) with the same visual tokens.

**Currency input pattern:**
```html
<div class="field">
  <label class="field-label field-label-required">Loan Amount</label>
  <div style="position: relative;">
    <span style="position:absolute; left:12px; top:50%; transform:translateY(-50%);
                 color:var(--color-text-tertiary); font-family:var(--font-mono);">ETB</span>
    <input class="input input-amount" style="padding-left: 44px;" placeholder="0.00" />
  </div>
  <span class="field-hint">Minimum: ETB 1,000 · Maximum: ETB 500,000</span>
</div>
```

### 6.3 Status Badge

The most-rendered component in the product. Optimised for zero ambiguity.

```css
.badge {
  display:       inline-flex;
  align-items:   center;
  gap:           var(--space-1);
  padding:       var(--space-0-5) var(--space-2);
  border-radius: var(--radius-full);
  font-size:     var(--text-xs);
  font-weight:   var(--font-semibold);
  letter-spacing: var(--tracking-wide);
  text-transform: uppercase;
  white-space:   nowrap;
}

/* One class per semantic color */
.badge-success { background: var(--color-success-bg); color: var(--color-success-text); }
.badge-info    { background: var(--color-info-bg);    color: var(--color-info-text); }
.badge-warning { background: var(--color-warning-bg); color: var(--color-warning-text); }
.badge-danger  { background: var(--color-danger-bg);  color: var(--color-danger-text); }
.badge-neutral { background: var(--color-neutral-bg); color: var(--color-neutral-text); }
.badge-purple  { background: var(--color-purple-bg);  color: var(--color-purple-text); }
```

**Badge dot (optional):**
```html
<span class="badge badge-warning">
  <span style="width:6px;height:6px;border-radius:50%;
               background:currentColor;flex-shrink:0;"></span>
  Overdue
</span>
```

### 6.4 Card

```css
.card {
  background:    var(--color-bg-surface);
  border:        1px solid var(--color-border-default);
  border-radius: var(--radius-lg);
  box-shadow:    var(--shadow-sm);
  overflow:      hidden; /* clips the status rail */
}

.card-header {
  display:         flex;
  align-items:     center;
  justify-content: space-between;
  padding:         var(--space-4) var(--space-5);
  border-bottom:   1px solid var(--color-border-default);
}
.card-header h2 {
  font-size:   var(--text-xl);
  font-weight: var(--font-semibold);
  color:       var(--color-text-primary);
}

.card-body    { padding: var(--space-5); }
.card-footer  {
  padding:     var(--space-4) var(--space-5);
  border-top:  1px solid var(--color-border-default);
  background:  var(--color-bg-sunken);
  display:     flex;
  align-items: center;
  gap:         var(--space-3);
  justify-content: flex-end;
}

/* === STATUS RAIL — the signature element === */
.card-status-rail {
  display: flex;
}
.card-status-rail::before {
  content:      '';
  flex-shrink:  0;
  width:        3px;
  align-self:   stretch;
  border-radius: var(--radius-sm) 0 0 var(--radius-sm);
  /* Colour driven by modifier class */
}
.card-status-rail.status-active::before  { background: var(--color-success-rail); }
.card-status-rail.status-overdue::before { background: var(--color-warning-rail); }
.card-status-rail.status-defaulted::before { background: var(--color-danger-rail); }
.card-status-rail.status-review::before  { background: var(--color-purple-rail); }
.card-status-rail.status-neutral::before { background: var(--color-neutral-rail); }
```

**KPI Card variant:**
```html
<div class="card">
  <div class="card-body" style="display:flex; flex-direction:column; gap:var(--space-1);">
    <span style="font-size:var(--text-sm); color:var(--color-text-secondary);">
      Total Outstanding
    </span>
    <span style="font-family:var(--font-mono); font-size:var(--text-3xl);
                 font-weight:var(--font-bold); color:var(--color-text-primary);">
      ETB 2,847,500
    </span>
    <span style="font-size:var(--text-sm); color:var(--color-success-text);">
      ↑ 12.4% vs last month
    </span>
  </div>
</div>
```

### 6.5 Data Table

Financial tables need dense information without visual noise.

```css
.table-wrapper {
  overflow-x:    auto;
  border:        1px solid var(--color-border-default);
  border-radius: var(--radius-lg);
}

table {
  width:           100%;
  border-collapse: collapse;
  font-size:       var(--text-base);
}

thead th {
  padding:         var(--space-3) var(--space-4);
  text-align:      left;
  font-size:       var(--text-xs);
  font-weight:     var(--font-semibold);
  text-transform:  uppercase;
  letter-spacing:  var(--tracking-widest);
  color:           var(--color-text-tertiary);
  background:      var(--color-bg-sunken);
  border-bottom:   1px solid var(--color-border-default);
  white-space:     nowrap;
}

tbody tr {
  border-bottom:  1px solid var(--color-border-default);
  transition:     background var(--duration-fast);
}
tbody tr:last-child { border-bottom: none; }
tbody tr:hover      { background: var(--color-bg-sunken); }

tbody td {
  padding:  var(--space-3) var(--space-4);
  color:    var(--color-text-primary);
  vertical-align: middle;
}

/* Column alignment conventions */
td.col-amount,
td.col-rate,
td.col-count  { font-family: var(--font-mono); text-align: right; }
td.col-id     { font-family: var(--font-mono); font-size: var(--text-sm);
                color: var(--color-text-secondary); }
td.col-date   { font-family: var(--font-mono); font-size: var(--text-sm);
                white-space: nowrap; color: var(--color-text-secondary); }

/* Status rail in table rows */
tbody tr.status-rail-active  td:first-child { box-shadow: inset 3px 0 0 var(--color-success-rail); }
tbody tr.status-rail-overdue td:first-child { box-shadow: inset 3px 0 0 var(--color-warning-rail); }
tbody tr.status-rail-danger  td:first-child { box-shadow: inset 3px 0 0 var(--color-danger-rail); }
```

**Table toolbar pattern:**
```
┌─────────────────────────────────────────────────────┐
│  [🔍 Search loans...]   [Status ▾] [Date ▾]  [↑↓]  │
├─────────────────────────────────────────────────────┤
│  Loan ID    Borrower    Amount    Status    Due Date │
│ ─────────────────────────────────────────────────── │
│  LN-00123   Abebe T.   50,000    ● Active  Jun 30   │
│  LN-00119   Sara M.    25,000    ⚠ Overdue Jun 15   │
└─────────────────────────────────────────────────────┘
```

### 6.6 Modal & Drawer

```css
/* === Overlay === */
.modal-overlay {
  position:   fixed;
  inset:      0;
  background: var(--color-bg-overlay);
  z-index:    var(--z-overlay);
  display:    flex;
  align-items: center;
  justify-content: center;
  padding:    var(--space-4);
}

/* === Modal === */
.modal {
  background:    var(--color-bg-surface);
  border:        1px solid var(--color-border-default);
  border-radius: var(--radius-xl);
  box-shadow:    var(--shadow-xl);
  z-index:       var(--z-modal);
  width:         100%;
  max-height:    calc(100vh - var(--space-16));
  overflow-y:    auto;
}
.modal-sm  { max-width: 400px; }
.modal-md  { max-width: 560px; }
.modal-lg  { max-width: 720px; }

.modal-header {
  display:         flex;
  align-items:     center;
  justify-content: space-between;
  padding:         var(--space-5) var(--space-6);
  border-bottom:   1px solid var(--color-border-default);
  position:        sticky;
  top:             0;
  background:      var(--color-bg-surface);
}
.modal-body   { padding: var(--space-6); }
.modal-footer {
  padding:       var(--space-4) var(--space-6);
  border-top:    1px solid var(--color-border-default);
  display:       flex;
  justify-content: flex-end;
  gap:           var(--space-3);
  position:      sticky;
  bottom:        0;
  background:    var(--color-bg-surface);
}

/* === Right Drawer (Loan Detail, Audit Log) === */
.drawer {
  position:   fixed;
  top:        0;
  right:      0;
  bottom:     0;
  width:      min(560px, 100vw);
  background: var(--color-bg-surface);
  border-left: 1px solid var(--color-border-default);
  box-shadow: var(--shadow-xl);
  z-index:    var(--z-modal);
  display:    flex;
  flex-direction: column;
  overflow:   hidden;
}
.drawer-header { /* same as modal-header */ }
.drawer-body   { flex: 1; overflow-y: auto; padding: var(--space-6); }
.drawer-footer { /* same as modal-footer */ }
```

**Confirmation modal pattern (for Reject / Approve / Disburse):**
```
┌──────────────────────────────────┐
│  Disburse Loan                 ✕ │
├──────────────────────────────────┤
│                                  │
│  Disburse ETB 50,000 to          │
│  Abebe Tadesse's wallet?         │
│                                  │
│  This action cannot be undone.   │
│                                  │
├──────────────────────────────────┤
│               [Cancel] [Disburse]│
└──────────────────────────────────┘
```

### 6.7 Navigation (Sidebar)

```css
.sidebar {
  width:         var(--sidebar-width-expanded);
  height:        100vh;
  background:    var(--color-bg-surface);
  border-right:  1px solid var(--color-border-default);
  display:       flex;
  flex-direction: column;
  overflow:      hidden;
  position:      sticky;
  top:           0;
  flex-shrink:   0;
}

.sidebar-logo {
  height:       var(--header-height);
  padding:      0 var(--space-4);
  display:      flex;
  align-items:  center;
  border-bottom: 1px solid var(--color-border-default);
  flex-shrink:  0;
}

.sidebar-nav { flex: 1; overflow-y: auto; padding: var(--space-3) var(--space-2); }

.nav-section-label {
  font-size:      var(--text-xs);
  font-weight:    var(--font-semibold);
  text-transform: uppercase;
  letter-spacing: var(--tracking-widest);
  color:          var(--color-text-tertiary);
  padding:        var(--space-3) var(--space-3) var(--space-1);
}

.nav-item {
  display:       flex;
  align-items:   center;
  gap:           var(--space-3);
  padding:       var(--space-2) var(--space-3);
  border-radius: var(--radius-md);
  font-size:     var(--text-sm);
  font-weight:   var(--font-medium);
  color:         var(--color-text-secondary);
  text-decoration: none;
  transition:    background var(--duration-fast), color var(--duration-fast);
  cursor:        pointer;
}
.nav-item:hover    { background: var(--color-bg-sunken); color: var(--color-text-primary); }
.nav-item.active   {
  background:  var(--color-brand-subtle);
  color:       var(--color-brand-text);
  font-weight: var(--font-semibold);
}

.nav-item-badge {  /* unread count, pending tasks */
  margin-left: auto;
  min-width:   20px;
  height:      20px;
  border-radius: var(--radius-full);
  background:  var(--color-danger-bg);
  color:       var(--color-danger-text);
  font-size:   var(--text-xs);
  font-weight: var(--font-semibold);
  display:     flex;
  align-items: center;
  justify-content: center;
  padding:     0 var(--space-1-5);
}
```

**Sidebar navigation structure:**
```
FinCore                        [Tenant: Nile Credit ▾]

  OVERVIEW
  ⬜ Dashboard

  LENDING
  📋 Loan Products
  💼 Loans              [12 active]
  👛 Wallets

  WORKFLOW
  ✅ My Tasks              [3]
  🔄 Workflows

  FINANCE
  📊 Reports
  📒 Audit Log

  SETTINGS
  👥 Members
  🔐 Roles
  💳 Billing
```

### 6.8 Toast / Notification Banner

```css
.toast-region {
  position:  fixed;
  bottom:    var(--space-6);
  right:     var(--space-6);
  z-index:   var(--z-toast);
  display:   flex;
  flex-direction: column;
  gap:       var(--space-3);
  max-width: 380px;
  width:     100%;
}

.toast {
  display:       flex;
  align-items:   flex-start;
  gap:           var(--space-3);
  padding:       var(--space-4);
  border-radius: var(--radius-lg);
  border:        1px solid;
  box-shadow:    var(--shadow-lg);
  background:    var(--color-bg-surface);
  font-size:     var(--text-sm);
}
.toast-success { border-color: var(--color-success-border);
                 border-left:  3px solid var(--color-success-rail); }
.toast-error   { border-color: var(--color-danger-border);
                 border-left:  3px solid var(--color-danger-rail); }
.toast-warning { border-color: var(--color-warning-border);
                 border-left:  3px solid var(--color-warning-rail); }
.toast-info    { border-color: var(--color-info-border);
                 border-left:  3px solid var(--color-info-rail); }

.toast-title   { font-weight: var(--font-semibold); color: var(--color-text-primary); }
.toast-message { color: var(--color-text-secondary); margin-top: var(--space-0-5); }
```

### 6.9 Tabs

```css
.tabs         { display: flex; border-bottom: 1px solid var(--color-border-default); }
.tab-item {
  padding:       var(--space-3) var(--space-4);
  font-size:     var(--text-sm);
  font-weight:   var(--font-medium);
  color:         var(--color-text-secondary);
  border-bottom: 2px solid transparent;
  cursor:        pointer;
  white-space:   nowrap;
  transition:    color var(--duration-fast), border-color var(--duration-fast);
  margin-bottom: -1px;
}
.tab-item:hover { color: var(--color-text-primary); }
.tab-item.active {
  color:         var(--color-brand-text);
  border-bottom-color: var(--color-brand-default);
  font-weight:   var(--font-semibold);
}
```

**Use on:** Loan detail (Info / Schedule / Transactions / History), Settings (Profile / Security / Notifications).

### 6.10 Empty States

```css
.empty-state {
  display:        flex;
  flex-direction: column;
  align-items:    center;
  text-align:     center;
  padding:        var(--space-16) var(--space-8);
  gap:            var(--space-4);
}
.empty-state-icon  { width: 48px; height: 48px; color: var(--color-text-disabled); }
.empty-state-title {
  font-size:   var(--text-xl);
  font-weight: var(--font-semibold);
  color:       var(--color-text-primary);
}
.empty-state-desc  { font-size: var(--text-base); color: var(--color-text-secondary); max-width: 360px; }
```

**Copy examples:**
- Loans list (new tenant): "No loans yet. Create a loan product, then submit your first application."
- My Tasks (empty inbox): "All clear. No approvals waiting for you."
- Audit log (filtered, no results): "No activity matches these filters. Try a wider date range."

---

## 7. Design System File Structure

```
src/
├── styles/
│   ├── tokens/
│   │   ├── base.css          # Raw values — hex, px, rem
│   │   ├── semantic.css      # Purpose-mapped aliases (light)
│   │   ├── semantic.dark.css # Dark mode overrides
│   │   └── index.css         # @import all three
│   └── globals.css           # Reset + body defaults, imports index.css
│
├── components/
│   └── ui/                   # Design system components only
│       ├── Button.tsx
│       ├── Input.tsx
│       ├── Badge.tsx
│       ├── Card.tsx
│       ├── Modal.tsx
│       ├── Drawer.tsx
│       ├── Table.tsx
│       ├── Tabs.tsx
│       ├── Toast.tsx
│       ├── EmptyState.tsx
│       └── index.ts          # Barrel export
│
├── components/
│   └── domain/               # Finance-specific components
│       ├── LoanStatusBadge.tsx    # Wraps Badge + loan status mapping
│       ├── AmountDisplay.tsx      # Mono font, currency prefix, formatting
│       ├── RepaymentSchedule.tsx
│       ├── LoanTimeline.tsx       # State machine visual
│       ├── WorkflowStepCard.tsx
│       └── KPICard.tsx
│
└── lib/
    ├── format.ts    # formatAmount(n, currency), formatDate(d), formatLoanId(id)
    └── status.ts    # loanStatusToVariant(status) → 'success' | 'danger' | ...
```

---

## 8. Tailwind Integration

### 8.1 CSS Variables Bridge

Wire semantic tokens into Tailwind so you can write `bg-surface`, `text-secondary` etc.

```js
// tailwind.config.js
const { fontFamily } = require('tailwindcss/defaultTheme');

module.exports = {
  darkMode: ['selector', '[data-theme="dark"]'],
  content: ['./src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', ...fontFamily.sans],
        mono: ['JetBrains Mono', ...fontFamily.mono],
      },
      colors: {
        page:      'var(--color-bg-page)',
        surface:   'var(--color-bg-surface)',
        elevated:  'var(--color-bg-elevated)',
        sunken:    'var(--color-bg-sunken)',
        border:    'var(--color-border-default)',
        'border-strong': 'var(--color-border-strong)',
        brand:     'var(--color-brand-default)',
        'brand-subtle': 'var(--color-brand-subtle)',
      },
      textColor: {
        primary:   'var(--color-text-primary)',
        secondary: 'var(--color-text-secondary)',
        tertiary:  'var(--color-text-tertiary)',
        disabled:  'var(--color-text-disabled)',
        inverse:   'var(--color-text-inverse)',
        link:      'var(--color-text-link)',
        brand:     'var(--color-brand-text)',
      },
      borderRadius: {
        sm: 'var(--radius-sm)',
        DEFAULT: 'var(--radius-md)',
        lg: 'var(--radius-lg)',
        xl: 'var(--radius-xl)',
        full: 'var(--radius-full)',
      },
      spacing: {
        '0.5': 'var(--space-0-5)',
        1:  'var(--space-1)',
        1.5:'var(--space-1-5)',
        2:  'var(--space-2)',
        3:  'var(--space-3)',
        4:  'var(--space-4)',
        5:  'var(--space-5)',
        6:  'var(--space-6)',
        8:  'var(--space-8)',
        10: 'var(--space-10)',
        12: 'var(--space-12)',
        16: 'var(--space-16)',
      },
      boxShadow: {
        sm: 'var(--shadow-sm)',
        DEFAULT: 'var(--shadow-md)',
        lg: 'var(--shadow-lg)',
        xl: 'var(--shadow-xl)',
      },
      transitionDuration: {
        fast:   'var(--duration-fast)',
        normal: 'var(--duration-normal)',
        slow:   'var(--duration-slow)',
      },
    },
  },
  plugins: [],
};
```

### 8.2 Dark Mode Toggle (Next.js)

```tsx
// lib/theme.ts
export function setTheme(theme: 'light' | 'dark') {
  document.documentElement.dataset.theme = theme;
  localStorage.setItem('fincore-theme', theme);
}

export function initTheme() {
  const saved = localStorage.getItem('fincore-theme');
  const system = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  setTheme((saved as 'light' | 'dark') ?? system);
}
```

```tsx
// app/layout.tsx
<html lang="en" suppressHydrationWarning>
  <head>
    <script dangerouslySetInnerHTML={{__html: `
      (function(){
        var t=localStorage.getItem('fincore-theme')
          || (window.matchMedia('(prefers-color-scheme:dark)').matches?'dark':'light');
        document.documentElement.dataset.theme=t;
      })();
    `}} />
  </head>
  ...
</html>
```

### 8.3 Key Utility Classes (Reference)

```
Backgrounds:   bg-page, bg-surface, bg-elevated, bg-sunken
Text:          text-primary, text-secondary, text-tertiary, text-inverse, text-brand
Border:        border-border, border-[color:var(--color-border-strong)]
Font:          font-sans, font-mono
Shadow:        shadow-sm, shadow, shadow-lg, shadow-xl
Radius:        rounded-sm, rounded, rounded-lg, rounded-xl, rounded-full
```

---

## 9. Accessibility Standards

| Concern | Requirement | Implementation |
|---|---|---|
| Colour contrast | AA minimum (4.5:1 text, 3:1 large) | All semantic colour pairs tested at design time |
| Focus visibility | Visible focus ring on all interactive elements | `focus-visible` ring using `--color-border-focus` (amber) |
| Keyboard nav | Full keyboard support for modals, dropdowns, tables | Use Headless UI or Radix primitives |
| Screen reader | Semantic HTML + ARIA labels | `<button>` not `<div onClick>`, `aria-label` on icon-only buttons |
| Motion | Respect `prefers-reduced-motion` | Wrap all `transition` / `animation` in media query |
| Form errors | Error message linked to field via `aria-describedby` | Set `aria-invalid="true"` + `aria-describedby="field-error-id"` |
| Status colour | Never colour-only for status | Status badge always includes text label, not just dot |
| Table headers | `<th scope="col">` for all column headers | Never use `<td>` for header cells |

```css
/* Reduced motion override */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

---

## 10. Responsive Strategy

### Breakpoints

| Name | Min-width | Target |
|---|---|---|
| `sm` | 640px | Landscape mobile |
| `md` | 768px | Tablet (sidebar appears) |
| `lg` | 1024px | Small laptop |
| `xl` | 1280px | Standard desktop |

### Adaptation Rules

**< 768px (mobile):**
- Sidebar hidden; bottom tab bar (5 items: Dashboard, Loans, Tasks, Notifications, More)
- Cards stack in single column
- Tables scroll horizontally (`overflow-x: auto`) — never shrink columns
- Modals become full-screen bottom sheets (`border-radius` only on top)
- KPI row becomes 2×2 grid

**768px–1024px (tablet):**
- Sidebar collapsed to icon-only mode (56px wide), expands on hover
- 2-column KPI grid
- Tables fully visible

**> 1024px (desktop):**
- Full sidebar expanded
- 3–4 column KPI grid
- Optional two-pane layout (list + detail drawer side-by-side)

---

## 11. Product-Specific Implementation Notes

### 11.1 Amount Formatting

Standardise in one utility, use everywhere:

```ts
// lib/format.ts
export function formatAmount(
  amount: number,
  currency = 'ETB',
  locale = 'am-ET'
): string {
  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
  }).format(amount / 100); // stored in minor units (cents)
}

export function formatLoanId(id: string): string {
  // LN-00123 style
  return `LN-${id.slice(0, 8).toUpperCase()}`;
}

export function formatDate(date: string): string {
  return new Intl.DateTimeFormat('en-ET', {
    day: '2-digit', month: 'short', year: 'numeric'
  }).format(new Date(date));
}
```

### 11.2 Loan Status Utility

```ts
// lib/status.ts
type BadgeVariant = 'success' | 'info' | 'warning' | 'danger' | 'neutral' | 'purple';

const LOAN_STATUS_MAP: Record<string, BadgeVariant> = {
  CREATED:      'neutral',
  SUBMITTED:    'info',
  UNDER_REVIEW: 'purple',
  APPROVED:     'success',
  DISBURSED:    'success',
  ACTIVE:       'success',
  COMPLETED:    'neutral',
  REJECTED:     'danger',
  DEFAULTED:    'danger',
  OVERDUE:      'warning',
};

export function loanStatusVariant(status: string): BadgeVariant {
  return LOAN_STATUS_MAP[status] ?? 'neutral';
}
```

### 11.3 Onboarding Flow

New tenant first-login checklist (rendered as a dismissible card on Dashboard):

```
Getting started with FinCore

  ✅  1. Your organisation is set up
  ⬜  2. Invite your first team member
  ⬜  3. Create a loan product
  ⬜  4. Submit your first loan application
  ⬜  5. Configure your notification preferences

  [Continue setup →]                    [Dismiss]
```

- Steps unlock sequentially — locked steps are greyed out, not hidden
- Step 5 is optional and always available to dismiss
- Checklist disappears permanently once all 5 are complete

### 11.4 Branding

| Element | Spec |
|---|---|
| Logo area | 32×32 icon mark + "FinCore" wordmark in `--font-sans` semibold |
| Favicon | Amber square with stylised "F" letterform |
| Page `<title>` | `{Page Name} — FinCore` |
| Loading state | Amber progress bar at top of viewport (NProgress style) |
| 404 page | "This page doesn't exist. Here's your [Dashboard →]." |
| Error boundary | "Something went wrong. [Reload page]" with error code in mono font |

### 11.5 My Tasks (Workflow Inbox)

This is the approval officer's primary screen. Design it like an email inbox:

```
My Tasks                                          3 pending

  ┌─────────────────────────────────────────────────────────┐
  │ ● Loan Approval    LN-A1B2C3D4         Abebe Tadesse    │
  │   ETB 50,000 · 12 months · Submitted 2h ago   [Review] │
  ├─────────────────────────────────────────────────────────┤
  │ ● Loan Approval    LN-E5F6G7H8         Sara Mohammed    │
  │   ETB 120,000 · 24 months · Submitted 4h ago  [Review] │
  ├─────────────────────────────────────────────────────────┤
  │ ○ Disbursement     LN-I9J0K1L2         Dawit Haile      │
  │   ETB 30,000 · Auto-step · Awaiting funds    [Execute] │
  └─────────────────────────────────────────────────────────┘
```

- Unread dot (●) on items not yet opened
- [Review] opens a right Drawer with full loan detail + Approve / Reject / Return buttons
- After action, item removes from list with a brief success toast

---

## 12. Quick-Reference Cheat Sheet

```
SEMANTIC COLOR CLASSES (pick the right intent)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
success  →  active, approved, disbursed, completed payments
info     →  submitted, in progress, informational
warning  →  overdue, expiring soon, attention needed
danger   →  rejected, defaulted, error states, destructive actions
neutral  →  created, draft, archived, disabled
purple   →  under review, pending decision, in workflow

FONT RULES
━━━━━━━━━━
All money  →  font-mono font-semibold
All IDs    →  font-mono text-sm text-secondary
All dates  →  font-mono text-sm
Everything else  →  font-sans

SPACING QUICK PICKS
━━━━━━━━━━━━━━━━━━━
Icon gap   →  space-1-5 (6px)
Item gap   →  space-3 (12px)
Card pad   →  space-5 (20px)
Page pad   →  space-6 (24px)
Section gap →  space-8 (32px)

Z-INDEX LAYERS
━━━━━━━━━━━━━━
Dropdown  →  z-dropdown (100)
Sticky    →  z-sticky   (200)
Overlay   →  z-overlay  (300)
Modal     →  z-modal    (400)
Toast     →  z-toast    (500)
```

---

> **Maintenance:** Tokens live in `src/styles/tokens/`. All component changes flow from editing a semantic token — never hard-code a hex value in a component file. When adding a new entity type (e.g., savings products), extend `status.ts` and the status token map before touching any UI component.
