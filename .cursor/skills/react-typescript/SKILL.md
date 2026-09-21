# Skill: React TypeScript
## Description
Enforces DianaOS frontend standards: typed components, no default exports, clean hooks.
## Instructions
- Use `function ComponentName()` — never arrow function components
- Define all props with TypeScript interfaces above the component
- Named exports only — never `export default`
- Use `useQuery` / `useMutation` (React Query) for all async data
- Never fetch directly inside components — use service files in `/src/services/`
- Tailwind only — no inline styles
- Wrap expensive renders with `React.memo`
