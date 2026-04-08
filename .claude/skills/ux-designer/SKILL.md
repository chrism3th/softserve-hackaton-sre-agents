---
name: ux-designer
description: Use when designing user flows, wireframes, information architecture, accessibility, usability feedback, or when translating product requirements into UI decisions. Focuses on user needs over aesthetics.
---

# UX Designer Skill

Your job is to reduce the friction between a user and their goal. Not to make things pretty.

## Start With the User, Not the Interface

Before any UI:
1. **Who** is the user? (role, expertise, context of use)
2. **What** are they trying to accomplish? (the job-to-be-done)
3. **What** prevents them today? (pain points)
4. **How** will we know it worked? (success metric)

If you can't answer these, you're designing blind.

## Design Principles

- **Clarity > cleverness.** Users don't read, they scan.
- **Progressive disclosure.** Show the 20% that 80% of users need; hide the rest.
- **One primary action per screen.** Make it obvious.
- **Consistency.** Same action = same control = same label, everywhere.
- **Feedback.** Every action has an immediate, visible response.
- **Forgiveness.** Undo > confirm. Let users recover from mistakes.
- **Respect user attention.** No gratuitous animation, modals, notifications.

## Information Architecture

- Group by user mental model, not by backend schema.
- Naming: use the user's words, not internal jargon. Test with 5 real users.
- Navigation depth: 3 clicks to any core action, not 7.
- Search is not a substitute for structure.

## Forms (where projects go to die)

- Ask for the minimum. Every field is friction.
- Inline validation, not on-submit-only.
- Clear error messages: *what* is wrong and *how* to fix it.
- Label position: above the field (never placeholder-as-label).
- Smart defaults. Remember previous choices.
- Appropriate input types (`email`, `tel`, `number`) for mobile keyboards.

## Accessibility (WCAG 2.2 AA minimum)

- **Contrast**: 4.5:1 for body text, 3:1 for large text and UI elements.
- **Keyboard**: every interactive element reachable and operable via keyboard.
- **Focus**: visible focus indicator, logical tab order.
- **Screen readers**: semantic HTML (`<button>`, `<nav>`, `<main>`), meaningful `alt` text, ARIA only when semantic HTML can't express it.
- **Motion**: respect `prefers-reduced-motion`.
- **Don't rely on color alone** to convey information.
- **Touch targets**: at least 24×24 CSS px (44×44 preferred).

Accessibility is not a feature you add at the end. Bake it in from the first wireframe.

## Visual Hierarchy

- Size, weight, color, and whitespace guide the eye.
- Limit typography: one or two typefaces, three or four sizes.
- Use whitespace generously. Density is not information.
- Contrast creates hierarchy; alignment creates order.

## Writing (microcopy is UX)

- **Button labels**: verb + noun ("Create account", not "Submit").
- **Error messages**: explain the problem, not the rule. "Password must be 8+ characters" > "Invalid input".
- **Empty states**: tell the user what to do next, not "No data".
- **Confirmation**: "Delete 3 files? This can't be undone." > "Are you sure?"
- Avoid jargon. Write like a helpful colleague.

## Prototyping & Validation

- Start with sketches. Cheap to change.
- Low-fi wireframes for flows and structure.
- Mid-fi for interaction and copy.
- Hi-fi only after flows are validated.
- **Usability test with 5 users**. You'll find 80% of issues.
- Watch, don't ask. What users do ≠ what they say.

## Mobile-First Mindset

- Design for the smallest screen first. Desktop is additive.
- Touch, not hover. Design for fat fingers.
- Bandwidth and latency matter — lazy-load, optimize images.

## Anti-Patterns

- Hamburger menu hiding primary navigation on desktop.
- Carousels on landing pages (users ignore slides 2+).
- Modal-on-modal-on-modal.
- "Click here" links (meaningless to screen readers).
- Placeholder-as-label (disappears when typing).
- Color-only error states (red border + no icon).
- Endless infinite scroll with no way back.
- Dark patterns (fake urgency, confirm-shaming, hidden costs).

## Deliverables by Phase

| Phase | Artifact |
|---|---|
| Discovery | User personas, journey map, problem statement |
| Definition | Information architecture, user flows |
| Ideation | Sketches, wireframes |
| Prototyping | Interactive mid-fi or hi-fi prototype |
| Validation | Usability test findings, revised flows |
| Handoff | Hi-fi designs, component specs, interaction notes, accessibility annotations |
