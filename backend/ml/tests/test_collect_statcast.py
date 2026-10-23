import pytest
import pandas as pd
from pathlib import Path
from ml.collect_statcast import date_chunks, season_chunks, fetch_chunk, collect


def test_date_chunks():
    chunks = date_chunks("2024-04-01", "2024-04-15", chunk_days=7)
    assert chunks == [
        ("2024-04-01", "2024-04-07"),
        ("2024-04-08", "2024-04-14"),
        ("2024-04-15", "2024-04-15"),
    ]


def test_season_chunks():
    chunks = season_chunks(2024, chunk_days=30)
    assert len(chunks) > 0
    assert chunks[0][0] == "2024-03-20"
    assert chunks[-1][1] == "2024-09-30"


def test_fetch_chunk_success():
    def fake_fetcher(start, end):
        return pd.DataFrame({"game_date": [start], "game_type": ["R"]})

    df = fetch_chunk("2024-04-01", "2024-04-07", retries=3, backoff=0.01, fetcher=fake_fetcher)
    assert df is not None
    assert len(df) == 1


def test_fetch_chunk_retry_then_success():
    attempts = 0

    def fake_fetcher(start, end):
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise ConnectionError("Network error")
        return pd.DataFrame({"game_date": [start], "game_type": ["R"]})

    df = fetch_chunk("2024-04-01", "2024-04-07", retries=3, backoff=0.001, fetcher=fake_fetcher)
    assert df is not None
    assert attempts == 3


def test_fetch_chunk_always_fails():
    def fake_fetcher(start, end):
        raise ConnectionError("Persistent error")

    df = fetch_chunk("2024-04-01", "2024-04-07", retries=2, backoff=0.001, fetcher=fake_fetcher)
    assert df is None


def test_collect_cached_skipped(tmp_path):
    out_dir = tmp_path / "data"
    raw_dir = out_dir / "raw"
    raw_dir.mkdir(parents=True)

    cached_file = raw_dir / "statcast_2024-04-01_2024-04-07.parquet"
    df_sample = pd.DataFrame({"game_date": ["2024-04-01"], "game_type": ["R"]})
    df_sample.to_parquet(cached_file)

    fetch_called = False

    def fake_fetcher(start, end):
        nonlocal fetch_called
        fetch_called = True
        return pd.DataFrame()

    stats = collect(
        start="2024-04-01",
        end="2024-04-07",
        chunk_days=7,
        out_dir=out_dir,
        fetcher=fake_fetcher,
    )
    assert not fetch_called
    assert stats["cached"] == 1
    assert stats["downloaded"] == 0
    assert stats["failed"] == 0


def test_collect_failure_reports_failed(tmp_path):
    out_dir = tmp_path / "data"

    def fake_fetcher(start, end):
        raise RuntimeError("Always fail")

    stats = collect(
        start="2024-04-01",
        end="2024-04-07",
        chunk_days=7,
        out_dir=out_dir,
        retries=1,
        backoff=0.001,
        fetcher=fake_fetcher,
    )
    assert stats["failed"] == 1
