"""Pinned source identity and the local execution artifact.

package_version is source metadata. It is not an npm registry artifact and
not an official published image. registry_digest stays empty.
"""

from __future__ import annotations

import hashlib
import json

SOURCE_REPOSITORY = "https://github.com/modelcontextprotocol/servers"
SOURCE_COMMIT = "f46d9578190b476b3501923ea8977d899e8db2cb"
COMPONENT_PATH = "src/everything"
PACKAGE_NAME = "@modelcontextprotocol/server-everything"
PACKAGE_VERSION = "2.0.0"
ARTIFACT_ORIGIN = "locally_built_from_pinned_source"
BUILD_RECIPE = "npm ci --ignore-scripts && tsc -p src/everything/tsconfig.json"
BUILD_RECIPE_VERSION = "1"
LOCKFILE_SHA256 = "df3034c8bb82e772389fa4518793c0cee24361c581c66e7bb04d0d7270dc24e1"
NODE_VERSION = "v22.12.0"
NPM_VERSION = "10.9.0"
BASE_IMAGE_ID = "sha256:51eff88af6dff26f59316b6e356188ffa2c422bd3c3b76f2556a2e7e89d080bd"
LOCAL_IMAGE_ID = "sha256:5f1784c80a95be56091a16ac8f6955b32eb170dcf89ee3b9d2cb86c0b26fe1d6"
REGISTRY_DIGEST = None
BUILD_TIMESTAMP = "2026-09-26T05:44:34.512508881-07:00"
CONTAINER_ARGV = ("node", "dist/index.js", "stdio")
CONTAINER_WORKDIR = "/src/src/everything"


def source_identity() -> dict[str, str]:
    return {
        "source_repository": SOURCE_REPOSITORY,
        "source_commit": SOURCE_COMMIT,
        "component_path": COMPONENT_PATH,
        "package_name": PACKAGE_NAME,
        "package_version": PACKAGE_VERSION,
        "package_version_meaning": "source package metadata, not an npm registry artifact",
    }


def identity_material(source: dict[str, object], artifact: dict[str, object]) -> dict[str, object]:
    """Canonical identity. Lockfile is named once. No second copy of the facts."""
    return {
        "source_repository": source["source_repository"],
        "source_commit": source["source_commit"],
        "component_path": source["component_path"],
        "package_name": source["package_name"],
        "package_version": source["package_version"],
        "package_version_meaning": source.get("package_version_meaning"),
        "lockfile_sha256": artifact["lockfile_sha256"],
        "artifact_origin": artifact["artifact_origin"],
        "build_recipe": artifact["build_recipe"],
        "build_recipe_version": artifact["build_recipe_version"],
        "node_version": artifact["node_version"],
        "npm_version": artifact["npm_version"],
        "base_image_id": artifact["base_image_id"],
        "local_image_id": artifact["local_image_id"],
        "registry_digest": artifact["registry_digest"],
    }


def identity_reference(source: dict[str, object], artifact: dict[str, object]) -> str:
    blob = json.dumps(
        identity_material(source, artifact),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(blob).hexdigest()


def execution_artifact() -> dict[str, str | None]:
    return {
        "artifact_origin": ARTIFACT_ORIGIN,
        "build_recipe": BUILD_RECIPE,
        "build_recipe_version": BUILD_RECIPE_VERSION,
        "lockfile_sha256": LOCKFILE_SHA256,
        "node_version": NODE_VERSION,
        "npm_version": NPM_VERSION,
        "base_image_id": BASE_IMAGE_ID,
        "local_image_id": LOCAL_IMAGE_ID,
        "registry_digest": REGISTRY_DIGEST,
        "build_timestamp": BUILD_TIMESTAMP,
    }
