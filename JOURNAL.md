# Engineering Journal — Deep Production Pass

## Findings from the second deep audit

1. **Product language was too close to an authorship detector.** The UI and narrative now consistently describe an engineering-evidence profile. The system explicitly avoids claiming AI use, fraud, competence, or intent.
2. **Four-signal scoring was too dependent on weak proxies.** The model is now six-dimensional: activity continuity, structure, workflow, communication, maintenance, and breadth. Communication has only 10% weight because commit-message text is a weak proxy.
3. **PR absence was previously too easy to misread.** Solo repositories now receive neutral collaboration treatment; a solo/no-PR repository is an observation, not a penalty.
4. **Flat directory structure was over-interpreted.** It was removed as an automatic negative flag. Structure is evaluated as one contextual dimension instead.
5. **Sample limitations were not explicit enough.** The report now tells the operator when commit history is capped, tree data is truncated, or endpoints are unavailable.
6. **The application had no proper HTTP boundary.** A FastAPI service was added around the same pipeline, with optional API-key protection and a health endpoint. Streamlit and CLI continue using the exact same service layer.
7. **The Mistral contract needed stronger structure.** The integration now prefers Mistral Structured Outputs via `chat.parse` when supported and falls back to JSON mode. Output is still independently validated and the score adjustment remains hard-clamped.
8. **The review workflow stopped at a score.** Reports now include positive evidence, limitations, and neutral verification questions so the next action is a human validation step rather than an automated decision.

## Quality gates

- Python compilation passes.
- Regression tests cover scoring, privacy minimization, URL parsing, API health, and LLM-output validation.
- CI workflow runs compilation and pytest on every push/pull request.
- Secrets remain environment-backed and excluded from source control.
