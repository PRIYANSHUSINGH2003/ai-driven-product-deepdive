# Product Requirement Document (PRD)
## Project: AI Product Deep Dive — Discovery Phase

### 1. Purpose
This document captures the problem discovery process rather than a finished technical architecture. The goal is to identify one real problem worth solving, validate it with evidence, and then build a minimal AI-native solution.

### 2. What We Are Looking For
- A user problem with real demand, not just technical interest.
- A problem in a domain we can personally connect with or directly access users for.
- An AI-native capability that makes the solution meaningfully different from existing tools.
- A problem small enough to ship and iterate on quickly.

### 3. Candidate Problem Spaces
Potential areas to explore:
- Developer workflow friction or productivity gaps.
- Knowledge work and collaboration bottlenecks.
- Personal or local productivity issues you encounter daily.
- Small accessibility or communication problems grounded in real users.
- AI-era hiring and screening friction, where polished AI-generated artifacts make builder authenticity hard to judge.

### 4. Chosen Early Problem
- **Core friction:** AI makes resumes, essays, code samples, and even commit histories appear polished, while hiding whether a candidate truly understands and owns the work.
- **Hypothesis:** evaluating process signals — commit history depth, prompt-to-commit evolution, reasoning artifacts, and candidate explanations — is a more reliable signal of real builder capability than artifact quality alone.
- **AI-native angle:** use AI to parse, summarize, and surface evidence from development workflows and candidate interactions, rather than just generating a final artifact.
- **Validation plan:** build a lean MVP that collects and surfaces process signals from candidate repos and workflows, then test it with real hiring users.

### 5. Objectives
- Validate at least one problem with evidence from real users or direct experience.
- Define the AI capability at the heart of the solution.
- Create a small, end-to-end MVP that can be shown or tested.
- Track decisions, assumptions, trade-offs, and AI guidance clearly in this repo.

### 5. User Personas (Example)
- **Primary User:** A developer or knowledge worker with a specific daily workflow pain.
- **Secondary User:** A teammate or customer who benefits from the AI-enabled solution.

### 6. Requirements
#### Discovery Requirements
- Interview or observe at least one real user in the selected domain.
- Write a short problem statement that explains why the problem matters.
- Capture assumptions and risks explicitly.

#### Solution Requirements
- Identify the AI capability that enables the solution.
- Keep scope intentionally small: one feature, one use case.
- Build an MVP focused on evidence, not polish.

#### Process Requirements
- Manage the project from day one: planning, decisions, tracking, journal entries.
- Document when AI is used, what it suggested, and when it was corrected.
- Share progress early and often.

### 7. Execution Plan
- **Phase 0:** Problem discovery and validation.
- **Phase 1:** Define the AI-native solution and minimal MVP.
- **Phase 2:** Build the MVP and validate it with users.
- **Phase 3:** Iterate based on feedback and document learnings.

### 8. Validation Criteria
- The chosen problem is supported by evidence or direct experience.
- The solution has a clear AI-native value proposition.
- The MVP is small, usable, and testable.
- Progress is documented transparently in the journal.

---