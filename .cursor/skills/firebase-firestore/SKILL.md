# Skill: Firebase Firestore
## Description
Firestore patterns for DianaOS — auth, data modeling, security rules.
## Instructions
- Always scope queries with `where("userId", "==", uid)`
- Use subcollections for nested data (e.g., users/{uid}/sessions/{id})
- Batch writes for multi-doc updates — never sequential writes
- Security rules must deny all by default, allowlist explicitly
- Use Firebase Auth UID as the primary user identifier everywhere
- Cache reads with `getDocFromCache` before network calls
