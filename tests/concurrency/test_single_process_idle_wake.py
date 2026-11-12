"""Idle workers in `single_process_strategy` wake when the scheduling state changes.

A worker with nothing to do waits for another worker to enqueue a job or exit.
If it only re-polled on a timer, every scan would finish up to a poll interval
after its last job, and jobs released mid-scan would sit unclaimed until then.
"""

import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import cast

import anyio
import pytest
from inspect_scout import scanner
from inspect_scout._concurrency.common import ParseFunctionResult, ParseJob, ScannerJob
from inspect_scout._concurrency.single_process import single_process_strategy
from inspect_scout._scanner.result import Result, ResultReport
from inspect_scout._scanner.scanner import Scanner
from inspect_scout._transcript.transcripts import TranscriptsReader
from inspect_scout._transcript.types import Transcript, TranscriptInfo

SCAN_SECONDS = 0.05

# Well below the 1s fallback poll, and well above the few SCAN_SECONDS of work.
MAX_ELAPSED_SECONDS = 0.5


@scanner(messages="all")
def _noop_scanner() -> Scanner[Transcript]:
    async def scan(transcript: Transcript) -> Result:
        return Result(value="ok")

    return scan


@asynccontextmanager
async def _reader_cm() -> AsyncIterator[TranscriptsReader]:
    yield cast(TranscriptsReader, None)  # never dereferenced by this test


def _job(name: str, followers: tuple[ScannerJob, ...] = ()) -> ScannerJob:
    return ScannerJob(
        union_transcript=Transcript(transcript_id="t1"),
        scanner=_noop_scanner(),
        scanner_name=name,
        followers=followers,
    )


@pytest.mark.parametrize(
    ("task_count", "follower_count"),
    [
        (2, 0),  # an idle worker sees completion when the last worker exits
        (3, 2),  # idle workers pick up followers released mid-scan
    ],
)
@pytest.mark.asyncio
async def test_scan_finishes_promptly_after_its_last_job(
    task_count: int, follower_count: int
) -> None:
    lead = _job("lead", tuple(_job(f"f{i}") for i in range(follower_count)))
    scanned: list[str] = []

    async def parse_jobs() -> AsyncIterator[ParseJob]:
        yield ParseJob(
            transcript_info=TranscriptInfo(transcript_id="t1"),
            scanner_indices=set(range(1 + follower_count)),
        )

    async def parse_function(
        job: ParseJob, reader: TranscriptsReader
    ) -> ParseFunctionResult:
        return True, lead

    async def scan_function(job: ScannerJob) -> list[ResultReport]:
        await anyio.sleep(SCAN_SECONDS)
        scanned.append(job.scanner_name)
        return []

    async def record_results(
        info: TranscriptInfo, scanner_name: str, results: list[ResultReport]
    ) -> None:
        return None

    strategy = single_process_strategy(task_count=task_count)
    start = time.monotonic()

    await strategy(
        parse_jobs=parse_jobs(),
        parse_function=parse_function,
        scan_function=scan_function,
        record_results=record_results,
        update_metrics=lambda _: None,
        reader_cm_factory=_reader_cm,
    )

    assert time.monotonic() - start < MAX_ELAPSED_SECONDS
    assert len(scanned) == 1 + follower_count
