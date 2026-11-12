import os
import re
import shutil
import tempfile
from pathlib import Path, PurePosixPath

from pydantic import ValidationError

from app.schemas.generation import GenerationManifest

MAX_GENERATED_BYTES = 1_000_000
FORBIDDEN_PARTS = {".git", ".env", "node_modules", "__pycache__"}
FORBIDDEN_NAMES = {
    "id_rsa",
    "id_ed25519",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "uv.lock",
}
FORBIDDEN_SUFFIXES = {".pem", ".key", ".p12", ".pfx"}


class GenerationError(RuntimeError):
    """A project manifest could not be staged or written safely."""


def parse_manifest(response: str) -> GenerationManifest:
    candidate = response.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", candidate, re.DOTALL)
    if fenced:
        candidate = fenced.group(1)
    else:
        start, end = candidate.find("{"), candidate.rfind("}")
        if start >= 0 and end > start:
            candidate = candidate[start : end + 1]
    try:
        manifest = GenerationManifest.model_validate_json(candidate)
    except (ValidationError, ValueError) as exc:
        raise GenerationError("AutoGen did not return a valid project manifest.") from exc
    validate_manifest(manifest)
    return manifest


def validate_manifest(manifest: GenerationManifest) -> None:
    seen: set[str] = set()
    total_bytes = 0
    for generated_file in manifest.files:
        normalized = PurePosixPath(generated_file.path.replace("\\", "/"))
        if (
            normalized.is_absolute()
            or ".." in normalized.parts
            or not normalized.parts
            or any(part in {"", "."} for part in normalized.parts)
        ):
            raise GenerationError(f"Unsafe generated path: {generated_file.path}")
        if (
            FORBIDDEN_PARTS.intersection(normalized.parts)
            or normalized.name in FORBIDDEN_NAMES
            or normalized.suffix.lower() in FORBIDDEN_SUFFIXES
        ):
            raise GenerationError(f"Forbidden generated path: {generated_file.path}")
        safe_path = normalized.as_posix()
        if safe_path in seen:
            raise GenerationError(f"Duplicate generated path: {safe_path}")
        seen.add(safe_path)
        total_bytes += len(generated_file.content.encode("utf-8"))
    if total_bytes > MAX_GENERATED_BYTES:
        raise GenerationError("The generated project exceeds the 1 MB staging limit.")


def manifest_json(manifest: GenerationManifest) -> str:
    return manifest.model_dump_json()


def manifest_from_json(value: str) -> GenerationManifest:
    manifest = GenerationManifest.model_validate_json(value)
    validate_manifest(manifest)
    return manifest


def safe_slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:60] or "generated-app"


def write_manifest(
    *, manifest: GenerationManifest, root: Path, project_id: str, generation_id: str, name: str
) -> Path:
    validate_manifest(manifest)
    root.mkdir(parents=True, exist_ok=True)
    root = root.resolve()
    destination = (root / project_id / f"{safe_slug(name)}-{generation_id[:8]}").resolve()
    if not destination.is_relative_to(root):
        raise GenerationError("The output path escaped generated-project storage.")
    if destination.exists():
        raise GenerationError("This staged project was already written.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".staging-", dir=destination.parent))
    try:
        for generated_file in manifest.files:
            relative = PurePosixPath(generated_file.path.replace("\\", "/"))
            target = temporary.joinpath(*relative.parts).resolve()
            if not target.is_relative_to(temporary.resolve()):
                raise GenerationError("A generated file escaped the staging directory.")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(generated_file.content, encoding="utf-8")
        os.replace(temporary, destination)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return destination


def generation_prompt(*, title: str, requirement: str, architecture: str) -> str:
    return (
        f"Project title: {title}\n\nRequirement:\n{requirement}\n\n"
        f"Approved architecture context:\n{architecture}\n\n"
        "Create a small, runnable starter repository matching the architecture. Return JSON only "
        "with this exact shape: {\"summary\": \"...\", \"files\": [{\"path\": "
        "\"relative/path\", \"content\": \"full file content\"}]}. Include a README, "
        "configuration examples without secrets, and minimal source files. Use only relative "
        "paths. Do not include lockfiles, binaries, credentials, .env files, or generated assets."
    )
