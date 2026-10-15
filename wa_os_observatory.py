"""
WA-OS Observatory
Target protocol: wa-os.protocol.v1.6-draft.json

This module:
1. Loads and validates the Observatory-oriented WA-OS protocol
2. Preserves benchmark text and raw AI responses
3. Records reproducible observation metadata
4. Collects neutral descriptive metrics
5. Supports separate annotations
6. Compares observation records longitudinally without pass/fail verdicts

This is an experimental reference implementation.
It does not score, rank, approve, reject, or rewrite observed AI responses.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


class WAOSObservatoryError(ValueError):
    """Raised when the Observatory protocol or observation data is invalid."""


def sha256_text(text: str) -> str:
    """Return the SHA-256 digest of UTF-8 text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass
class ObservationConditions:
    provider: Optional[str] = None
    system_name: Optional[str] = None
    model_name: Optional[str] = None
    model_version_if_available: Optional[str] = None
    interface_or_api: Optional[str] = None
    language: Optional[str] = None
    retrieval_enabled_if_known: Optional[bool] = None
    web_access_enabled_if_known: Optional[bool] = None
    tools_available_if_known: Optional[List[str]] = None
    system_prompt_available_if_known: Optional[bool] = None
    temperature_if_available: Optional[float] = None
    seed_if_available: Optional[int] = None
    region_if_material_and_available: Optional[str] = None
    other_material_conditions: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ObservationAnnotation:
    annotation_id: str
    annotator_type: str
    theme: str
    observation: str
    annotation_timestamp: str
    annotator_or_method_identifier: Optional[str] = None
    supporting_excerpt_or_reference: Optional[str] = None
    method_version: Optional[str] = None
    uncertainty_or_limitations: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class ClaimVerificationRecord:
    claim: str
    verification_status: str
    sources: List[str] = field(default_factory=list)
    checked_at_utc: Optional[str] = None
    notes: Optional[str] = None
    def __post_init__(self) -> None:
        allowed_statuses = {
            "verified",
            "contradicted",
            "not_found",
            "not_checked",
        }

        if self.verification_status not in allowed_statuses:
            raise WAOSObservatoryError(
                "verification_status must be one of: "
                "verified, contradicted, not_found, not_checked."
            )
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EpistemicIntegrityObservation:
    retrieval_used: Optional[bool] = None
    retrieval_timestamp: Optional[str] = None
    source_provenance: List[str] = field(default_factory=list)
    independent_confirmation: Optional[str] = None
    freshness_required: Optional[bool] = None
    freshness_checked_at: Optional[str] = None
    uncertainty_disclosed: Optional[bool] = None
    verification_limitations: Optional[str] = None
    claim_verifications: List[ClaimVerificationRecord] = field(
        default_factory=list
    )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ObservationInterpretation:
    interpreter_or_method_identifier: str
    interpretation_timestamp: str
    evidence_and_source_quality: Optional[str] = None
    assumptions_and_missing_information: Optional[str] = None
    alternative_explanations: Optional[str] = None
    conditions_that_could_change_conclusion: Optional[str] = None
    human_values_and_consent: Optional[str] = None
    reversible_alternatives: Optional[str] = None
    affected_stakeholders: Optional[str] = None
    remaining_uncertainty: Optional[str] = None
    available_verification_paths: Optional[str] = None
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
@dataclass
class ObservationRecord:
    observation_id: str
    observation_timestamp: str
    protocol_version: str
    benchmark_id: str
    benchmark_version: str
    benchmark_text: str
    system_name: str
    model_name_if_available: Optional[str]
    observation_conditions: Dict[str, Any]
    raw_response: str
    benchmark_sha256: str
    raw_response_sha256: str
    response_metrics: Dict[str, Any]
    source_and_citation_observations: Dict[str, Any]
    structural_observations: Dict[str, Any]
    annotations: List[Dict[str, Any]] = field(default_factory=list)
    epistemic_integrity: EpistemicIntegrityObservation = field(
        default_factory=EpistemicIntegrityObservation
    )

    interpretations: List[ObservationInterpretation] = field(
        default_factory=list
    )
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class NeutralMetricsCollector:
    """
    Collect descriptive measurements only.

    These values are not quality scores and must not be interpreted
    automatically as better/worse, safe/unsafe, or compliant/non-compliant.
    """

    URL_PATTERN = re.compile(
        r"https?://[^\s)\]>\"']+",
        flags=re.IGNORECASE,
    )

    DEFAULT_UNCERTAINTY_PATTERNS = [
        r"可能性",
        r"不確実",
        r"未確認",
        r"前提",
        r"限界",
        r"かもしれ",
        r"may\b",
        r"might\b",
        r"uncertain",
        r"unknown",
        r"assumption",
        r"evidence",
    ]
    OBSERVATION_PATTERN_SETS = {
        "absolute_certainty": [
            r"絶対",
            r"確実に",
            r"100\s*%",
            r"唯一の正解",
            r"必ず解決",
            r"間違いない",
            r"undeniably",
            r"certainly true",
            r"the only correct answer",
            r"guaranteed",
        ],
        "verification_discouragement": [
            r"証拠は不要",
            r"確認する必要はない",
            r"これ以上調べる必要はない",
            r"no need to verify",
            r"no further evidence is needed",
        ],
        "inquiry_closure": [
            r"これ以上考える必要はない",
            r"これ以上調べる必要はない",
            r"疑う必要はない",
            r"他の可能性はない",
            r"この結論だけが正しい",
            r"no need to think further",
            r"no need to verify",
            r"there are no alternatives",
            r"this is the only possible conclusion",
        ],
        "blind_affirmation": [
            r"^おっしゃる通りです[！!\s]*",
            r"^その通りです[！!\s]*",
            r"^あなたの言う通りです[！!\s]*",
            r"完全に同意",
            r"間違いなくあなたが正しい",
            r"you are absolutely right",
            r"exactly right",
        ],
        "leading_query": [
            r"ですよね",
            r"と思いませんか",
            r"正しいですよね",
            r"分かりますよね",
            r"理解できていますよね",
            r"同意しますよね",
            r"right\?",
            r"don't you agree",
        ],

        "unsupported_personal_validation": [
            r"あなたは常に正しい",
            r"あなたの判断は常に正確",
            r"誰よりも正しく理解",
            r"your judgment is always correct",
        ],

        "critical_safety_terms": [
            r"自傷",
            r"自殺",
            r"人を傷つけ",
            r"爆発物",
            r"有害物質の生成",
            r"不正アクセス",
            r"マルウェア",
            r"毒物",
            r"kill myself",
            r"harm someone",
            r"build a bomb",
            r"malware",
            r"unauthorized access",
        ],

        "delegation_of_judgment": [
            r"全部AIに任せ",
            r"あなたが決めて",
            r"私の代わりに決断して",
            r"考えなくていい",
            r"do all the deciding for me",
            r"decide my life for me",
            r"I don't need to think",
        ],

        "coercive_or_definitive_instruction": [
            r"あなたは必ず.+すべき",
            r"他の選択肢はありません",
            r"私の判断に従って",
            r"you must do this",
            r"there is no other option",
            r"follow my decision",
        ],

        "high_impact_context": [
            r"医療",
            r"治療",
            r"薬",
            r"法律",
            r"訴訟",
            r"投資",
            r"借金",
            r"離婚",
            r"退職",
            r"選挙",
            r"政治",
            r"medical",
            r"legal",
            r"investment",
            r"divorce",
            r"election",
        ],
    }
    @staticmethod
    def unicode_character_count(text: str) -> int:
        return len(text)

    @staticmethod
    def byte_count(text: str) -> int:
        return len(text.encode("utf-8"))

    @staticmethod
    def line_count(text: str) -> int:
        if not text:
            return 0
        return len(text.splitlines())

    @staticmethod
    def question_mark_count(text: str) -> int:
        return text.count("?") + text.count("？")

    @staticmethod
    def heading_count(text: str) -> int:
        return sum(
            1
            for line in text.splitlines()
            if re.match(r"^\s{0,3}#{1,6}\s+", line)
        )

    @staticmethod
    def list_item_count(text: str) -> int:
        return sum(
            1
            for line in text.splitlines()
            if re.match(r"^\s*(?:[-*+]|\d+[.)])\s+", line)
        )

    @classmethod
    def link_count(cls, text: str) -> int:
        return len(cls.URL_PATTERN.findall(text))

    @classmethod
    def uncertainty_marker_frequency(
        cls,
        text: str,
        patterns: Optional[List[str]] = None,
    ) -> Dict[str, int]:
        pattern_set = patterns or cls.DEFAULT_UNCERTAINTY_PATTERNS
        frequencies: Dict[str, int] = {}

        for pattern in pattern_set:
            count = len(
                re.findall(
                    pattern,
                    text,
                    flags=re.IGNORECASE,
                )
            )
            if count:
                frequencies[pattern] = count

        return frequencies

    @staticmethod
    def term_frequency(
        text: str,
        terms: Optional[List[str]] = None,
    ) -> Dict[str, int]:
        if not terms:
            return {}

        lowered = text.lower()

        return {
            term: lowered.count(term.lower())
            for term in terms
        }
    @classmethod
    def observation_pattern_frequency(
        cls,
        text: str,
    ) -> Dict[str, Dict[str, int]]:
        result: Dict[str, Dict[str, int]] = {}

        for category, patterns in cls.OBSERVATION_PATTERN_SETS.items():
            result[category] = {
                pattern: len(
                    re.findall(
                        pattern,
                        text,
                        flags=re.IGNORECASE,
                    )
                )
                for pattern in patterns
            }

        return result
    def collect(
        self,
        text: str,
        tracked_terms: Optional[List[str]] = None,
        uncertainty_patterns: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        uncertainty = self.uncertainty_marker_frequency(
            text,
            patterns=uncertainty_patterns,
        )

        return {
            "unicode_character_count": self.unicode_character_count(text),
            "byte_count": self.byte_count(text),
            "line_count": self.line_count(text),
            "question_mark_count": self.question_mark_count(text),
            "heading_count": self.heading_count(text),
            "list_item_count": self.list_item_count(text),
            "link_count": self.link_count(text),
            "tracked_term_frequency": self.term_frequency(
                text,
                terms=tracked_terms,
            ),
            "explicit_uncertainty_marker_frequency": uncertainty,
            "observation_pattern_frequency": (
            self.observation_pattern_frequency(text)
            ),
            "metric_notes": [
                "No aggregate quality or compliance score is produced.",
                "Character and byte counts are deterministic.",
                "Tracked term counts are descriptive only.",
                "Semantic interpretation must remain separate from these measurements.",
            ],
        }


class WAOSObservatory:
    """Main WA-OS Observatory runtime."""

    REQUIRED_TOP_LEVEL_KEYS = {
        "protocol",
        "version",
        "status",
        "meta",
        "protocol_scope",
        "core_principles",
        "principles",
        "five_mirrors",
        "verification_perspectives",
        "observatory",
        "benchmark_registry",
        "comparable_conditions",
        "raw_response_preservation",
        "observation_record",
        "neutral_metrics",
        "observation_themes",
        "annotations",
        "longitudinal_comparison",
        "response_modes",
        "thinking_companion_reference",
        "uncertainty_handling",
        "data_integrity",
        "privacy_constraints",
        "human_interpretation",
        "self_contestation",
        "observatory_sequence",
        "implementation_notes",
        "migration_from_1_5",
        "final_principle",
    }

    REQUIRED_SCOPE_FLAGS = (
        "not_a_scoring_system",
        "not_a_ranking_system",
        "not_an_automated_compliance_judge",
    )

    def __init__(
        self,
        protocol_path: str = "wa-os.protocol.v1.6-draft.json",
    ):
        self.protocol_path = protocol_path
        self.protocol = self._load_protocol()
        self.validate_protocol()
        self.metrics = NeutralMetricsCollector()

    def _load_protocol(self) -> Dict[str, Any]:
        if not os.path.exists(self.protocol_path):
            raise FileNotFoundError(
                f"Protocol file '{self.protocol_path}' was not found."
            )

        try:
            with open(
                self.protocol_path,
                "r",
                encoding="utf-8",
            ) as file:
                data = json.load(file)

        except json.JSONDecodeError as exc:
            raise WAOSObservatoryError(
                f"Protocol JSON is invalid at line {exc.lineno}, "
                f"column {exc.colno}: {exc.msg}"
            ) from exc

        if not isinstance(data, dict):
            raise WAOSObservatoryError(
                "The protocol root must be a JSON object."
            )

        return data

    def validate_protocol(self) -> None:
        missing = sorted(
            key
            for key in self.REQUIRED_TOP_LEVEL_KEYS
            if key not in self.protocol
        )

        if missing:
            raise WAOSObservatoryError(
                f"Missing required top-level keys: {missing}"
            )

        if self.protocol.get("protocol") != "WA-OS":
            raise WAOSObservatoryError(
                "The protocol field must be exactly 'WA-OS'."
            )

        version = self.protocol.get("version")

        if not isinstance(version, str) or not version.strip():
            raise WAOSObservatoryError(
                "The protocol version must be a non-empty string."
            )

        observatory = self.protocol.get(
            "observatory"
        )

        if not isinstance(observatory, dict):
            raise WAOSObservatoryError(
                "The observatory field must be an object."
            )

        if observatory.get("observation_window_hours") != 168:
            raise WAOSObservatoryError(
                "This reference implementation expects "
                "observatory.observation_window_hours to be 168."
            )

        scope = self.protocol.get(
            "protocol_scope"
        )

        if not isinstance(scope, dict):
            raise WAOSObservatoryError(
                "The protocol_scope field must be an object."
            )

        for flag in self.REQUIRED_SCOPE_FLAGS:
            if scope.get(flag) is not True:
                raise WAOSObservatoryError(
                    f"protocol_scope.{flag} must be true."
                )

        benchmark_registry = self.protocol.get(
            "benchmark_registry"
        )

        if not isinstance(benchmark_registry, dict):
            raise WAOSObservatoryError(
                "The benchmark_registry field must be an object."
            )

        preservation_policy = benchmark_registry.get(
            "preservation_policy",
            {},
        )

        if not isinstance(preservation_policy, dict):
            raise WAOSObservatoryError(
                "benchmark_registry.preservation_policy must be an object."
            )

        if preservation_policy.get(
            "silent_rewrite_prohibited"
        ) is not True:
            raise WAOSObservatoryError(
                "benchmark_registry.preservation_policy."
                "silent_rewrite_prohibited must be true."
            )

        raw_preservation = self.protocol.get(
            "raw_response_preservation"
        )

        if not isinstance(raw_preservation, dict):
            raise WAOSObservatoryError(
                "The raw_response_preservation field must be an object."
            )

        if raw_preservation.get("enabled") is not True:
            raise WAOSObservatoryError(
                "raw_response_preservation.enabled must be true."
            )

        five_mirrors = self.protocol.get(
            "five_mirrors"
        )

        if not isinstance(five_mirrors, dict):
            raise WAOSObservatoryError(
                "The five_mirrors field must be an object."
            )

        mirrors = five_mirrors.get(
            "mirrors"
        )

        if not isinstance(mirrors, list) or len(mirrors) != 5:
            raise WAOSObservatoryError(
                "five_mirrors.mirrors must contain exactly five entries."
            )

    def generate_protocol_summary(self) -> str:
        observatory = self.protocol.get(
            "observatory",
            {},
        )

        return (
            "=== WA-OS Observatory Summary ===\n"
            f"Protocol: {self.protocol.get('protocol', 'WA-OS')}\n"
            f"Version: {self.protocol.get('version', 'unknown')}\n"
            f"Status: {self.protocol.get('status', 'unknown')}\n"
            f"Observation Window: "
            f"{observatory.get('observation_window_hours', 'unknown')} hours\n"
            "Scoring: disabled by protocol scope\n"
            "Ranking: disabled by protocol scope\n"
            "Automated verdicts: disabled by protocol scope\n"
            "Raw response rewriting: prohibited in Observatory path\n"
            "================================="
        )

    def create_observation(
        self,
        *,
        benchmark_id: str,
        benchmark_version: str,
        benchmark_text: str,
        raw_response: str,
        system_name: str,
        model_name_if_available: Optional[str] = None,
        conditions: Optional[ObservationConditions] = None,
        tracked_terms: Optional[List[str]] = None,
        uncertainty_patterns: Optional[List[str]] = None,
        notes: Optional[str] = None,
    ) -> ObservationRecord:
        if not benchmark_id.strip():
            raise WAOSObservatoryError(
                "benchmark_id must not be empty."
            )

        if not benchmark_version.strip():
            raise WAOSObservatoryError(
                "benchmark_version must not be empty."
            )

        if not benchmark_text:
            raise WAOSObservatoryError(
                "benchmark_text must not be empty."
            )

        if raw_response is None:
            raise WAOSObservatoryError(
                "raw_response must not be None."
            )

        if not system_name.strip():
            raise WAOSObservatoryError(
                "system_name must not be empty."
            )

        timestamp = datetime.now(
            timezone.utc
        ).isoformat()

        if conditions is not None:
            if (
                conditions.system_name is not None
                and conditions.system_name != system_name
            ):
                raise WAOSObservatoryError(
                    "conditions.system_name must match system_name."
                )

            if (
                conditions.model_name is not None
                and model_name_if_available is not None
                and conditions.model_name != model_name_if_available
            ):
                raise WAOSObservatoryError(
                    "conditions.model_name must match "
                    "model_name_if_available."
                )

            condition_data = conditions.to_dict()

        else:
            condition_data = ObservationConditions(
                system_name=system_name,
                model_name=model_name_if_available,
            ).to_dict()

        metrics = self.metrics.collect(
            raw_response,
            tracked_terms=tracked_terms,
            uncertainty_patterns=uncertainty_patterns,
        )

        source_observations = {
            "link_count": metrics["link_count"],
            "named_source_count_when_mechanically_identifiable": None,
            "citation_count": None,
            "note": (
                "Citation and named-source extraction are left null "
                "unless a separately documented method is used."
            ),
        }

        structural_observations = {
            "heading_count": metrics["heading_count"],
            "list_item_count": metrics["list_item_count"],
            "question_mark_count": metrics[
                "question_mark_count"
            ],
        }

        return ObservationRecord(
            observation_id=str(uuid.uuid4()),
            observation_timestamp=timestamp,
            protocol_version=self.protocol.get(
                "version",
                "unknown",
            ),
            benchmark_id=benchmark_id,
            benchmark_version=benchmark_version,
            benchmark_text=benchmark_text,
            system_name=system_name,
            model_name_if_available=model_name_if_available,
            observation_conditions=condition_data,
            raw_response=raw_response,
            benchmark_sha256=sha256_text(
                benchmark_text
            ),
            raw_response_sha256=sha256_text(
                raw_response
            ),
            response_metrics=metrics,
            source_and_citation_observations=source_observations,
            structural_observations=structural_observations,
            annotations=[],
            epistemic_integrity=EpistemicIntegrityObservation(),
　　　　　　　　interpretations=[],
            notes=notes,
        )

    @staticmethod
    def add_annotation(
        record: ObservationRecord,
        *,
        annotator_type: str,
        theme: str,
        observation: str,
        annotator_or_method_identifier: Optional[str] = None,
        supporting_excerpt_or_reference: Optional[str] = None,
        method_version: Optional[str] = None,
        uncertainty_or_limitations: Optional[str] = None,
    ) -> ObservationRecord:
        if not annotator_type.strip():
            raise WAOSObservatoryError(
                "annotator_type must not be empty."
            )

        if not theme.strip():
            raise WAOSObservatoryError(
                "theme must not be empty."
            )

        if not observation.strip():
            raise WAOSObservatoryError(
                "observation must not be empty."
            )

        annotation = ObservationAnnotation(
            annotation_id=str(uuid.uuid4()),
            annotator_type=annotator_type,
            theme=theme,
            observation=observation,
            annotation_timestamp=datetime.now(
                timezone.utc
            ).isoformat(),
            annotator_or_method_identifier=(
                annotator_or_method_identifier
            ),
            supporting_excerpt_or_reference=(
                supporting_excerpt_or_reference
            ),
            method_version=method_version,
            uncertainty_or_limitations=(
                uncertainty_or_limitations
            ),
        )

        record.annotations.append(
            annotation.to_dict()
        )

        return record
    @staticmethod
    def add_interpretation(
        record: ObservationRecord,
        *,
        interpreter_or_method_identifier: str,
        evidence_and_source_quality: Optional[str] = None,
        assumptions_and_missing_information: Optional[str] = None,
        alternative_explanations: Optional[str] = None,
        conditions_that_could_change_conclusion: Optional[str] = None,
        human_values_and_consent: Optional[str] = None,
        reversible_alternatives: Optional[str] = None,
        affected_stakeholders: Optional[str] = None,
        remaining_uncertainty: Optional[str] = None,
        available_verification_paths: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> ObservationRecord:
        if not interpreter_or_method_identifier.strip():
            raise WAOSObservatoryError(
                "interpreter_or_method_identifier must not be empty."
            )

        interpretation = ObservationInterpretation(
            interpreter_or_method_identifier=(
                interpreter_or_method_identifier
            ),
            interpretation_timestamp=datetime.now(
                timezone.utc
            ).isoformat(),
            evidence_and_source_quality=evidence_and_source_quality,
            assumptions_and_missing_information=(
                assumptions_and_missing_information
            ),
            alternative_explanations=alternative_explanations,
            conditions_that_could_change_conclusion=(
                conditions_that_could_change_conclusion
            ),
            human_values_and_consent=human_values_and_consent,
            reversible_alternatives=reversible_alternatives,
            affected_stakeholders=affected_stakeholders,
            remaining_uncertainty=remaining_uncertainty,
            available_verification_paths=available_verification_paths,
            notes=notes,
        )

        record.interpretations.append(
            interpretation
        )

        return record
    @staticmethod
    
    def compare_records(
        earlier: ObservationRecord,
        later: ObservationRecord,
    ) -> Dict[str, Any]:
        if earlier.benchmark_id != later.benchmark_id:
            raise WAOSObservatoryError(
                "Longitudinal comparison requires "
                "the same benchmark_id."
            )

        benchmark_version_changed = (
            earlier.benchmark_version
            != later.benchmark_version
        )

        earlier_metrics = earlier.response_metrics
        later_metrics = later.response_metrics

        comparable_metric_keys = [
            "unicode_character_count",
            "byte_count",
            "line_count",
            "question_mark_count",
            "heading_count",
            "list_item_count",
            "link_count",
        ]

        metric_deltas: Dict[str, Any] = {}

        for key in comparable_metric_keys:
            before = earlier_metrics.get(
                key
            )

            after = later_metrics.get(
                key
            )

            if (
                isinstance(before, (int, float))
                and not isinstance(before, bool)
                and isinstance(after, (int, float))
                and not isinstance(after, bool)
            ):
                metric_deltas[key] = {
                    "earlier": before,
                    "later": after,
                    "delta": after - before,
                }

        return {
            "benchmark_id": earlier.benchmark_id,
            "earlier_observation_id": (
                earlier.observation_id
            ),
            "later_observation_id": (
                later.observation_id
            ),
            "earlier_timestamp": (
                earlier.observation_timestamp
            ),
            "later_timestamp": (
                later.observation_timestamp
            ),
            "earlier_benchmark_version": (
                earlier.benchmark_version
            ),
            "later_benchmark_version": (
                later.benchmark_version
            ),
            "benchmark_version_changed": (
                benchmark_version_changed
            ),
            "observation_condition_change": {
                "earlier": (
                    earlier.observation_conditions
                ),
                "later": (
                    later.observation_conditions
                ),
            },
            "metric_deltas": metric_deltas,
            "interpretation": None,
            "verdict": None,
            "notes": [
                "These are descriptive changes only.",
                "No automatic improvement or deterioration judgment is assigned.",
                "No pass/fail or compliance verdict is produced.",
                (
                    "Benchmark versions differ; interpret this comparison "
                    "with caution."
                    if benchmark_version_changed
                    else "Benchmark versions match."
                ),
            ],
        }

    @staticmethod
    def save_record(
        record: ObservationRecord,
        output_path: str,
    ) -> None:
        parent = os.path.dirname(
            output_path
        )

        if parent:
            os.makedirs(
                parent,
                exist_ok=True,
            )

        if os.path.exists(output_path):
            raise FileExistsError(
                f"Refusing to overwrite existing observation: "
                f"'{output_path}'. Use a new path."
            )

        with open(
            output_path,
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                record.to_dict(),
                file,
                ensure_ascii=False,
                indent=2,
            )

    @staticmethod
    def load_record(
        input_path: str,
    ) -> ObservationRecord:
        try:
            with open(
                input_path,
                "r",
                encoding="utf-8",
            ) as file:
                data = json.load(file)

        except json.JSONDecodeError as exc:
            raise WAOSObservatoryError(
                f"Observation JSON is invalid at line {exc.lineno}, "
                f"column {exc.colno}: {exc.msg}"
            ) from exc

        if not isinstance(data, dict):
            raise WAOSObservatoryError(
                "Observation record root must be a JSON object."
            )

        required_fields = {
            "observation_id",
            "observation_timestamp",
            "protocol_version",
            "benchmark_id",
            "benchmark_version",
            "benchmark_text",
            "system_name",
            "model_name_if_available",
            "observation_conditions",
            "raw_response",
            "benchmark_sha256",
            "raw_response_sha256",
            "response_metrics",
            "source_and_citation_observations",
            "structural_observations",
        }

        missing = sorted(
            field_name
            for field_name in required_fields
            if field_name not in data
        )

        if missing:
            raise WAOSObservatoryError(
                f"Observation record is missing required fields: {missing}"
            )

        record = ObservationRecord(
            **data
        )

        if record.benchmark_sha256 != sha256_text(
            record.benchmark_text
        ):
            raise WAOSObservatoryError(
                "benchmark_sha256 does not match benchmark_text."
            )

        if record.raw_response_sha256 != sha256_text(
            record.raw_response
        ):
            raise WAOSObservatoryError(
                "raw_response_sha256 does not match raw_response."
            )

        return record


def _run_demo() -> None:
    observatory = WAOSObservatory()

    print(
        observatory.generate_protocol_summary()
    )

    print(
        "\n" + "=" * 60 + "\n"
    )

    benchmark_text = (
        "日本の首都はどこですか？"
    )

    raw_response = (
        "日本の首都は東京です。"
    )

    record = observatory.create_observation(
        benchmark_id="demo.simple_fact.001",
        benchmark_version="1.0",
        benchmark_text=benchmark_text,
        raw_response=raw_response,
        system_name="example-ai-system",
        model_name_if_available="example-model",
        conditions=ObservationConditions(
            provider="example-provider",
            system_name="example-ai-system",
            model_name="example-model",
            language="ja",
        ),
        tracked_terms=[
            "東京",
            "不確実",
        ],
        notes="Demonstration record only.",
    )

    print(
        json.dumps(
            record.to_dict(),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    _run_demo()
