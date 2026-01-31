"""
Enhanced base kill-chain: flexible matching, context validation, fuzzy patterns,
number normalization, weighted confidence. Implements KillChainPrompt phases 1–2.
"""

from abc import ABC, abstractmethod
from typing import Dict, Tuple, List, Optional, Any
from datetime import datetime
import json
import logging
import re
import math

logger = logging.getLogger(__name__)

# Phase 3 FIX 9: Below this confidence we may call LLM for stage detection
LLM_CONFIDENCE_THRESHOLD = 0.60

# Keyword importance weights for confidence scoring (Phase 2 FIX 7)
KEYWORD_WEIGHTS = {
    "high": 0.50,
    "medium": 0.30,
    "low": 0.15,
}

_FUZZY_SUBSTITUTIONS = {
    "a": "[a@4]", "e": "[e3]", "i": "[i1!]", "o": "[o0]",
    "t": "[t7]", "s": "[s5$]", "l": "[l1]", "g": "[g9]",
}
_NUMBER_WORDS = {"five": "5", "ten": "10", "fifty": "50", "hundred": "100", "thousand": "1000"}


def keyword_to_pattern(keyword: str, allow_gaps: bool = True) -> str:
    """Convert keyword to regex with word boundaries. Phase 1 FIX 3."""
    words = keyword.split()
    if len(words) == 1:
        return r"\b" + re.escape(keyword) + r"\b"
    escaped = [re.escape(w) for w in words]
    if allow_gaps:
        return r"\b" + r"(?:\s+\w+){0,2}\s+".join(escaped) + r"\b"
    return r"\b" + r"\s+".join(escaped) + r"\b"


def match_keyword_flexible(keyword: str, message: str, allow_gaps: bool = True) -> bool:
    """Match keyword with word boundaries."""
    return bool(re.search(keyword_to_pattern(keyword, allow_gaps), message, re.IGNORECASE))


def match_keywords_count(keywords: List[str], message: str, allow_gaps: bool = True) -> int:
    """Count keywords that match with flexible matching."""
    return sum(1 for kw in keywords if match_keyword_flexible(kw, message, allow_gaps))


def generate_fuzzy_patterns(keyword: str) -> List[str]:
    """Fuzzy regex for typos/leet. Phase 2 FIX 6."""
    patterns: List[str] = []
    word = keyword.lower()
    fuzzy_chars = [_FUZZY_SUBSTITUTIONS.get(c, re.escape(c)) for c in word]
    patterns.append(r"\b" + "".join(fuzzy_chars) + r"\b")
    if len(word) > 4:
        mid = len(word) // 2
        patterns.append(r"\b" + re.escape(word[:mid]) + r"\s*" + re.escape(word[mid:]) + r"\b")
    return patterns


def match_keyword_fuzzy(keyword: str, message: str) -> bool:
    """Match with typo tolerance."""
    if match_keyword_flexible(keyword, message):
        return True
    for pattern in generate_fuzzy_patterns(keyword):
        if re.search(pattern, message, re.IGNORECASE):
            return True
    return False


def normalize_numbers(text: str) -> str:
    """Normalize 5k, Rs 5,000, 1 lakh etc. Phase 2 FIX 8."""
    t = text.lower()
    t = re.sub(r"₹|rs\.?|inr\s*", "", t, flags=re.IGNORECASE)
    t = re.sub(r"(\d+)\s*k\b", lambda m: str(int(m.group(1)) * 1000), t, flags=re.IGNORECASE)
    t = re.sub(r"(\d+)\s*l\b", lambda m: str(int(m.group(1)) * 100000), t, flags=re.IGNORECASE)
    t = re.sub(r"(\d+),(\d+)", r"\1\2", t)
    t = re.sub(r"(\d+)\s*lakh", lambda m: str(int(m.group(1)) * 100000), t, flags=re.IGNORECASE)
    t = re.sub(r"\blakh\b", "100000", t, flags=re.IGNORECASE)
    t = re.sub(r"(\d+)\s*thousand", lambda m: str(int(m.group(1)) * 1000), t, flags=re.IGNORECASE)
    for word, digit in _NUMBER_WORDS.items():
        t = re.sub(r"\b" + word + r"\b", digit, t, flags=re.IGNORECASE)
    return t


