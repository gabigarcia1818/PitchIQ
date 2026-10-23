"""
Collect historical Statcast pitch data using pybaseball and store as Parquet chunks.
"""

import argparse
from datetime import datetime, timedelta
import logging
from pathlib import Path
import sys
import time
import pandas as pd

logger = logging.getLogger(__name__)

SEASON_DATES = {
    2021: ("2021-04-01", "2021-10-03"),
    2022: ("2022-04-07", "2022-10-05"),
    2023: ("2023-03-30", "2023-10-01"),
    2024: ("2024-03-20", "2024-09-30"),
    2025: ("2025-03-18", "2025-09-28"),
}


def date_chunks(start, end, chunk_days=7):
    """Split a date range into consecutive chunks of chunk_days."""
    if isinstance(start, str):
        start_date = datetime.strptime(start, "%Y-%m-%d").date()
    elif isinstance(start, datetime):
        start_date = start.date()
    else:
        start_date = start

    if isinstance(end, str):
        end_date = datetime.strptime(end, "%Y-%m-%d").date()
    elif isinstance(end, datetime):
        end_date = end.date()
    else:
        end_date = end

    chunks = []
    curr = start_date
    while curr <= end_date:
        chunk_end = min(curr + timedelta(days=chunk_days - 1), end_date)
        chunks.append((curr.strftime("%Y-%m-%d"), chunk_end.strftime("%Y-%m-%d")))
        curr = chunk_end + timedelta(days=1)
    return chunks


def season_chunks(season, chunk_days=7):
    """Get date chunks for a specific MLB season's regular season window."""
    if season not in SEASON_DATES:
        raise ValueError(f"Season {season} not supported. Available seasons: {list(SEASON_DATES.keys())}")
    start_str, end_str = SEASON_DATES[season]
    return date_chunks(start_str, end_str, chunk_days)


def fetch_chunk(start, end, retries=3, backoff=5, fetcher=None):
    """Fetch Statcast data for a date range with retries and exponential backoff."""
    if fetcher is None:
        import pybaseball
        fetcher = pybaseball.statcast

    for attempt in range(retries):
        try:
            logger.info("Fetching Statcast data for %s to %s (attempt %d/%d)", start, end, attempt + 1, retries)
            df = fetcher(start, end)
            return df
        except Exception as e:
            sleep_sec = backoff * (2 ** attempt)
            logger.warning("Attempt %d failed for %s to %s: %s. Retrying in %ds...", attempt + 1, start, end, e, sleep_sec)
            if attempt < retries - 1:
                time.sleep(sleep_sec)
            else:
                logger.error("All %d retries failed for %s to %s", retries, start, end)
    return None


def collect(seasons=None, start=None, end=None, chunk_days=7, out_dir=None, force=False, retries=3, backoff=5, combine=False, fetcher=None):
    """Collect Statcast data for requested seasons or date range into parquet chunks."""
    if out_dir is None:
        out_dir = Path(__file__).parent / "data"
    else:
        out_dir = Path(out_dir)

    raw_dir = out_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    tasks = []
    if start or end:
        if not (start and end):
            raise ValueError("--start and --end must be used together")
        chunks = date_chunks(start, end, chunk_days)
        tasks.append((None, chunks))
    else:
        if seasons is None:
            seasons = [2021, 2022, 2023, 2024, 2025]
        for season in seasons:
            chunks = season_chunks(season, chunk_days)
            tasks.append((season, chunks))

    stats = {"downloaded": 0, "cached": 0, "failed": 0}
    all_season_files = {}

    for season, chunks in tasks:
        season_chunk_files = []
        for chunk_start, chunk_end in chunks:
            parquet_path = raw_dir / f"statcast_{chunk_start}_{chunk_end}.parquet"
            marker_path = raw_dir / f"statcast_{chunk_start}_{chunk_end}.empty"

            is_cached = parquet_path.exists() or marker_path.exists()

            if is_cached and not force:
                logger.info("Skipping cached chunk %s to %s", chunk_start, chunk_end)
                stats["cached"] += 1
                if parquet_path.exists():
                    season_chunk_files.append(parquet_path)
                continue

            df = fetch_chunk(chunk_start, chunk_end, retries=retries, backoff=backoff, fetcher=fetcher)
            if df is None:
                stats["failed"] += 1
                logger.error("Chunk %s to %s failed permanently.", chunk_start, chunk_end)
                continue

            if not df.empty and "game_type" in df.columns:
                df = df[df["game_type"] == "R"]

            if df.empty:
                logger.info("Chunk %s to %s resulted in empty data. Writing empty marker.", chunk_start, chunk_end)
                marker_path.touch()
                if parquet_path.exists():
                    parquet_path.unlink()
                stats["downloaded"] += 1
            else:
                df.to_parquet(parquet_path, index=False)
                logger.info("Saved %d rows to %s", len(df), parquet_path)
                season_chunk_files.append(parquet_path)
                stats["downloaded"] += 1

        if season is not None:
            all_season_files[season] = season_chunk_files
        else:
            all_season_files[f"{start}_{end}"] = season_chunk_files

    if combine:
        logger.info("Combining chunk files...")
        for key, files in all_season_files.items():
            if not files:
                logger.warning("No non-empty chunk files to combine for %s", key)
                continue
            dfs = [pd.read_parquet(f) for f in files]
            if not dfs:
                continue
            combined_df = pd.concat(dfs, ignore_index=True)
            if isinstance(key, int):
                combined_path = raw_dir / f"statcast_{key}.parquet"
            else:
                combined_path = raw_dir / f"statcast_{key}_combined.parquet"
            combined_df.to_parquet(combined_path, index=False)
            logger.info("Wrote combined dataset to %s (%d rows)", combined_path, len(combined_df))

    logger.info("Collection summary: downloaded=%d, cached=%d, failed=%d", stats["downloaded"], stats["cached"], stats["failed"])
    return stats


def main(argv=None):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    parser = argparse.ArgumentParser(description="Collect historical Statcast pitch data.")
    parser.add_argument("--seasons", type=int, nargs="+", default=[2021, 2022, 2023, 2024, 2025], help="Seasons to collect")
    parser.add_argument("--start", type=str, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", type=str, help="End date (YYYY-MM-DD)")
    parser.add_argument("--chunk-days", type=int, default=7, help="Days per date chunk")
    parser.add_argument("--out", type=str, help="Output directory")
    parser.add_argument("--force", action="store_true", help="Force re-download even if cached")
    parser.add_argument("--retries", type=int, default=3, help="Max retry attempts per chunk")
    parser.add_argument("--backoff", type=float, default=5.0, help="Base backoff seconds for retries")
    parser.add_argument("--combine", action="store_true", help="Combine chunk files per season/range after download")

    args = parser.parse_args(argv)

    stats = collect(
        seasons=args.seasons if not (args.start or args.end) else None,
        start=args.start,
        end=args.end,
        chunk_days=args.chunk_days,
        out_dir=args.out,
        force=args.force,
        retries=args.retries,
        backoff=args.backoff,
        combine=args.combine,
    )

    if stats["failed"] > 0:
        logger.error("Collection completed with %d failed chunks.", stats["failed"])
        sys.exit(1)
    else:
        logger.info("Collection completed successfully.")


if __name__ == "__main__":
    main()
