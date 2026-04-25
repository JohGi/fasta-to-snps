---
description: Project coding standards and guidelines for professional academic publication
applyTo: '**' # Apply to all files in this project
---

# FASTA-to-SNPs Project: Code Standards & Guidelines

This project targets academic publication, so all code must meet professional standards. Follow these guidelines systematically.

## General Code Quality

- **Code Level**: Professional-grade code suitable for academic publication
- **Language**: Write all scripts in **English** (comments, documentation, code)
- **Design**: Prioritize simple, elegant, and idiomatic solutions
  - Python: pythonic code following PEP 8 conventions
  - Bash: POSIX-compliant shell scripts
- **Structure**: Clean, readable, reusable code with clear separation of concerns
- **Functions**: Break logic into small, focused functions—one responsibility per function
- **Scope**: Never define nested functions; define all functions at module level (use `@staticmethod` if appropriate within a class)
- **Class Design**: Use Object-Oriented Programming when appropriate; avoid redundant classes; verify no unnecessary duplication

## Code Review Standards

When reviewing code I propose to you:

- **Refactoring Opportunities**: I will suggest improvements when code can be cleaner or more idiomatically written
- **Issues**: I will flag logical errors, security vulnerabilities, and design problems
- **Suggestions**: These are recommendations; you decide whether to apply them

## Python-Specific Standards

### General

- **Imports**: Place all imports at the top of the file, organized as: stdlib, third-party, local imports
- **Type Hints**: Use type hints for all function parameters, returns, and class attributes (Python 3.9+ syntax with lowercase types: `list[str]`, `dict[str, int]`, etc.)
- **Docstrings**: Add concise English docstrings for:
  - Modules
  - Classes
  - Public methods and functions
- **Logging**: Use the `logging` module instead of `print()` for debug/info messages
- **Argument Parsing**: Always create a dedicated function to parse arguments with `argparse`; call it from `main()`

### Object-Oriented Programming

- **Data Classes**: Use the `attrs` package with the modern `@define` decorator for all classes
- **Type Hints**: Always include type hints for class attributes and methods
- **Attrs Features**: Use `frozen=True`, `field()`, and `validator()` to enhance safety and clarity
- **Methods**: Define functions that populate/compute class attributes as methods within the class
- **Testing**: Structure code to facilitate unit testing

### Libraries & Data Processing

- **New Projects**: Prefer `polars` over `pandas` for data handling
- **DataFrames**: Use polars for efficient data manipulation

### Main Function Constraints

- **Max Indentation**: Do not exceed one level of indentation in `main()` (no nested blocks)

## Bash Scripts

- **Naming**: Use descriptive names for scripts and variables (UPPER_CASE for constants)
- **Error Handling**: Include proper error handling (`set -e`, check exit codes)
- **Documentation**: Add comments explaining non-obvious logic
- **Arguments**: Never hardcode file paths; pass them as arguments to the script

## File I/O Conventions

- **No Hardcoded Paths**: Never hardcode input/output file names in scripts
- **Arguments Over Magic Strings**: Accept all file paths as command-line arguments or configuration parameters
- **Flexibility**: Ensure scripts can be reused across different data locations

## Git Commit Conventions

When committing code, use **Conventional Commits** format:

```
<type>(<scope>): <subject>

<optional description>
```

**Types**:
- `feat:` New feature
- `fix:` Bug fix
- `perf:` Performance improvement
- `refactor:` Code restructuring without changing behavior
- `docs:` Documentation changes
- `test:` Adding or updating tests
- `chore:` Maintenance, dependency updates, tooling

**Example**:
```
feat(snp-detection): add polars-based SNP filtering

Implement new filtering logic using polars for better performance.
```

## Author Attribution

- **Script Signatures**: When signing scripts, use the professional name: **Johanna Girodolle**
- **Header**: Include a file header with author information in scripts created from scratch
