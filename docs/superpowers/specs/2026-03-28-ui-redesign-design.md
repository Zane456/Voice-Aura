# Voice Aura UI Redesign — Design Spec

**Date:** 2026-03-28
**Status:** Approved

## Overview

Redesign the Voice Aura GUI with a Powder Blue + Apple Glassmorphism visual language. The redesign targets the Tkinter frontend (`src/frontend/main_gui.py` and related visual files) only — no backend changes.

## Design Direction

**Style:** Apple Glassmorphism — semi-transparent layers, soft edges, depth via layering.
**Palette:** Powder Blue (low saturation, high lightness).
**Feel:** Alive and dynamic — animated background, spring-physics buttons, pulsing indicators.

## Color System

```
Background          #E0EEF6  (powder blue, window fill)
Card BG             #FFFFFF 80% opacity (rgba 255,255,255,0.50)
Card border         rgba(255,255,255,0.65)
Card inset highlight rgba(255,255,255,0.60) top edge

Primary accent      #A8CEE0  (powder blue buttons)
Accent hover        #8ABCD4  (darkened 15%)
Start button        rgba(168,206,224,0.55)
Stop button         rgba(240,200,200,0.45)

Text primary        #2C5A73
Text secondary      #3A6880
Text label          rgba(50,80,105,0.50)
Text hint           rgba(50,80,105,0.55)

Status green        #7ECE95
Status red          #F0C8C8
Status yellow       #E8D090

Entry border        rgba(0,0,0,0.06)
Entry focus ring    rgba(168,206,224,0.50) with 3px spread
Listbox selection   rgba(168,206,224,0.30)
```

## Typography

| Element | Font | Size | Weight | Color |
|---------|------|------|--------|-------|
| App title | Helvetica | 22 | semibold | #2C5A73 |
| Section header | Helvetica | 11 | semibold | rgba(50,80,105,0.50) uppercase tracking 1px |
| Body text | Helvetica | 13 | regular | #3A6880 |
| Secondary text | Helvetica | 12 | regular | rgba(50,80,105,0.55) |
| Button text | Helvetica | 13 | medium | inherits from button |
| Small button | Helvetica | 12 | medium | #2E5E74 |

## Layout Changes

### Removed
- "语音输入管理" subtitle text next to the title

### Window
- Background: `#E0EEF6` (powder blue, replaces pure white)
- Border radius: 16px (macOS standard, handled by window manager)
- Shadow: multi-layer soft shadows

### Cards
- Background: semi-transparent white `rgba(255,255,255,0.50)` over window background
- Border: `1px solid rgba(255,255,255,0.65)`
- Top edge: subtle white highlight line (inset top border)
- Border radius: 14px
- Hover: card lifts 1px with deeper shadow
- Entry animation: staggered slide-up from bottom

### Buttons
- Spring physics: press scales to 0.95, release bounces back with `cubic-bezier(0.34,1.56,0.64,1)`
- Hover: lift 1px + deeper shadow + color intensify
- Border radius: 10px
- Shadow: subtle 1-3px colored shadow matching button hue

### Status Indicator
- Active dot: pulsing ring animation (opacity 0.5→0, scale 0.8→1.3, 2s cycle)

## Dynamic Background

The window background features an animated canvas with three layers:

### Layer 1: Rotating Gradient
- Conic gradient using powder blue/lavender tones
- Slowly rotates (30s per revolution)
- Provides subtle color shifting

### Layer 2: Floating Light Orbs
- 3-4 semi-transparent circles with 60px blur
- Colors: `rgba(168,206,224,0.35)`, `rgba(200,210,240,0.30)`, `rgba(180,220,230,0.25)`
- Each orb follows a unique sine/cosine path
- Periods: 14-22 seconds
- Creates depth and organic movement

### Layer 3: Wave Lines
- 3 curved lines drawn on canvas
- Slowly undulate using sine wave animation
- Stroke: `#8BB8D0` at very low opacity (0.08)
- Adds subtle texture without distraction

### Tkinter Implementation Note
The background animation will use a `tk.Canvas` widget as the window background. A `root.after(50ms, ...)` loop redraws orbs and waves each frame (~20fps). The conic gradient is approximated with overlapping radial gradients or replaced entirely by the orbs (which provide sufficient color variation).

## Components Affected

| File | Changes |
|------|---------|
| `src/frontend/main_gui.py` | Color scheme `C` dict, all widget styling, add background canvas animation, remove subtitle, add staggered entry animations, button spring physics |
| `src/frontend/recording_overlay.py` | No changes needed (already uses blue pulsing dot) |

## What Does NOT Change

- All backend files (`src/backend/*`)
- Entry points (`voice_gui.py`, `voice_input_qwen.py`)
- Config structure (`~/.voice_config.json`)
- Functionality — only visual layer changes
- Recording overlay (already well-designed with NSPanel)

## Implementation Constraints (Tkinter)

Tkinter cannot do true `backdrop-filter: blur()`. The glassmorphism effect is approximated by:
1. Using the powder blue window background as the "gradient" visible through cards
2. Cards use carefully chosen semi-transparent white to simulate frosted glass
3. The animated background canvas sits behind all content
4. Inset top borders simulate light reflection

Tkinter cannot do CSS `transition`. Animations are implemented via:
1. `root.after()` for timed callbacks
2. Incremental property changes (color, position) per frame
3. Easing functions approximated with linear interpolation or simple math
