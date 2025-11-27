---
name: hello-world
description: A simple example skill that demonstrates the skill structure. Use this skill when learning how to create new skills or as a template for new skills.
license: MIT
allowed-tools:
  - Bash
  - Read
metadata:
  author: example
  version: "1.0"
---

# Hello World Skill

This is a simple example skill demonstrating the basic structure of a skill.

## What This Skill Does

When invoked, this skill provides instructions for creating a simple "Hello World" program.

## Instructions

1. **Greet the user** - Start by acknowledging that the Hello World skill has been activated
2. **Ask for language preference** - Ask the user which programming language they want to use
3. **Generate code** - Create a Hello World program in the requested language

## Supported Languages

- Python: `print("Hello, World!")`
- JavaScript: `console.log("Hello, World!");`
- Bash: `echo "Hello, World!"`
- Go: `fmt.Println("Hello, World!")`
- Rust: `println!("Hello, World!");`

## Example Usage

User: "Use the hello-world skill to create a greeting program"

Response: I'll help you create a Hello World program. Which programming language would you like to use?

## Guidelines

- Always ask for the user's preferred language first
- Provide a complete, runnable code example
- Include instructions on how to run the code
- Keep the code simple and beginner-friendly
