---
name: Serene Enterprise Intelligence
colors:
  surface: '#f6faf7'
  surface-dim: '#d7dbd8'
  surface-bright: '#f6faf7'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f0f5f1'
  surface-container: '#ebefec'
  surface-container-high: '#e5e9e6'
  surface-container-highest: '#dfe3e0'
  on-surface: '#181d1b'
  on-surface-variant: '#414846'
  inverse-surface: '#2c312f'
  inverse-on-surface: '#edf2ee'
  outline: '#727976'
  outline-variant: '#c1c8c5'
  surface-tint: '#47645d'
  primary: '#16332d'
  on-primary: '#ffffff'
  primary-container: '#2d4a43'
  on-primary-container: '#99b9b0'
  inverse-primary: '#adcdc4'
  secondary: '#51625d'
  on-secondary: '#ffffff'
  secondary-container: '#d4e7e1'
  on-secondary-container: '#576863'
  tertiary: '#4a2500'
  on-tertiary: '#ffffff'
  tertiary-container: '#6b3700'
  on-tertiary-container: '#ff993b'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#c9e9e0'
  primary-fixed-dim: '#adcdc4'
  on-primary-fixed: '#02201a'
  on-primary-fixed-variant: '#2f4c45'
  secondary-fixed: '#d4e7e1'
  secondary-fixed-dim: '#b8cbc5'
  on-secondary-fixed: '#0e1e1b'
  on-secondary-fixed-variant: '#394a46'
  tertiary-fixed: '#ffdcc3'
  tertiary-fixed-dim: '#ffb77d'
  on-tertiary-fixed: '#2f1500'
  on-tertiary-fixed-variant: '#6e3900'
  background: '#f6faf7'
  on-background: '#181d1b'
  surface-variant: '#dfe3e0'
typography:
  headline-lg:
    fontFamily: Source Han Sans SC, Microsoft YaHei, sans-serif
    fontSize: 30px
    fontWeight: '600'
    lineHeight: 40px
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Source Han Sans SC, Microsoft YaHei, sans-serif
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Source Han Sans SC, Microsoft YaHei, sans-serif
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  body-lg:
    fontFamily: Source Han Sans SC, Microsoft YaHei, sans-serif
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 26px
  body-md:
    fontFamily: Source Han Sans SC, Microsoft YaHei, sans-serif
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 22px
  label-md:
    fontFamily: Source Han Sans SC, Microsoft YaHei, sans-serif
    fontSize: 13px
    fontWeight: '500'
    lineHeight: 18px
    letterSpacing: 0.02em
  label-sm:
    fontFamily: Source Han Sans SC, Microsoft YaHei, sans-serif
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.03em
  headline-lg-mobile:
    fontFamily: Source Han Sans SC, Microsoft YaHei, sans-serif
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  unit: 4px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 40px
  container-max: 1280px
  gutter: 20px
---

## Brand & Style

The design system is anchored in the concept of "Quiet Intelligence." It targets enterprise environments where cognitive load must be minimized to facilitate deep focus and secure knowledge management. The aesthetic is a refined blend of **Minimalism** and **Corporate Modern**, prioritizing clarity, stability, and institutional trust.

The emotional response should be one of "composed authority"—a system that feels like a well-organized library or a high-end physical workspace. By avoiding the aggressive visual trends of consumer AI (gradients, glows, and floating glass), this design system establishes a professional atmosphere suitable for sensitive data and rigorous analytical work. Every element is intentional, removing decorative noise to elevate the content.

## Colors

The palette is derived from natural, muted tones to reduce eye strain during long-form reading and knowledge discovery.

- **Primary (#2D4A43):** A low-saturation deep teal used for key actions, active states, and branding. It conveys wisdom and stability.
- **Background (#F6F5F1):** A soft, warm grey that provides a paper-like quality, distinguishing the work environment from the standard stark white of consumer web apps.
- **Surface (#FCFCFA):** A nearly-white shade used for containers and content areas to create a subtle lift from the background.
- **Text (#2F3432):** A charcoal grey that maintains high legibility without the harshness of pure black.
- **Warning (#D97706):** A restrained amber used sparingly for sensitive data markers or system alerts, ensuring they are noticed without causing undue alarm.

## Typography

The typography system utilizes high-quality CJK sans-serif typefaces to ensure maximum legibility for Simplified Chinese.

- **Hierarchy:** We use a tight scale to maintain a professional, document-centric feel. Large display sizes are avoided to keep the focus on information density and utility.
- **Weights:** Use "Medium" (500) for labels and "Bold/SemiBold" (600) for headlines. Regular (400) is reserved for body text to ensure a clean, airy texture in dense knowledge bases.
- **Line Height:** Generous line-heights (1.5x - 1.6x) are applied to body text to facilitate long-form reading and complex technical documentation.

## Layout & Spacing

The layout philosophy is a **Fixed-Fluid Hybrid**. On desktop, the main content area follows a structured 12-column grid with a maximum width of 1280px to prevent excessive line lengths in text documents.

- **Rhythm:** An 8px base grid governs all spatial relationships.
- **Structure:** Sidebars are integrated into the background color (#F6F5F1) to feel like part of the architectural shell, while the "Workspace" (the active content area) sits on a Surface (#FCFCFA) card or layer.
- **Mobile:** Elements reflow to a single column with 16px side margins. Complex data tables should utilize horizontal scrolling or simplified card-views on small screens.

## Elevation & Depth

This design system avoids heavy shadows and floating effects to maintain a "grounded" professional feel.

- **Tonal Layers:** Depth is primarily communicated through color shifts (Background vs. Surface).
- **Outlines:** Elements are defined by thin, 1px borders in a slightly darker neutral shade (#E5E3DB). This creates a "blueprint" or "archival" feel that is crisp and precise.
- **Subtle Shadows:** For interactive elements like dropdowns or active modals, use a single, very soft, non-diffused shadow: `0px 2px 8px rgba(45, 74, 67, 0.05)`. The shadow should have a slight teal tint to remain cohesive with the primary palette.

## Shapes

The shape language is controlled and balanced. We use a **8px to 12px corner radius** (Level 2/Rounded) for most UI components.

- **Standard (8px):** Applied to buttons, input fields, and small cards.
- **Large (12px):** Reserved for main content containers and modals.
- **Strictness:** Rounding should never exceed 12px (no pill-shaped buttons) to maintain the "enterprise" architectural rigor.

## Components

- **Buttons:** Primary buttons use the dark green (#2D4A43) with white text. Secondary buttons are outlined in 1px teal with teal text. Interaction states should involve a subtle darken (active) or lighten (hover) of the fill, not a shift in elevation.
- **Input Fields:** Use the Surface color (#FCFCFA) for the fill with an #E5E3DB border. On focus, the border transitions to a 1px solid Primary color. Labels should be placed above the field in Label-MD style.
- **Cards:** Cards should not "float" with heavy shadows. They are defined by a thin border and a flat white surface. For grouping information, use a "Section Header" with a subtle horizontal rule.
- **Lists & Data Tables:** Use alternating row highlights (Zebra striping) using a very faint version of the background color. Borders should only be horizontal to emphasize the flow of reading.
- **AI Feedback / Chat:** AI-generated responses are distinguished by a subtle Primary-color left border (3px) and a slightly different background tint (a 2% opacity teal) to signify the "intelligence" layer without using distracting gradients.
- **Chips/Tags:** Small, rectangular with 4px radius. Use a light teal background with dark teal text for categories, and the restrained amber for "Sensitive" or "Confidential" markers.