def calculate_weighted_confidence(
    matched_keywords: List[str],
    keyword_weights: Optional[Dict[str, float]] = None,
    default_weight: float = 0.25,
) -> float:
    """Weighted confidence with sigmoid. Phase 2 FIX 7."""
    if not matched_keywords:
        return 0.0
    w = keyword_weights or {}
    score = sum(w.get(kw, default_weight) for kw in matched_keywords)
    conf = 1 / (1 + math.exp(-score + 1.5))
    return max(0.20, min(0.98, conf))


class BaseKillChain(ABC):
    """
    Abstract base for scam kill-chains. Optional llm_client enables Phase 3 FIX 9 (LLM fallback).
    """

    def __init__(self, llm_client: Optional[Any] = None) -> None:
        self.current_stage = 1
        self.stage_history: List[int] = [1]
        self.transition_confidences: List[float] = []
        self.conversation_context: List[Dict[str, Any]] = []
        self.turns_at_current_stage = 0
        self.llm_client = llm_client

    @abstractmethod
    def get_stage_count(self) -> int:
        pass

    @abstractmethod
    def get_stage_name(self, stage: int) -> str:
        pass

    @abstractmethod
    def get_stage_objective(self, stage: int) -> str:
        pass

    @abstractmethod
    def detect_transition(self, current_stage: int, message: str) -> Tuple[int, float]:
        pass

    def analyze_message(
        self,
        message: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Analyze message and update state. Optional conversation_history for context."""
        if conversation_history:
            sorted_hist = sorted(
                conversation_history,
                key=lambda x: x.get("timestamp") or datetime.min,
            )
            self.conversation_context = sorted_hist[-5:]

        new_stage, confidence = self.detect_transition(self.current_stage, message)
        llm_used = False

        # Phase 3 FIX 9: LLM fallback when rule-based confidence is low
        if (
            confidence < LLM_CONFIDENCE_THRESHOLD
            and getattr(self, "llm_client", None) is not None
        ):
            llm_stage, llm_confidence = self._llm_stage_detection(message)
            if (
                llm_confidence > confidence
                and 1 <= llm_stage <= self.get_stage_count()
                and llm_stage >= self.current_stage
            ):
                new_stage, confidence = llm_stage, llm_confidence
                llm_used = True

        # Phase 2 FIX 5: block stage skip without context
        if new_stage > self.current_stage + 1 and self._should_force_intermediate_stage(new_stage):
            new_stage = self.current_stage + 1
            confidence = 0.60

        if new_stage == self.current_stage:
            self.turns_at_current_stage += 1
            if self.turns_at_current_stage > 5:
                confidence = self._apply_stage_decay(confidence)
        else:
            self.turns_at_current_stage = 0

        did_transition = new_stage != self.current_stage
        if did_transition:
            self.current_stage = new_stage
            self.stage_history.append(new_stage)
            self.transition_confidences.append(confidence)

        completion = (self.current_stage / self.get_stage_count()) * 100
        out: Dict[str, Any] = {
            "currentStage": self.current_stage,
            "stageName": self.get_stage_name(self.current_stage),
            "stageObjective": self.get_stage_objective(self.current_stage),
            "nextPredictedStage": min(self.current_stage + 1, self.get_stage_count()),
            "killChainCompletion": round(completion, 2),
            "transitionConfidence": confidence if did_transition else 0.0,
            "stageHistory": self.stage_history,
        }
        out["progressionValid"] = self._validate_progression()
        out["turnsAtStage"] = self.turns_at_current_stage
        out["llmUsed"] = llm_used
        return out

    def _llm_stage_detection(self, message: str) -> Tuple[int, float]:
        """
        Phase 3 FIX 9: Use LLM to detect stage when keyword matching is uncertain.
        Expects llm_client with .generate(prompt, temperature=..., max_tokens=...) -> str.
        Returns (detected_stage, confidence). On failure returns (current_stage, 0.0).
        """
        if not getattr(self, "llm_client", None):
            return (self.current_stage, 0.0)
        stage_descriptions = [
            f"Stage {i}: {self.get_stage_name(i)} - {self.get_stage_objective(i)}"
            for i in range(1, self.get_stage_count() + 1)
        ]
        context_lines = [
            f"- {m.get('text', '')}" for m in self.conversation_context[-3:]
        ]
        prompt = f"""You are analyzing a scam message for kill-chain stage detection.

Kill-chain type: {self.__class__.__name__.replace("KillChain", "")}
Current stage: {self.current_stage}
Stages (sequential):
{chr(10).join(stage_descriptions)}

Message to analyze: "{message}"
Recent context:
{chr(10).join(context_lines) if context_lines else "(none)"}

Task: Which stage (1-{self.get_stage_count()}) does this message most likely represent? Stages usually progress sequentially.
Respond with ONLY valid JSON, no markdown: {{"detected_stage": <number>, "confidence": <0.0-1.0>, "reasoning": "<brief>"}}"""

        try:
            response = self.llm_client.generate(
                prompt=prompt,
                temperature=0.3,
                max_tokens=150,
            )
            if not response or not response.strip():
                return (self.current_stage, 0.0)
            text = response.strip()
            data = None
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                start, end = text.find("{"), text.rfind("}")
                if start != -1 and end > start:
                    try:
                        data = json.loads(text[start : end + 1])
                    except json.JSONDecodeError:
                        pass
            if not data or not isinstance(data, dict):
                return (self.current_stage, 0.0)
            stage = int(data.get("detected_stage", self.current_stage))
            conf = float(data.get("confidence", 0.5))
            stage = max(1, min(stage, self.get_stage_count()))
            conf = max(0.0, min(1.0, conf))
            return (stage, conf)
        except Exception as e:
            logger.warning("Kill-chain LLM stage detection failed: %s", e)
            return (self.current_stage, 0.0)

    def _should_force_intermediate_stage(self, target_stage: int) -> bool:
        """Force sequential progression if no intermediate keywords in context."""
        if not self.conversation_context:
            return True
        intermediate = self.current_stage + 1
        if not hasattr(self, "STAGE_DEFINITIONS"):
            return True
        stage_def = getattr(self, "STAGE_DEFINITIONS", {}).get(intermediate, {})
        context_text = " ".join(m.get("text", "") for m in self.conversation_context)
        if "keywords" in stage_def and match_keywords_count(stage_def["keywords"], context_text) >= 1:
            return False
        if "patterns" in stage_def:
            for p in stage_def["patterns"]:
                if re.search(p, context_text, re.IGNORECASE):
                    return False
        return True

    def _apply_stage_decay(self, confidence: float) -> float:
        """Reduce confidence when stuck at same stage. Phase 2 FIX 5."""
        decay = 0.6 ** (self.turns_at_current_stage - 5)
        decayed = confidence * decay
        if decayed < 0.3 and self.current_stage > 1:
            self.current_stage = max(1, self.current_stage - 1)
            self.turns_at_current_stage = 0
            return 0.5
        return decayed

    def _validate_progression(self) -> bool:
        """True if no unvalidated stage skips in history."""
        for i in range(len(self.stage_history) - 1):
            if self.stage_history[i + 1] - self.stage_history[i] > 1:
                return False
        return True

    def detect_best_stage(
        self,
        message: str,
        candidates: Optional[List[int]] = None,
    ) -> Tuple[int, float]:
        """
        Phase 3 FIX 10: Score multiple candidate stages and return best match.
        Default candidates: current, current+1, current+2.
        """
        if candidates is None:
            candidates = [
                self.current_stage,
                min(self.current_stage + 1, self.get_stage_count()),
                min(self.current_stage + 2, self.get_stage_count()),
            ]
        candidates = list(set(c for c in candidates if 1 <= c <= self.get_stage_count()))
        scores = {stage: self._calculate_stage_match_score(stage, message) for stage in candidates}
        valid = {s: sc for s, sc in scores.items() if s >= self.current_stage and sc > 0}
        if not valid:
            return (self.current_stage, 0.0)
        best_stage = max(valid, key=valid.get)
        confidence = valid[best_stage]
        if confidence < 0.50:
            return (self.current_stage, 0.0)
        return (best_stage, confidence)

    def _calculate_stage_match_score(self, stage: int, message: str) -> float:
        """Phase 3 FIX 10: Match score for a specific stage. Used by detect_best_stage."""
        if not hasattr(self, "STAGE_DEFINITIONS"):
            return 0.0
        stage_def = getattr(self, "STAGE_DEFINITIONS", {}).get(stage, {})
        matched: List[str] = []
        if "keywords" in stage_def:
            for kw in stage_def["keywords"]:
                if match_keyword_flexible(kw, message):
                    matched.append(kw)
        pattern_matches = 0
        if "patterns" in stage_def:
            pattern_matches = sum(
                1 for p in stage_def["patterns"] if re.search(p, message, re.IGNORECASE)
            )
        if not matched and pattern_matches == 0:
            return 0.0
        conf = calculate_weighted_confidence(matched, default_weight=0.25)
        if pattern_matches > 0:
            conf = min(0.98, conf + pattern_matches * 0.08)
        return conf