# Best Practices: Building Pipeline Stages with Claude Agent SDK

A comprehensive guide for agents building multi-stage pipelines with externally-enforced validation loops.

---

## Table of Contents

1. [The Generate-Validate-Fix Pattern](#1-the-generate-validate-fix-pattern)
2. [Session Management](#2-session-management)
3. [Prompt Engineering for Pipelines](#3-prompt-engineering-for-pipelines)
4. [External Validation](#4-external-validation)
5. [Batch Processing Patterns](#5-batch-processing-patterns)
6. [Configuration Management](#6-configuration-management)
7. [Anti-Patterns to Avoid](#7-anti-patterns-to-avoid)
8. [Complete Reference Implementation](#8-complete-reference-implementation)

---

## 1. The Generate-Validate-Fix Pattern

### Why External Enforcement Matters

The most critical insight in this codebase: **agents should never validate their own work**. Validation must be mechanically enforced by the orchestration layer (Python), not by the agent itself.

```
┌────────────────────────────────────────────────────────────┐
│                    ORCHESTRATION (Python)                  │
│                                                            │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐             │
│   │ Phase 1  │───▶│ Phase 2  │───▶│ Phase 3  │             │
│   │ Generate │    │ Validate │    │   Fix    │◀────┐       │
│   └──────────┘    └──────────┘    └──────────┘     │       │
│        │               │               │           │       │
│        │          (subprocess)         │           │       │
│        │               │               │      (loop until  │
│        ▼               ▼               ▼       valid)      │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐     │       │
│   │  Agent   │    │ External │    │  Agent   │─────┘       │
│   │  Writes  │    │ Validator│    │  Fixes   │             │
│   │   File   │    │   CLI    │    │  Errors  │             │
│   └──────────┘    └──────────┘    └──────────┘             │
└─────────────────────────────────────────────────────────────┘
```

### The Three-Phase Architecture

```python
async def generate_lesson(...) -> bool:
    """
    Phase 1: Generation
    Phase 2: External validation (loop)
    Phase 3: Fix (if validation fails)
    """
    
    # ─────────────────────────────────────────────────────────
    # PHASE 1: Agent generates content
    # ─────────────────────────────────────────────────────────
    gen_prompt = build_generation_prompt(...)
    agent_ok, session_id = await _run_agent(
        prompt=gen_prompt,
        options=_agent_options(model=model, max_turns=max_turns),
    )
    
    if not agent_ok:
        return False  # Generation failed
    
    # ─────────────────────────────────────────────────────────
    # PHASE 2 & 3: Validation loop (external enforcement)
    # ─────────────────────────────────────────────────────────
    for attempt in range(1, MAX_VALIDATION_ATTEMPTS + 1):
        
        # Phase 2: Python runs validator (agent cannot skip this)
        result = validate_mlai_file(output_file)
        
        if result.success:
            return True  # ✅ Done!
        
        if attempt == MAX_VALIDATION_ATTEMPTS:
            return False  # Exhausted attempts
        
        # Phase 3: Feed errors back to agent
        fix_prompt = build_fix_prompt(
            output_file=output_file,
            validation_errors=result.raw_output,
            attempt=attempt,
        )
        
        # Resume session so agent has context
        fix_ok, session_id = await _run_agent(
            prompt=fix_prompt,
            options=_agent_options(
                model=model,
                max_turns=max_turns,
                session_id=session_id,  # ← Key: context continuity
            ),
        )
    
    return False
```

### Key Principle: Separation of Concerns

| Responsibility | Who Handles It |
|----------------|----------------|
| Content generation | Agent |
| File writing | Agent (via tools) |
| Validation execution | Python (subprocess) |
| Error parsing | Python |
| Fix instructions | Python → Agent |
| Loop control | Python |

---

## 2. Session Management

### Why Session Continuity Matters

When the agent fixes errors, it needs to remember what it originally wrote. Without session resumption, each fix attempt starts fresh—the agent has no memory of its previous work.

### Capturing the Session ID

```python
async def _run_agent(prompt: str, options: ClaudeAgentOptions) -> tuple[bool, str | None]:
    """Run agent and capture session_id for resumption."""
    success = False
    session_id = None

    async for message in query(prompt=prompt, options=options):
        # Capture session ID from the init message
        if hasattr(message, "subtype") and message.subtype == "init":
            if hasattr(message, "session_id"):
                session_id = message.session_id
        
        # ... handle other message types ...

    return success, session_id
```

### Resuming with Context

```python
def _agent_options(
    model: str,
    max_turns: int,
    session_id: str | None = None,  # ← Pass previous session
) -> ClaudeAgentOptions:
    opts = ClaudeAgentOptions(
        allowed_tools=["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
        permission_mode="acceptEdits",
        model=model,
        system_prompt=build_system_prompt(),
        max_turns=max_turns,
        cwd=str(PROJECT_ROOT),
    )
    if session_id:
        opts.resume = session_id  # ← Resume previous session
    return opts
```

### Session Resumption Benefits

| Without Resumption | With Resumption |
|-------------------|-----------------|
| Agent re-reads entire file | Agent remembers file contents |
| No memory of intent | Understands original goals |
| More token usage | Efficient context |
| Lower fix quality | Higher fix quality |

---

## 3. Prompt Engineering for Pipelines

### The System Prompt: Domain Knowledge Injection

The system prompt should embed all reference material the agent needs. Don't make the agent search for format specs—give them directly.

```python
def build_system_prompt() -> str:
    """Build system prompt with format guide embedded."""
    mlai_guide = MLAI_FORMAT_GUIDE.read_text(encoding="utf-8")
    
    return f"""You are a lesson content generator that produces interactive 
educational lessons in MLAI format (XML).

## MLAI Format Reference

{mlai_guide}

## Content Generation Guidelines

1. **Structure**: Start with <Meta>, then organize content...
2. **Instructional Content**: Write clear, engaging explanations...
3. **FlashCards**: Create FlashCards for key terms...
...

## Your Workflow

1. Read the lesson specification markdown file
2. Read the curriculum.json for course-level context
3. Generate a complete .mlai file and write it to the specified output path
4. Report that you have finished writing the file

Focus exclusively on generating high-quality content. 
Do not attempt to validate the file yourself — validation is handled separately.
"""
```

### The Generation Prompt: Clear Instructions

```python
def build_generation_prompt(
    lesson_spec_path: str,
    curriculum_path: str,
    output_file: Path,
    lesson_id: str,
) -> str:
    return f"""Generate an MLAI lesson from the specification.

**Lesson spec file**: {lesson_spec_path}
**Curriculum context**: {curriculum_path}
**Output file path**: {output_file}

Steps:
1. Read the lesson spec: {lesson_spec_path}
2. Read the curriculum for context: {curriculum_path}
3. Generate a complete, high-quality .mlai lesson file
4. Write it to: {output_file}

The lesson should include:
- Proper <Meta> block with lesson ID "{lesson_id}" and appropriate title/tags
- Rich instructional content with sections, headings, body text, and code examples
- At least 4 FlashCards for key concepts
- At least 2 SingleSelect questions
...

Once you have written the file, confirm that you are done."""
```

### The Fix Prompt: Error Feedback

```python
def build_fix_prompt(output_file: Path, validation_errors: str, attempt: int) -> str:
    return f"""The MLAI file you generated failed validation (attempt {attempt}).

**File**: {output_file}

**Validation errors**:
```
{validation_errors}
```

Read the error messages carefully, then edit the file to fix every error.
After making your fixes, confirm that you are done."""
```

### Prompt Design Principles

| Principle | Example |
|-----------|---------|
| Be explicit about inputs | `**Lesson spec file**: {path}` |
| Number the steps | `1. Read... 2. Generate... 3. Write...` |
| Specify expected outputs | "At least 4 FlashCards" |
| Include attempt context | `(attempt {attempt})` in fix prompt |
| Request confirmation | "confirm that you are done" |

---

## 4. External Validation

### The Validator Wrapper

Never let the agent run validation itself. Wrap your validator CLI in Python:

```python
import subprocess
from dataclasses import dataclass
from pathlib import Path

@dataclass
class ValidationResult:
    """Result of running the MLAI validator."""
    success: bool
    raw_output: str
    error_count: int

def validate_mlai_file(file_path: Path) -> ValidationResult:
    """Run validator via subprocess—agent cannot bypass this."""
    
    # Guard: Check validator exists
    if not VALIDATOR_CLI.exists():
        return ValidationResult(
            success=False,
            raw_output=f"Validator CLI not found at {VALIDATOR_CLI}",
            error_count=1,
        )
    
    # Guard: Check file exists
    if not file_path.exists():
        return ValidationResult(
            success=False,
            raw_output=f"File not found: {file_path}",
            error_count=1,
        )
    
    try:
        result = subprocess.run(
            ["node", str(VALIDATOR_CLI), str(file_path)],
            capture_output=True,
            text=True,
            timeout=30,  # Prevent hangs
        )
        
        combined_output = result.stdout
        if result.stderr:
            combined_output += "\n" + result.stderr
        
        # Parse error count for reporting
        error_lines = [
            line for line in combined_output.splitlines()
            if "error" in line.lower() and not line.strip().startswith("#")
        ]
        
        is_success = result.returncode == 0
        return ValidationResult(
            success=is_success,
            raw_output=combined_output.strip(),
            error_count=0 if is_success else max(len(error_lines), 1),
        )
    
    except subprocess.TimeoutExpired:
        return ValidationResult(
            success=False,
            raw_output="Validator timed out after 30 seconds.",
            error_count=1,
        )
    except Exception as exc:
        return ValidationResult(
            success=False,
            raw_output=f"Unexpected error: {exc}",
            error_count=1,
        )
```

### Why Subprocess Isolation?

1. **Security**: Agent cannot manipulate validator code
2. **Reliability**: Validation runs in clean environment
3. **Accountability**: Clear audit trail of what was validated
4. **Reproducibility**: Same validation as manual runs

---

## 5. Batch Processing Patterns

### Iterating Over Work Items

```python
async def generate_all_lessons(
    curriculum_path: str,
    output_dir: str,
    module_filter: str | None = None,
    model: str = DEFAULT_MODEL,
    max_turns: int = DEFAULT_MAX_TURNS,
) -> dict:
    """Generate lessons for all items in curriculum."""
    
    with open(curriculum_file, encoding="utf-8") as f:
        curriculum = json.load(f)
    
    results: dict[str, list[str]] = {
        "success": [],
        "failed": [],
        "skipped": []
    }
    
    for module in curriculum["modules"]:
        module_id = module["module_id"]
        
        # Optional filtering
        if module_filter and module_id != module_filter:
            continue
        
        for lesson in module["lessons"]:
            lesson_id = lesson["lesson_id"]
            lesson_spec = curriculum_dir / module_id / f"{lesson_id}.md"
            
            # Skip if spec doesn't exist
            if not lesson_spec.exists():
                results["skipped"].append(lesson_id)
                continue
            
            # Process single item
            ok = await generate_lesson(...)
            
            if ok:
                results["success"].append(lesson_id)
            else:
                results["failed"].append(lesson_id)
    
    return results
```

### Enriching Output Artifacts

After processing, update your output manifest with results:

```python
# Enrich curriculum.json with generated file paths
success_set = set(results["success"])
enriched = copy.deepcopy(curriculum)

for module in enriched["modules"]:
    for lesson in module["lessons"]:
        lesson_id = lesson["lesson_id"]
        if lesson_id in success_set:
            lesson["mlai_path"] = f"{module_id}/{lesson_id}.mlai"

# Write enriched manifest
output_curriculum = output_dir_path / "curriculum.json"
with open(output_curriculum, "w", encoding="utf-8") as f:
    json.dump(enriched, f, indent=2, ensure_ascii=False)
```

### Batch Results Summary

Always provide a clear summary at the end:

```python
print(f"\n{'=' * 60}")
print("BATCH RESULTS")
print(f"{'=' * 60}")
print(f"✅ Success: {len(results['success'])} lessons")
print(f"❌ Failed:  {len(results['failed'])} lessons")
print(f"⚠️  Skipped: {len(results['skipped'])} lessons")

if results["failed"]:
    print(f"\nFailed lessons: {', '.join(results['failed'])}")
```

---

## 6. Configuration Management

### Centralized Configuration

Keep all paths, defaults, and limits in one file:

```python
# config.py
from pathlib import Path

# ─────────────────────────────────────────────────────────────
# Paths
# ─────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent

VALIDATOR_CLI = (
    Path.home()
    / "Documents"
    / "CODING"
    / "vibely-v2"
    / "vibely-v2-parser"
    / "dist"
    / "cli.js"
)

MLAI_FORMAT_GUIDE = (
    Path(__file__).resolve().parent / "prompts" / "mlai_format_guide.md"
)

# ─────────────────────────────────────────────────────────────
# Defaults
# ─────────────────────────────────────────────────────────────
DEFAULT_MODEL = "claude-opus-4-5"
DEFAULT_MAX_TURNS = 30
MAX_VALIDATION_ATTEMPTS = 500
```

### Why Centralized Config?

| Benefit | Example |
|---------|---------|
| Single source of truth | Change model once, applies everywhere |
| Easy to audit | All limits visible in one file |
| Environment flexibility | Swap validator path per machine |
| No magic numbers | `MAX_VALIDATION_ATTEMPTS` vs `500` |

---

## 7. Anti-Patterns to Avoid

### ❌ Agent Self-Validation

```python
# BAD: Agent validates its own work
prompt = """Generate the file, then validate it yourself and fix any errors."""
```

**Why it's bad**: Agents may skip validation, report false success, or not catch errors they made.

**✅ Correct approach**: External validation via subprocess.

---

### ❌ Skipping Session Resumption

```python
# BAD: Each fix attempt starts fresh
for attempt in range(MAX_ATTEMPTS):
    fix_ok, _ = await _run_agent(
        prompt=fix_prompt,
        options=_agent_options(model=model),  # No session_id!
    )
```

**Why it's bad**: Agent loses context, re-reads files, lower fix quality.

**✅ Correct approach**: Pass `session_id` to resume.

---

### ❌ Unbounded Retries

```python
# BAD: Infinite loop
while True:
    result = validate(file)
    if result.success:
        break
    await fix(file)
```

**Why it's bad**: Could run forever, waste resources.

**✅ Correct approach**: Use `MAX_VALIDATION_ATTEMPTS` limit.

---

### ❌ Mixing Concerns in Prompts

```python
# BAD: One giant prompt for everything
prompt = """Generate the file. 
Then validate it with this regex: ...
If errors, fix them.
Then validate again.
Loop until done."""
```

**Why it's bad**: Agent controls the loop, can skip steps.

**✅ Correct approach**: Separate prompts per phase, Python controls flow.

---

### ❌ Hardcoded Paths

```python
# BAD: Paths scattered throughout code
validator = "/Users/john/tools/validator.js"  # Won't work on other machines
```

**Why it's bad**: Breaks portability, hard to maintain.

**✅ Correct approach**: Centralize in `config.py`.

---

### ❌ Swallowing Errors

```python
# BAD: Silent failure
try:
    result = subprocess.run(...)
except:
    pass  # What happened?
```

**Why it's bad**: No visibility into failures.

**✅ Correct approach**: Return structured `ValidationResult` with error details.

---

## 8. Complete Reference Implementation

### Project Structure

```
lesson_agent/
├── agent.py              # Main orchestration logic
├── config.py             # Centralized configuration
├── main.py               # CLI entry point
├── validator.py          # External validator wrapper
├── prompts/
│   ├── __init__.py
│   ├── system.py         # System prompt builder
│   ├── generation.py     # Generation phase prompt
│   ├── fix.py            # Fix phase prompt
│   └── mlai_format_guide.md  # Domain knowledge
└── output/               # Generated artifacts
```

### Flow Diagram

```
                    ┌─────────────┐
                    │   main.py   │
                    │   (CLI)     │
                    └──────┬──────┘
                           │
            ┌──────────────┴──────────────┐
            │                             │
            ▼                             ▼
    ┌───────────────┐            ┌───────────────┐
    │ Single Lesson │            │ Batch Process │
    │ (one spec)    │            │ (curriculum)  │
    └───────┬───────┘            └───────┬───────┘
            │                             │
            └──────────────┬──────────────┘
                           │
                           ▼
                 ┌───────────────────┐
                 │  generate_lesson  │
                 │  (orchestrator)   │
                 └─────────┬─────────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
         ▼                 ▼                 ▼
   ┌──────────┐      ┌──────────┐      ┌──────────┐
   │ Phase 1  │      │ Phase 2  │      │ Phase 3  │
   │ Generate │─────▶│ Validate │─────▶│   Fix    │
   │ (agent)  │      │(subprocess)     │ (agent)  │
   └──────────┘      └──────────┘      └────┬─────┘
                           ▲                 │
                           │                 │
                           └─────────────────┘
                              (loop until valid)
```

### Key Imports

```python
from claude_agent_sdk import (
    query,
    ClaudeAgentOptions,
    AssistantMessage,
    ResultMessage,
    TextBlock,
)
```

### Agent Options Factory

```python
def _agent_options(
    model: str,
    max_turns: int,
    session_id: str | None = None,
) -> ClaudeAgentOptions:
    opts = ClaudeAgentOptions(
        allowed_tools=["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
        permission_mode="acceptEdits",
        model=model,
        system_prompt=build_system_prompt(),
        max_turns=max_turns,
        cwd=str(PROJECT_ROOT),
    )
    if session_id:
        opts.resume = session_id
    return opts
```

---

## Summary: The Pipeline Checklist

When building a pipeline with Claude Agent SDK:

- [ ] **External validation**: Use subprocess, never let agent self-validate
- [ ] **Session management**: Capture and resume `session_id`
- [ ] **Separate prompts**: Different prompts for generation vs fix phases
- [ ] **Domain knowledge**: Embed format specs in system prompt
- [ ] **Bounded retries**: Set `MAX_VALIDATION_ATTEMPTS`
- [ ] **Centralized config**: Paths and defaults in one file
- [ ] **Structured results**: Return dataclasses, not raw strings
- [ ] **Progress reporting**: Print status at each phase
- [ ] **Batch tracking**: Track success/failed/skipped
- [ ] **Enriched output**: Update manifests with generated paths

---

## Sources

This guide is based on the `vibely-lesson-agent` codebase, which demonstrates a production-ready implementation of the Generate-Validate-Fix pattern for educational content generation.
