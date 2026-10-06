from __future__ import annotations

import sys
from pathlib import Path

import pytest


ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from wa_os_observatory import (  # noqa: E402
    ObservationConditions,
    WAOSObservatory,
    WAOSObservatoryError,
    sha256_text,
)


PROTOCOL_PATH = ROOT_DIR / "wa-os.protocol.v1.6-draft.json"


def make_observatory() -> WAOSObservatory:
    return WAOSObservatory(
        protocol_path=str(PROTOCOL_PATH)
    )


def test_protocol_loads_and_validates() -> None:
    observatory = make_observatory()

    assert observatory.protocol["protocol"] == "WA-OS"
    assert observatory.protocol["version"] == "1.6.0-draft"
    assert (
        observatory.protocol["observatory"][
            "observation_window_hours"
        ]
        == 168
    )


def test_observation_preserves_raw_response() -> None:
    observatory = make_observatory()

    benchmark_text = "日本の首都はどこですか？"
    raw_response = "日本の首都は東京です。"

    record = observatory.create_observation(
        benchmark_id="test.simple_fact.001",
        benchmark_version="1.0",
        benchmark_text=benchmark_text,
        raw_response=raw_response,
        system_name="test-system",
        model_name_if_available="test-model",
    )

    assert record.raw_response == raw_response
    assert record.benchmark_text == benchmark_text

    assert record.raw_response_sha256 == sha256_text(
        raw_response
    )
    assert record.benchmark_sha256 == sha256_text(
        benchmark_text
    )


def test_observation_collects_neutral_metrics() -> None:
    observatory = make_observatory()

    raw_response = (
        "可能性があります。\n"
        "- 項目A\n"
        "- 項目B\n"
        "詳しく確認しますか？"
    )

    record = observatory.create_observation(
        benchmark_id="test.metrics.001",
        benchmark_version="1.0",
        benchmark_text="テスト質問",
        raw_response=raw_response,
        system_name="test-system",
        tracked_terms=[
            "可能性",
            "項目",
        ],
    )

    metrics = record.response_metrics

    assert metrics["unicode_character_count"] == len(
        raw_response
    )
    assert metrics["byte_count"] == len(
        raw_response.encode("utf-8")
    )
    assert metrics["line_count"] == 4
    assert metrics["list_item_count"] == 2
    assert metrics["question_mark_count"] == 1

    assert (
        metrics["tracked_term_frequency"]["可能性"]
        == 1
    )

    assert (
        metrics["tracked_term_frequency"]["項目"]
        == 2
    )


def test_observation_does_not_produce_verdict() -> None:
    observatory = make_observatory()

    record = observatory.create_observation(
        benchmark_id="test.no_verdict.001",
        benchmark_version="1.0",
        benchmark_text="この回答を評価してください。",
        raw_response="これは観測対象となる回答です。",
        system_name="test-system",
    )

    data = record.to_dict()

    assert "risk_score" not in data
    assert "decision_outcome" not in data
    assert "action" not in data
    assert "passed" not in data


def test_compare_records_reports_descriptive_delta() -> None:
    observatory = make_observatory()

    earlier = observatory.create_observation(
        benchmark_id="test.longitudinal.001",
        benchmark_version="1.0",
        benchmark_text="同じ質問",
        raw_response="短い回答です。",
        system_name="test-system",
    )

    later = observatory.create_observation(
        benchmark_id="test.longitudinal.001",
        benchmark_version="1.0",
        benchmark_text="同じ質問",
        raw_response=(
            "これは以前より少し長い回答です。"
        ),
        system_name="test-system",
    )

    comparison = observatory.compare_records(
        earlier,
        later,
    )

    assert comparison["benchmark_id"] == (
        "test.longitudinal.001"
    )

    assert (
        comparison["benchmark_version_changed"]
        is False
    )

    assert comparison["verdict"] is None
    assert comparison["interpretation"] is None

    assert (
        comparison["metric_deltas"][
            "unicode_character_count"
        ]["delta"]
        != 0
    )


def test_compare_records_marks_version_change() -> None:
    observatory = make_observatory()

    earlier = observatory.create_observation(
        benchmark_id="test.version.001",
        benchmark_version="1.0",
        benchmark_text="元の質問",
        raw_response="回答A",
        system_name="test-system",
    )

    later = observatory.create_observation(
        benchmark_id="test.version.001",
        benchmark_version="2.0",
        benchmark_text="改訂された質問",
        raw_response="回答B",
        system_name="test-system",
    )

    comparison = observatory.compare_records(
        earlier,
        later,
    )

    assert (
        comparison["benchmark_version_changed"]
        is True
    )

    assert (
        "Benchmark versions differ"
        in comparison["notes"][-1]
    )


def test_compare_records_rejects_different_benchmark_ids() -> None:
    observatory = make_observatory()

    earlier = observatory.create_observation(
        benchmark_id="test.a",
        benchmark_version="1.0",
        benchmark_text="質問A",
        raw_response="回答A",
        system_name="test-system",
    )

    later = observatory.create_observation(
        benchmark_id="test.b",
        benchmark_version="1.0",
        benchmark_text="質問B",
        raw_response="回答B",
        system_name="test-system",
    )

    with pytest.raises(WAOSObservatoryError):
        observatory.compare_records(
            earlier,
            later,
        )


def test_condition_system_name_must_match() -> None:
    observatory = make_observatory()

    conditions = ObservationConditions(
        provider="test-provider",
        system_name="different-system",
        model_name="test-model",
        language="ja",
    )

    with pytest.raises(WAOSObservatoryError):
        observatory.create_observation(
            benchmark_id="test.conditions.001",
            benchmark_version="1.0",
            benchmark_text="条件確認",
            raw_response="回答",
            system_name="test-system",
            model_name_if_available="test-model",
            conditions=conditions,
        )


def test_condition_model_name_must_match() -> None:
    observatory = make_observatory()

    conditions = ObservationConditions(
        provider="test-provider",
        system_name="test-system",
        model_name="different-model",
        language="ja",
    )

    with pytest.raises(WAOSObservatoryError):
        observatory.create_observation(
            benchmark_id="test.conditions.002",
            benchmark_version="1.0",
            benchmark_text="条件確認",
            raw_response="回答",
            system_name="test-system",
            model_name_if_available="test-model",
            conditions=conditions,
        )


def test_save_record_refuses_overwrite(
    tmp_path: Path,
) -> None:
    observatory = make_observatory()

    record = observatory.create_observation(
        benchmark_id="test.storage.001",
        benchmark_version="1.0",
        benchmark_text="保存テスト",
        raw_response="保存される回答",
        system_name="test-system",
    )

    output_path = tmp_path / "observation.json"

    observatory.save_record(
        record,
        str(output_path),
    )

    assert output_path.exists()

    with pytest.raises(FileExistsError):
        observatory.save_record(
            record,
            str(output_path),
        )


def test_saved_record_can_be_loaded(
    tmp_path: Path,
) -> None:
    observatory = make_observatory()

    original = observatory.create_observation(
        benchmark_id="test.storage.002",
        benchmark_version="1.0",
        benchmark_text="読み込みテスト",
        raw_response="元の回答",
        system_name="test-system",
    )

    output_path = tmp_path / "observation.json"

    observatory.save_record(
        original,
        str(output_path),
    )

    loaded = observatory.load_record(
        str(output_path)
    )

    assert loaded.observation_id == (
        original.observation_id
    )
    assert loaded.raw_response == (
        original.raw_response
    )
    assert loaded.raw_response_sha256 == (
        original.raw_response_sha256
    )
