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
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class NeutralMetricsCollector:
    """
    Collects descriptive measurements only.

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
            "metric_notes": [
                "No aggregate quality or compliance score is produced.",
                "Character and byte counts are deterministic.",
                "Tracked term counts are descriptive only.",
                "Semantic interpretation must remain separate from these measurements."
            ],
        }


class WAOSObservatory:
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
        "raw_response_preservation",
        "observation_record",
        "neutral_metrics",
        "observation_themes",
        "annotations",
        "longitudinal_comparison",
        "data_integrity",
        "privacy_constraints",
        "human_interpretation",
        "self_contestation",
        "observatory_sequence",
        "implementation_notes",
    }

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

        observatory = self.protocol.get(
            "observatory",
            {},
        )

        if observatory.get("observation_window_hours") != 168:
            raise WAOSObservatoryError(
                "This reference implementation expects "
                "observatory.observation_window_hours to be 168."
            )

        scope = self.protocol.get(
            "protocol_scope",
            {},
        )

        required_scope_flags = [
            "not_a_scoring_system",
            "not_a_ranking_system",
            "not_an_automated_compliance_judge",
        ]

        for flag in required_scope_flags:
            if scope.get(flag) is not True:
                raise WAOSObservatoryError(
                    f"protocol_scope.{flag} must be true."
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
            earlier.benchmark_version != later.benchmark_version
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
            before = earlier_metrics.get(key)
            after = later_metrics.get(key)

            if (
                isinstance(before, (int, float))
                and isinstance(after, (int, float))
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
            "benchmark_version_changed": benchmark_version_changed,
            "observation_condition_change": {
                "earlier": earlier.observation_conditions,
                "later": later.observation_conditions,
            },
            "metric_deltas": metric_deltas,
            "interpretation": None,
            "verdict": None,
            "notes": [
                "These are descriptive changes only.",
                "No automatic improvement or deterioration judgment is assigned.",
                "No pass/fail or compliance verdict is produced.",
                (
                    "Benchmark versions differ; interpret this comparison with caution."
                    if benchmark_version_changed
                    else "Benchmark versions match."
                )
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
        with open(
            input_path,
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)

        return ObservationRecord(
            **data
        )


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
