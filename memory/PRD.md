# Meridian Medical Studio — Product Notes

## Original problem statement
Build the referenced doctor website with a 3D hero, smooth scroll animation, parallax/depth, mouse-follow interactions, 3D card transitions, animated buttons, premium lighting/gradients/shadows/glassmorphism, responsive motion, and performance-conscious behavior.

## Architecture decisions
- React + TypeScript + Vite single-page marketing site.
- Framer Motion handles reveals, card motion, and dialog transitions.
- React Three Fiber/Drei/Three power the interactive medical orb in a lazy-loaded HeroScene chunk.
- CSS supplies the responsive editorial system, grain, fallback orb, reduced-motion behavior, and dialog surfaces.

## Implemented
- Meridian medical studio brand experience with hero, navigation, about, expertise cards, approach band, contact strip, and footer.
- Appointment dialog with required fields, confirmation state, Escape handling, focus trap, focus restoration, and stable test IDs.
- Responsive mobile menu, anchor navigation, pointer-follow depth, 3D orb fallback, and reduced-motion CSS support.

## Prioritized backlog
- P0: None.
- P1: Connect appointment request to a real scheduling/email service.
- P2: Add a dedicated doctor profile and patient stories section.

## Next tasks
- Add scheduling availability and confirmation emails when an integration is selected.
