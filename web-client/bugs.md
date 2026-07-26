# UI/UX & Functional Bug Tracker (`bugs.md`)

**Date:** 2026-07-26  
**Component:** Web Client Frontend (`C:/Users/rusha/Startup/web-client`)  
**Methodology:** Active browser testing via Chromium (`xd://browser`), accessibility tree inspection, viewport overflow analysis, and state-machine instrumentation.

---

## BUG-001: Empty Accessible Names on Mobile Tab Bar
- **Location:** `src/components/Header.tsx` (lines 116–133)
- **Severity:** High (Accessibility / UIA violation)
- **Root Cause:** The mobile bottom navigation buttons (`md:hidden`) rendered only Lucide SVG icons (`<Icon className="w-5 h-5" />`) without explicit `aria-label` or screen-reader text spans. In the Chromium accessibility tree, all four mobile navigation buttons were exposed as `role="button", name=""`, making them unnavigable for screen-reader and keyboard users.
- **Fix Applied:** Added explicit `aria-label={label}` and `title={label}` attributes to each mobile navigation button in `src/components/Header.tsx`, mapping directly from `TAB_CONFIG`.

---

## BUG-002: Delayed First State Emission & Excessively Long Session Launch Latency
- **Location:** `src/services/api.ts` (`subscribeSessionStateMachine`, lines 205–225)
- **Severity:** Medium (UX / Latency)
- **Root Cause:** `subscribeSessionStateMachine` initialized `index = 0` and delayed the first `callback` invocation until the first tick of `setInterval(..., 900)`. For the initial 900ms after a user clicked "Confirm & Connect", `sessionState` remained `null`, causing the session progress bar to appear frozen. Furthermore, stepping 9 times at 900ms required >8.1 seconds to reach the `live` state.
- **Fix Applied:** Refactored `subscribeSessionStateMachine` to emit `callback(SESSION_STATES[0])` synchronously upon subscription so `requested` status appears instantly, and reduced the interval duration from `900ms` to `550ms` (~4.4s total handshake time).

---

## BUG-003: Ambiguous Disabled Button Label on Commercial Rights Blocked Titles
- **Location:** `src/components/CatalogView.tsx` (lines 150–158)
- **Severity:** Medium (Product Gate Compliance / UX)
- **Root Cause:** When a title's `commercial_status` or `rights_basis` was `'blocked'`, `CatalogView.tsx` disabled the action button (`disabled={isBlocked}`), but the button text still read `"Request Streaming Session"`. Users could not determine from the button itself why the action was prohibited, risking confusion around the title-rights policy in `plan.md` Section 3.1.
- **Fix Applied:** Updated the button rendering to dynamically display `"Commercial Rights Blocked"` with an `AlertTriangle` icon when `isBlocked` is true, explicitly communicating the rights restriction.

---

## BUG-004: Missing Accessible Labels & Non-Functional Pointer Lock Toggle
- **Location:** `src/components/SessionPlayer.tsx` (lines 151–192, 18–25)
- **Severity:** Medium (Functional / Accessibility)
- **Root Cause:** The viewport control bar buttons (`toggleStats`, `toggleMute`, `togglePointerLock`, `handleFullscreen`) relied solely on browser `title` tooltips without `aria-label` attributes. Additionally, clicking the pointer lock button only toggled a React boolean state (`setPointerLocked`) without calling `requestPointerLock()` on the video container element or synchronizing with `document.onpointerlockchange`.
- **Fix Applied:** Added explicit `aria-label` attributes to all control bar buttons in `SessionPlayer.tsx`, attached a container ref (`containerRef`), and wired `requestPointerLock()` / `exitPointerLock()` to browser native pointer-lock events with graceful fallback.

---

## BUG-005: Telemetry Interval Resource Waste on Hidden Viewports
- **Location:** `src/components/NodeTelemetry.tsx` (lines 16–47)
- **Severity:** Low (Performance / Resource Optimization)
- **Root Cause:** The telemetry simulation loop ran an unthrottled `setInterval(..., 2000)` that updated state even when the user switched tabs or when the document visibility state was hidden (`document.hidden`).
- **Fix Applied:** Added visibility-state checking inside the interval so telemetry calculations pause when `document.hidden` is true, saving CPU and battery during background tab execution.

---

## BUG-006: Numerical Overflow & Unbounded Floating-Point Decimals in Preflight Metric Tiles
- **Location:** `src/services/api.ts` (`runPreflightCheck`, lines 176–179) and `src/components/PreflightModal.tsx` (`MetricTile`, lines 155–168, 307)
- **Severity:** High (UI Visual Overflow / Readability Bug)
- **Root Cause:** `runPreflightCheck()` generated RTT, jitter, and packet loss using raw `Math.random()` expressions without rounding or truncating, producing 15-decimal floating-point strings (e.g., `32.72075605284813ms`, `1.304024507275773%`). When rendered in the 4-column PreflightModal grid, the numbers overflowed and overlapped adjacent tiles.
- **Fix Applied:** 
  1. Updated `runPreflightCheck()` in `src/services/api.ts` to round `rtt_ms` and `estimated_bandwidth_mbps` to integers, `jitter_ms` to 1 decimal place (`.toFixed(1)`), and `packet_loss_pct` to 2 decimal places (`.toFixed(2)`).
  2. Added defensive rounding in `PreflightModal.tsx` when formatting tile strings and added `truncate` + `overflow-hidden` to `MetricTile` so numbers can never break layout bounds.
