---
name: code-review
description: Performs thorough code reviews with focus on best practices, security, performance, and maintainability. Use this skill when reviewing pull requests, auditing code quality, or getting feedback on implementations.
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash
---

# Code Review Skill

This skill provides a systematic approach to reviewing code for quality, security, and best practices.

## Review Checklist

### 1. Code Quality
- [ ] Code is readable and well-organized
- [ ] Functions/methods have single responsibility
- [ ] Variable and function names are descriptive
- [ ] No code duplication (DRY principle)
- [ ] Appropriate error handling

### 2. Security
- [ ] No hardcoded secrets or credentials
- [ ] Input validation present
- [ ] SQL injection prevention (parameterized queries)
- [ ] XSS prevention (output encoding)
- [ ] Authentication/authorization checks

### 3. Performance
- [ ] No N+1 query problems
- [ ] Appropriate caching strategies
- [ ] No unnecessary loops or computations
- [ ] Efficient data structures used

### 4. Maintainability
- [ ] Code follows project conventions
- [ ] Comments explain "why" not "what"
- [ ] Tests are present and meaningful
- [ ] Dependencies are appropriate

## Review Process

1. **Understand the context** - Read the PR description or understand the change's purpose
2. **High-level review** - Look at file changes and overall structure
3. **Detailed review** - Go through each file systematically
4. **Security scan** - Check for common vulnerabilities
5. **Test review** - Ensure tests cover the changes
6. **Provide feedback** - Give constructive, actionable comments

## Output Format

Provide review feedback in this format:

```markdown
## Code Review Summary

**Overall Assessment**: [APPROVE / REQUEST CHANGES / COMMENT]

### Strengths
- Point 1
- Point 2

### Issues Found

#### Critical
- Issue description (file:line)
  - Suggestion for fix

#### Major
- Issue description (file:line)

#### Minor
- Issue description (file:line)

### Suggestions
- Optional improvements
```

## Example Commands

```bash
# Find potential security issues
grep -r "password\|secret\|api_key" --include="*.py"

# Check for TODO comments
grep -r "TODO\|FIXME\|HACK" --include="*.py"

# Find large functions (potential refactoring candidates)
grep -n "def " *.py | head -20
```
