# Intent Intake Skill

Use when an engineer gives a short or ambiguous model optimization request.

## Goal

Turn a sentence such as "用 PTQ 量化 Qwen3.6 模型" into structured requirements and the minimum necessary questions.

## Workflow

1. Call `start_quantization_intake`.
2. Read the returned `questions`.
3. Ask only required missing questions first.
4. Call `answer_intake_questions`.
5. Continue only when `ready_for_recipe` is true.

## Do Not

- Start quantization directly from a vague prompt.
- Invent model URIs, calibration datasets, evaluation datasets, or KPI thresholds.
- Ask a long form if the MCP server already returned a short question list.

