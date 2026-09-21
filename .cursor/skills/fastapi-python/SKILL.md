# Skill: FastAPI Python
## Description
Enforces Diana backend API standards: async routes, Pydantic I/O, error guards.
## Instructions
- Use `async def` for all route handlers
- All inputs/outputs must use Pydantic BaseModel
- Apply early return error guards — no nested if-else
- Use `APIRouter` per domain (agents, memory, users, workflows)
- Return typed responses: `JSONResponse` or typed schema
- Never expose raw exceptions — wrap with HTTPException
- All routes must be user_id scoped for multi-tenancy
