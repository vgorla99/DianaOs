# Skill: n8n Workflows
## Description
Patterns for building lead automation and Diana workflow nodes.
## Instructions
- Always add error output branches on HTTP Request nodes
- Use Set node to normalize data before processing
- Webhook nodes must validate incoming payloads with IF node
- Store credentials in n8n Credential Store — never in node params
- Use `$json` and `$node` references, not hardcoded field names
- Design workflows as reusable templates with documented trigger conditions
