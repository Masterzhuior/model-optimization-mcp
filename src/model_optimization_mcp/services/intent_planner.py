"""Intent intake, clarification, and recipe synthesis.

This module models the part that generic local agents are usually bad at:
turning a short request such as "用 PTQ 量化 Qwen3.6 模型" into a complete,
auditable recipe before any expensive GPU work starts.
"""

from __future__ import annotations

import re
from copy import deepcopy
from typing import Any

from ..store import JsonStateStore
from ..utils import deep_merge, short_id, utc_now_iso


class IntentPlanner:
    def __init__(self, store: JsonStateStore):
        self.store = store

    def start_intake(
        self,
        *,
        project_id: str,
        user_id: str,
        utterance: str,
        defaults: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        extracted = _extract_intent(utterance)
        answers = deep_merge(extracted, defaults or {})
        all_questions = _build_questions(answers)
        required_questions = [q for q in all_questions if q.get("required", False)]
        session_id = short_id("intake")
        session = {
            "session_id": session_id,
            "project_id": project_id,
            "user_id": user_id,
            "utterance": utterance,
            "extracted": extracted,
            "answers": answers,
            "questions": all_questions,
            "status": "needs_input" if required_questions else "ready_for_recipe",
            "created_at": utc_now_iso(),
            "updated_at": utc_now_iso(),
        }
        self.store.upsert("intake_sessions", session_id, session)
        return _session_response(session)

    def answer_questions(
        self,
        *,
        session_id: str,
        answers: dict[str, Any],
    ) -> dict[str, Any]:
        session = self._get_session(session_id)
        session["answers"] = deep_merge(session.get("answers", {}), answers)
        all_questions = _build_questions(session["answers"])
        required_questions = [q for q in all_questions if q.get("required", False)]
        session["questions"] = all_questions
        session["status"] = "needs_input" if required_questions else "ready_for_recipe"
        session["updated_at"] = utc_now_iso()
        self.store.upsert("intake_sessions", session_id, session)
        return _session_response(session)

    def synthesize_recipe(self, *, session_id: str, force: bool = False) -> dict[str, Any]:
        session = self._get_session(session_id)
        all_questions = _build_questions(session.get("answers", {}))
        required_questions = [q for q in all_questions if q.get("required", False)]
        if required_questions and not force:
            session["questions"] = all_questions
            session["status"] = "needs_input"
            self.store.upsert("intake_sessions", session_id, session)
            return {
                "status": "needs_input",
                "summary": "More information is required before a safe quantization recipe can be created.",
                "session_id": session_id,
                "questions": required_questions,
            }

        recipe_id = short_id("qr")
        answers = session.get("answers", {})
        recipe = _build_recipe_spec(recipe_id, session, answers, all_questions)
        self.store.upsert("recipe_specs", recipe_id, recipe)
        session["status"] = "recipe_drafted"
        session["recipe_id"] = recipe_id
        session["updated_at"] = utc_now_iso()
        self.store.upsert("intake_sessions", session_id, session)
        return {
            "status": "succeeded",
            "summary": "Draft quantization recipe created.",
            "recipe_id": recipe_id,
            "recipe": recipe,
        }

    def validate_recipe(self, *, recipe_id: str) -> dict[str, Any]:
        recipe = self._get_recipe(recipe_id)
        blockers: list[str] = []
        warnings: list[str] = []
        spec = recipe.get("spec", {})
        if not spec.get("model", {}).get("model_uri"):
            blockers.append("model_uri is required for execution.")
        if not spec.get("calibration", {}).get("dataset_id"):
            blockers.append("calibration.dataset_id is required for PTQ.")
        if not spec.get("evaluation", {}).get("dataset_id"):
            blockers.append("evaluation.dataset_id is required for acceptance.")
        if not spec.get("acceptance", {}).get("max_accuracy_drop"):
            warnings.append("max_accuracy_drop is missing; defaulting to 1%.")
        if spec.get("device_farm", {}).get("enabled") and not spec.get("device_farm", {}).get("matrix"):
            warnings.append("device farm is enabled but no explicit device matrix was provided.")
        recipe["validation"] = {
            "status": "blocked" if blockers else "valid",
            "blockers": blockers,
            "warnings": warnings,
            "validated_at": utc_now_iso(),
        }
        recipe["status"] = "blocked" if blockers else "validated"
        self.store.upsert("recipe_specs", recipe_id, recipe)
        return {
            "status": "blocked" if blockers else "succeeded",
            "summary": "Recipe validation completed.",
            "recipe_id": recipe_id,
            "blockers": blockers,
            "warnings": warnings,
            "recipe_status": recipe["status"],
        }

    def approve_recipe(
        self,
        *,
        recipe_id: str,
        approver: str,
        approval_note: str | None = None,
    ) -> dict[str, Any]:
        recipe = self._get_recipe(recipe_id)
        validation = recipe.get("validation", {})
        if validation.get("status") != "valid":
            raise ValueError("recipe must be validated before approval")
        recipe["status"] = "approved"
        recipe["approval"] = {
            "approver": approver,
            "approval_note": approval_note,
            "approved_at": utc_now_iso(),
        }
        self.store.upsert("recipe_specs", recipe_id, recipe)
        return {
            "status": "succeeded",
            "summary": "Recipe approved for execution.",
            "recipe_id": recipe_id,
            "recipe": recipe,
        }

    def create_revision_from_feedback(
        self,
        *,
        recipe_id: str,
        feedback_id: str | None = None,
        kpi_report_id: str | None = None,
        strategy: str = "auto",
        notes: str | None = None,
    ) -> dict[str, Any]:
        base = self._get_recipe(recipe_id)
        revision_id = short_id("qr")
        revision = deepcopy(base)
        revision["recipe_id"] = revision_id
        revision["version"] = int(base.get("version", 1)) + 1
        revision["parent_recipe_id"] = recipe_id
        revision["status"] = "draft"
        revision["created_at"] = utc_now_iso()
        revision["updated_at"] = utc_now_iso()
        revision["revision_reason"] = {
            "feedback_id": feedback_id,
            "kpi_report_id": kpi_report_id,
            "strategy": strategy,
            "notes": notes,
        }
        _apply_revision_strategy(revision, strategy)
        self.store.upsert("recipe_specs", revision_id, revision)
        return {
            "status": "succeeded",
            "summary": "Recipe revision created from feedback.",
            "recipe_id": revision_id,
            "parent_recipe_id": recipe_id,
            "recipe": revision,
        }

    def list_recipes(
        self, *, project_id: str | None = None, status: str | None = None
    ) -> dict[str, Any]:
        recipes = self.store.list("recipe_specs")
        if project_id:
            recipes = [recipe for recipe in recipes if recipe.get("project_id") == project_id]
        if status:
            recipes = [recipe for recipe in recipes if recipe.get("status") == status]
        return {"recipes": recipes, "count": len(recipes)}

    def _get_session(self, session_id: str) -> dict[str, Any]:
        session = self.store.get("intake_sessions", session_id)
        if not session:
            raise ValueError(f"unknown session_id: {session_id}")
        return session

    def _get_recipe(self, recipe_id: str) -> dict[str, Any]:
        recipe = self.store.get("recipe_specs", recipe_id)
        if not recipe:
            raise ValueError(f"unknown recipe_id: {recipe_id}")
        return recipe


def _extract_intent(utterance: str) -> dict[str, Any]:
    normalized = utterance.lower()
    model_match = re.search(r"(qwen[\w.\-]*|llama[\w.\-]*|mistral[\w.\-]*)", normalized)
    quant_method = "ptq" if "ptq" in normalized or "post-training" in normalized else None
    if quant_method is None and any(token in normalized for token in ("量化", "quant")):
        quant_method = "ptq"
    precision = None
    if "int4" in normalized or "4bit" in normalized or "4-bit" in normalized:
        precision = "int4"
    elif "int8" in normalized or "8bit" in normalized or "8-bit" in normalized:
        precision = "int8"
    target = "mobile" if any(token in normalized for token in ("手机", "端侧", "mobile", "android")) else None

    # v2: Platform-aware intent extraction
    vendor_hint = None
    platform_id_hint = None
    # MediaTek detection keywords
    mediatek_keywords = ("天玑", "dimensity", "联发科", "mediatek", "apu", "npu",
                         "genio", "mt6991", "mt6989", "mt8189", "neuron")
    # Qualcomm detection keywords
    qualcomm_keywords = ("骁龙", "snapdragon", "高通", "qualcomm", "hexagon", "htp",
                         "qnn", "sm8650", "sm8550")
    if any(token in normalized for token in mediatek_keywords):
        vendor_hint = "mediatek"
    elif any(token in normalized for token in qualcomm_keywords):
        vendor_hint = "qualcomm"

    # Specific SoC detection
    soc_patterns = {
        "mediatek-dimensity-9400": ["dimensity-9400", "天玑9400", "d9400"],
        "mediatek-dimensity-9300": ["dimensity-9300", "天玑9300", "d9300"],
        "qualcomm-snapdragon-8gen3": ["snapdragon-8gen3", "骁龙8gen3", "8gen3", "sd8g3"],
        "qualcomm-snapdragon-8gen2": ["snapdragon-8gen2", "骁龙8gen2", "8gen2", "sd8g2"],
    }
    for pid, keywords in soc_patterns.items():
        if any(kw in normalized for kw in keywords):
            platform_id_hint = pid
            if pid.startswith("mediatek"):
                vendor_hint = "mediatek"
            elif pid.startswith("qualcomm"):
                vendor_hint = "qualcomm"
            break

    # Inference path detection
    inference_path = None
    if any(token in normalized for token in ("离线", "offline", "dla", "编译")):
        inference_path = "offline"
    elif any(token in normalized for token in ("在线", "online", "tflite")):
        inference_path = "online"

    return {
        "operation": "quantization" if any(token in normalized for token in ("量化", "quant", "ptq")) else None,
        "quantization_stage": quant_method,
        "model_hint": model_match.group(1) if model_match else None,
        "target_precision": precision,
        "deployment_target": target,
        "vendor_hint": vendor_hint,
        "platform_id_hint": platform_id_hint,
        "inference_path": inference_path,
    }


def _build_questions(answers: dict[str, Any]) -> list[dict[str, Any]]:
    questions: list[dict[str, Any]] = []
    _ask_if_missing(
        questions,
        answers,
        "model_uri",
        "模型的真实来源 URI 或 registry ID 是什么？",
        "比如 s3://models/qwen3.6 或 registry://llm/qwen3.6/prod。",
        required=True,
    )
    _ask_if_missing(
        questions,
        answers,
        "calibration_dataset_id",
        "PTQ 校准数据集使用哪一个？",
        "如果没有指定，可以先用 calib-general-v1，但生产前建议换成业务校准集。",
        required=True,
    )
    _ask_if_missing(
        questions,
        answers,
        "eval_dataset_id",
        "精度回归评估集使用哪一个？",
        "建议使用业务验收集，而不是只跑通用 benchmark。",
        required=True,
    )
    _ask_if_missing(
        questions,
        answers,
        "deployment_target",
        "目标部署场景是什么？",
        "例如 server-vllm、server-tensorrt-llm、mobile-android、mobile-ios。",
        required=True,
    )
    _ask_if_missing(
        questions,
        answers,
        "acceptance.max_accuracy_drop",
        "最大可接受精度下降是多少？",
        "常见默认值是 0.01，表示 1%。",
        required=True,
    )
    _ask_if_missing(
        questions,
        answers,
        "acceptance.primary_latency_ms",
        "目标延迟 KPI 是多少？",
        "如果是端侧，请给出 p50/p95 或单 token / 首 token 口径。",
        required=False,
    )
    if _get_nested(answers, "deployment_target") in {"mobile", "mobile-android", "mobile-ios"}:
        _ask_if_missing(
            questions,
            answers,
            "device_matrix",
            "需要覆盖哪些手机平台或 SoC？",
            "例如 snapdragon-8gen3、dimensity-9300、kirin-9000s。",
            required=True,
        )
        # v2: Platform-specific questions for mobile/edge deployment
        _ask_if_missing(
            questions,
            answers,
            "platform.vendor",
            "目标芯片厂商是什么？",
            "MediaTek (天玑/Genio)、Qualcomm (骁龙)、其他。用于选择正确的转换工具链。",
            required=False,
        )
        _ask_if_missing(
            questions,
            answers,
            "platform.platform_id",
            "目标平台型号是什么？",
            "例如 mediatek-dimensity-9400、qualcomm-snapdragon-8gen3。用于确定 NPU 版本和支持的算子。",
            required=False,
        )
        _ask_if_missing(
            questions,
            answers,
            "platform.inference_path",
            "推理路径是什么？",
            "online（TFLite/ONNX Runtime 运行时）或 offline（编译为 DLA/QNN context binary）。离线路径通常性能更高。",
            required=False,
        )
        _ask_if_missing(
            questions,
            answers,
            "platform.cpu_fallback_allowed",
            "是否允许 CPU 回退？",
            "如果模型有不支持的算子，NPU 可能需要回退到 CPU 执行。建议首次部署时允许回退。",
            required=False,
        )
    return questions


def _ask_if_missing(
    questions: list[dict[str, Any]],
    answers: dict[str, Any],
    field: str,
    question: str,
    guidance: str,
    *,
    required: bool,
) -> None:
    if _get_nested(answers, field) in (None, "", []):
        questions.append(
            {
                "id": field.replace(".", "__"),
                "field": field,
                "question": question,
                "guidance": guidance,
                "required": required,
            }
        )


def _get_nested(payload: dict[str, Any], path: str) -> Any:
    current: Any = payload
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _session_response(session: dict[str, Any]) -> dict[str, Any]:
    all_questions = session.get("questions", [])
    required_questions = [q for q in all_questions if q.get("required", False)]
    return {
        "status": session["status"],
        "summary": "Intake session updated.",
        "session_id": session["session_id"],
        "extracted": session.get("extracted", {}),
        "answers": session.get("answers", {}),
        "questions": all_questions,
        "ready_for_recipe": not required_questions,
    }


def _build_recipe_spec(
    recipe_id: str,
    session: dict[str, Any],
    answers: dict[str, Any],
    open_questions: list[dict[str, Any]],
) -> dict[str, Any]:
    deployment_target = answers.get("deployment_target", "server-vllm")
    target_precision = answers.get("target_precision") or "int4"
    method = answers.get("quantization_stage") or "ptq"
    return {
        "recipe_id": recipe_id,
        "version": 1,
        "project_id": session["project_id"],
        "user_id": session["user_id"],
        "status": "draft",
        "created_at": utc_now_iso(),
        "updated_at": utc_now_iso(),
        "source": {
            "session_id": session["session_id"],
            "utterance": session["utterance"],
            "extracted": session.get("extracted", {}),
            "open_questions": open_questions,
        },
        "spec": {
            "model": {
                "model_uri": answers.get("model_uri"),
                "model_hint": answers.get("model_hint"),
                "task_type": answers.get("task_type", "text-generation"),
                "framework": answers.get("framework", "transformers"),
            },
            "quantization": {
                "stage": method,
                "target_precision": target_precision,
                "candidate_methods": _candidate_methods(method, target_precision, deployment_target),
                "sensitivity_analysis": True,
                "fallback_plan": ["int8_weight_only", "mixed_precision", "exclude_sensitive_layers"],
            },
            "calibration": {
                "dataset_id": answers.get("calibration_dataset_id"),
                "sample_count": int(answers.get("calibration_sample_count", 1024)),
                "max_seq_len": int(answers.get("max_seq_len", 2048)),
                "sampling_strategy": answers.get("sampling_strategy", "diverse-and-business-weighted"),
            },
            "evaluation": {
                "dataset_id": answers.get("eval_dataset_id"),
                "metrics": answers.get("metrics", ["accuracy", "rouge_l", "exact_match"]),
                "badcase_analysis": True,
            },
            "execution": {
                "control_plane": True,
                "compute_pool_selector": answers.get("compute_pool_selector", {"capability": "ptq"}),
                "runtime_env": answers.get("runtime_env", "llm-opt-cu124-v3"),
                "requires_approval_before_gpu": bool(answers.get("requires_approval_before_gpu", False)),
            },
            "device_farm": {
                "enabled": deployment_target.startswith("mobile") or bool(answers.get("device_matrix")),
                "deployment_target": deployment_target,
                "matrix": answers.get("device_matrix", []),
                "kpis": answers.get(
                    "device_kpis",
                    ["accuracy_delta", "latency_p50_ms", "latency_p95_ms", "memory_peak_mb", "power_mw"],
                ),
            },
            "acceptance": {
                "max_accuracy_drop": float(_get_nested(answers, "acceptance.max_accuracy_drop") or 0.01),
                "min_speedup": float(_get_nested(answers, "acceptance.min_speedup") or 1.5),
                "primary_latency_ms": _get_nested(answers, "acceptance.primary_latency_ms"),
                "max_memory_mb": _get_nested(answers, "acceptance.max_memory_mb"),
                "thermal_limit_c": _get_nested(answers, "acceptance.thermal_limit_c"),
            },
            "rollback": {
                "artifact_stage": "candidate",
                "fallback_recipe": "int8_weight_only",
                "promotion_requires_approval": True,
            },
            # v2: Platform-specific deployment configuration
            "platform": {
                "platform_id": answers.get("platform.platform_id") or answers.get("platform_id_hint"),
                "vendor": answers.get("platform.vendor") or answers.get("vendor_hint"),
                "inference_path": answers.get("platform.inference_path") or answers.get("inference_path"),
                "runtime": answers.get("platform.runtime"),
                "runtime_version": answers.get("platform.runtime_version"),
                "converter": answers.get("platform.converter"),
                "compiler": answers.get("platform.compiler"),
                "output_format": answers.get("platform.output_format"),
                "cpu_fallback_allowed": bool(answers.get("platform.cpu_fallback_allowed", True)),
                "cpu_fallback_ops": answers.get("platform.cpu_fallback_ops"),
                "max_model_size_gb": answers.get("platform.max_model_size_gb"),
                "max_context_length": answers.get("platform.max_context_length"),
            },
            # v2: Vendor-specific extensions
            "vendor_extensions": _build_vendor_extensions(answers),
        },
    }


def _build_vendor_extensions(answers: dict[str, Any]) -> dict[str, Any]:
    """Build vendor-specific recipe extensions based on the detected or specified vendor."""
    vendor = answers.get("platform.vendor") or answers.get("vendor_hint")
    extensions: dict[str, Any] = {}
    if vendor == "mediatek":
        extensions["mediatek"] = {
            "np_version": answers.get("mediatek.np_version"),
            "mdla_version": answers.get("mediatek.mdla_version"),
            "neuron_sdk_version": answers.get("mediatek.neuron_sdk_version"),
            "converter_flags": answers.get("mediatek.converter_flags", {}),
            "compiler_flags": answers.get("mediatek.compiler_flags", {}),
            "profiler": "neuron-studio",
        }
    elif vendor == "qualcomm":
        extensions["qualcomm"] = {
            "htp_version": answers.get("qualcomm.htp_version"),
            "sdk_version": answers.get("qualcomm.sdk_version"),
            "backend": answers.get("qualcomm.backend", "htp"),
            "use_mixed_precision": answers.get("qualcomm.use_mixed_precision", False),
            "profiler": "qualcomm-profiling-tools",
        }
    return extensions


def _candidate_methods(method: str, precision: str, deployment_target: str) -> list[str]:
    if method == "ptq" and precision == "int4":
        if deployment_target.startswith("mobile"):
            return ["awq", "gptq", "int8_weight_only", "mixed_precision"]
        return ["awq", "gptq", "smoothquant", "int8_weight_only"]
    if method == "ptq" and precision == "int8":
        return ["int8_weight_only", "smoothquant", "mixed_precision"]
    return [method]


def _apply_revision_strategy(recipe: dict[str, Any], strategy: str) -> None:
    spec = recipe.setdefault("spec", {})
    quant = spec.setdefault("quantization", {})
    calibration = spec.setdefault("calibration", {})
    acceptance = spec.setdefault("acceptance", {})
    if strategy in {"accuracy_regression", "auto"}:
        calibration["sample_count"] = max(int(calibration.get("sample_count", 1024)) * 2, 2048)
        quant["sensitivity_analysis"] = True
        quant["fallback_plan"] = ["exclude_sensitive_layers", "mixed_precision", "int8_weight_only"]
    if strategy in {"latency_regression", "auto"}:
        quant["candidate_methods"] = list(dict.fromkeys(["awq", *quant.get("candidate_methods", [])]))
        spec.setdefault("device_farm", {}).setdefault("kpis", []).append("operator_hotspots")
    if strategy == "memory_regression":
        acceptance["max_memory_mb"] = acceptance.get("max_memory_mb") or "must_be_defined_by_next_intake"
