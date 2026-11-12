import os
import re
import shutil
import tempfile
from pathlib import Path, PurePosixPath
from uuid import UUID

from pydantic import ValidationError

from app.schemas.generation import GenerationManifest
from app.schemas.review import ReviewReport
from app.services.generation import GenerationError, validate_manifest


class ReviewError(RuntimeError):
    """A review or generated test manifest could not be handled safely."""


def _json_object(response: str) -> str:
    candidate = response.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", candidate, re.DOTALL)
    if fenced:
        return fenced.group(1)
    start, end = candidate.find("{"), candidate.rfind("}")
    return candidate[start : end + 1] if start >= 0 and end > start else candidate


def parse_review(response: str) -> ReviewReport:
    try:
        return ReviewReport.model_validate_json(_json_object(response))
    except (ValidationError, ValueError) as exc:
        raise ReviewError("The Code Reviewer did not return a valid report.") from exc


def parse_test_manifest(response: str) -> GenerationManifest:
    try:
        manifest = GenerationManifest.model_validate_json(_json_object(response))
        validate_manifest(manifest)
    except (ValidationError, ValueError, GenerationError) as exc:
        raise ReviewError("The Test Designer did not return a safe test manifest.") from exc
    for generated_file in manifest.files:
        path = PurePosixPath(generated_file.path.replace("\\", "/"))
        is_test = (
            "tests" in path.parts
            or ".test." in path.name
            or ".spec." in path.name
            or path.name.startswith("test_")
        )
        if not is_test:
            raise ReviewError(f"Generated test path is outside a test location: {path}")
    return manifest


def review_json(report: ReviewReport) -> str:
    return report.model_dump_json()


def tests_json(manifest: GenerationManifest) -> str:
    return manifest.model_dump_json()


def report_from_json(value: str) -> ReviewReport:
    return ReviewReport.model_validate_json(value)


def tests_from_json(value: str) -> GenerationManifest:
    return parse_test_manifest(value)


def review_prompt(manifest: GenerationManifest) -> str:
    return (
        "Review this generated project manifest for correctness, security, maintainability, "
        "error handling, and requirement gaps. Do not execute anything. Return JSON only with "
        "shape {\"summary\":\"...\",\"findings\":[{\"severity\":\"critical|high|medium|low|info\","
        "\"path\":\"optional/file\",\"issue\":\"...\",\"recommendation\":\"...\"}]}.\n\n"
        + manifest.model_dump_json()
    )


def test_prompt(manifest: GenerationManifest, report: ReviewReport) -> str:
    return (
        "Design focused tests for this project and its review findings. Do not execute anything. "
        "Return JSON only with shape {\"summary\":\"...\",\"files\":[{\"path\":\"tests/...\","
        "\"content\":\"complete test source\"}]}. All paths must clearly be test files.\n\n"
        f"Project manifest:\n{manifest.model_dump_json()}\n\nReview:\n{report.model_dump_json()}"
    )


def write_test_manifest(
    manifest: GenerationManifest, output_path: Path, review_id: UUID, generated_root: Path
) -> None:
    manifest = parse_test_manifest(manifest.model_dump_json())
    output_path = output_path.resolve()
    if not output_path.is_relative_to(generated_root.resolve()):
        raise ReviewError("The generated project is outside restricted storage.")
    if not output_path.is_dir():
        raise ReviewError("Approve and write the generated project before adding tests.")
    temporary = Path(tempfile.mkdtemp(prefix=f".tests-{str(review_id)[:8]}-", dir=output_path))
    try:
        targets: list[tuple[Path, Path]] = []
        for generated_file in manifest.files:
            relative = PurePosixPath(generated_file.path.replace("\\", "/"))
            target = output_path.joinpath(*relative.parts).resolve()
            if not target.is_relative_to(output_path):
                raise ReviewError("A test file escaped generated-project storage.")
            if target.exists():
                raise ReviewError(f"A generated test would overwrite an existing file: {relative}")
            staged = temporary.joinpath(*relative.parts)
            staged.parent.mkdir(parents=True, exist_ok=True)
            staged.write_text(generated_file.content, encoding="utf-8")
            targets.append((staged, target))
        for staged, target in targets:
            target.parent.mkdir(parents=True, exist_ok=True)
            os.replace(staged, target)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    shutil.rmtree(temporary, ignore_errors=True)
