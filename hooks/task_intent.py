"""Prompt intent and task-complexity helpers for SpecPilot hooks."""
import hashlib
import json
import os
import re
from datetime import datetime, timezone

INTENT_STATE_FILE = "prompt_intent.json"

QUESTION_TERMS = (
    "为什么",
    "是什么",
    "怎么回事",
    "解释",
    "说明",
    "看一下",
    "吗",
    "?",
    "？",
    "why",
    "what",
    "explain",
)
TASK_TERMS = (
    "开始工作",
    "继续",
    "实现",
    "修复",
    "新增",
    "更新",
    "调整",
    "开发",
    "维护",
    "升级",
    "运行",
    "测试",
    "提交",
    "发布",
    "推送",
    "同步",
    "release",
    "push",
    "commit",
    "tag",
    "TASK-",
    "hook_prompt",
    "做好后",
)
DIRECTIVE_TERMS = (
    "你需要",
    "需要确保",
    "必须",
    "不应该",
    "不能",
    "不要",
    "都要",
    "改成",
    "改为",
    "自动确认",
    "自动执行",
    "阶段过渡",
    "阶段切换",
    "阶段转换",
)
HIGH_COMPLEXITY_TERMS = (
    "大版本",
    "v3.0",
    "发布",
    "release",
    "github",
    "githu",
    "push",
    "tag",
    "PROJECT_SPEC",
    "任务书",
    "阶段目标",
    "受保护",
    "protected",
    "hook",
    "secret",
    "token",
    "凭据",
)
AMBIGUOUS_TERMS = (
    "可能",
    "也许",
    "大概",
    "不确定",
    "随便",
    "maybe",
    "probably",
    "not sure",
)
EXPLICIT_GOAL_TERMS = (
    "直接",
    "不要确认",
    "不需要用户确认",
    "完全自动",
    "自动化",
    "自动确认",
    "自动执行",
    "所有环节都是自动",
    "都要自动",
    "做好后",
    "发布",
    "release",
)
CONFIRMATION_TERMS = (
    "同意",
    "确认",
    "允许",
    "可以",
    "yes",
    "ok",
    "apply",
    "approve",
)


def _lower(text):
    return (text or "").lower()


def _contains_any(text, terms):
    lower = _lower(text)
    return any(term.lower() in lower for term in terms)


def is_confirmation_prompt(prompt_text):
    text = (prompt_text or "").strip()
    if not text:
        return False
    compact = re.sub(r"[\s,.!?;:，。！？；：、`'\"“”‘’()\[\]{}<>]+", "", text.lower())
    if compact in {"同意", "确认", "允许", "可以", "好的", "好", "没问题"}:
        return True
    tokens = re.findall(r"[a-z]+", text.lower())
    return any(token in {"yes", "ok", "apply", "approve"} for token in tokens)


def classify_prompt(prompt_text, latest_context=""):
    text = prompt_text or ""
    if not text.strip():
        return "conversation"
    latest_lower = _lower(latest_context)
    if is_confirmation_prompt(text) and (
        "spec_update_required" in latest_lower
        or "maintenance_authorization" in latest_lower
        or "protected maintenance" in latest_lower
        or "受保护维护" in latest_context
    ):
        return "development"
    if "<hook_prompt" in text or _contains_any(text, ("hook_prompt", "NEXT_ACTION")):
        return "development"
    if _contains_any(text, DIRECTIVE_TERMS):
        return "development"
    if _contains_any(text, ("发布", "release", "push", "tag", "github", "githu", "v3.0")):
        return "release"
    has_task = _contains_any(text, TASK_TERMS)
    has_question = _contains_any(text, QUESTION_TERMS)
    if has_question and not has_task:
        return "conversation"
    if has_task:
        return "development"
    if len(text.strip()) <= 80 and has_question:
        return "conversation"
    return "conversation"


def estimate_complexity(prompt_text):
    text = prompt_text or ""
    if _contains_any(text, HIGH_COMPLEXITY_TERMS):
        return "high"
    if _contains_any(text, TASK_TERMS):
        return "medium"
    return "simple"


def is_explicit_goal(prompt_text):
    return _contains_any(prompt_text, EXPLICIT_GOAL_TERMS)


def is_ambiguous(prompt_text):
    return _contains_any(prompt_text, AMBIGUOUS_TERMS)


def requires_user_confirmation(prompt_text, intent=None, complexity=None):
    intent = intent or classify_prompt(prompt_text)
    complexity = complexity or estimate_complexity(prompt_text)
    if intent == "conversation":
        return False
    if complexity in ("simple", "medium"):
        return False
    if is_explicit_goal(prompt_text) and not is_ambiguous(prompt_text):
        return False
    return True


def build_prompt_intent(prompt_text, latest_context=""):
    intent = classify_prompt(prompt_text, latest_context=latest_context)
    complexity = estimate_complexity(prompt_text)
    return {
        "intent": intent,
        "complexity": complexity,
        "requires_confirmation": requires_user_confirmation(
            prompt_text,
            intent=intent,
            complexity=complexity,
        ),
        "explicit_goal": is_explicit_goal(prompt_text),
        "ambiguous": is_ambiguous(prompt_text),
        "prompt_hash": hashlib.sha256((prompt_text or "").encode("utf-8")).hexdigest()[:16],
        "prompt_summary": (prompt_text or "").strip()[:500],
        "latest_context_hash": hashlib.sha256((latest_context or "").encode("utf-8")).hexdigest()[:16],
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def save_prompt_intent(intent, wiki_dir):
    os.makedirs(wiki_dir, exist_ok=True)
    path = os.path.join(wiki_dir, INTENT_STATE_FILE)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(intent or {}, f, indent=2, ensure_ascii=False)


def load_prompt_intent(wiki_dir):
    path = os.path.join(wiki_dir, INTENT_STATE_FILE)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def is_conversation_intent(intent):
    return (intent or {}).get("intent") == "conversation"


def should_auto_apply_spec_update(intent, reason="", next_action=""):
    data = intent or {}
    if data.get("intent") == "conversation":
        return False
    if data.get("requires_confirmation") is False:
        return True
    combined = "%s\n%s\n%s" % (
        data.get("prompt_summary", ""),
        reason or "",
        next_action or "",
    )
    return is_explicit_goal(combined) and not is_ambiguous(combined)
