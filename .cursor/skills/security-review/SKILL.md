# Skill: Security Review
## Description
Audit code for exposed secrets, broken auth, and injection vulnerabilities.
## Instructions
- Flag any hardcoded API keys, tokens, or passwords
- Verify all routes check authentication before processing
- Confirm no raw SQL string concatenation
- Check .env is in .gitignore
- Flag any CORS wildcard `*` in production configs
- Verify Firebase security rules deny unauthenticated access
