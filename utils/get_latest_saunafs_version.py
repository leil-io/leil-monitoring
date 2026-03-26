#!/usr/bin/env python3
# This file is part of saunafs-monitoring.
# Copyright (C) 2025 Leil Storage OÜ
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
from contextlib import closing
from http.client import HTTPResponse
import json
import re
import sys
from typing import cast
import urllib.request


DEBIAN_PACKAGE_TAGS_URL = "https://api.github.com/repos/leil-io/debian-package/tags?per_page=100"
TAG_PATTERN = re.compile(r"^(?P<release>\d+(?:\.\d+)*)(?:-(?P<revision>\d+))?$")


def normalize_tag(tag_name: str) -> str:
    normalized = tag_name.strip()
    if normalized.startswith("v"):
        normalized = normalized[1:]
    if not normalized or any(character.isspace() for character in normalized):
        raise ValueError(f"Invalid SaunaFS release tag: {tag_name!r}")
    if TAG_PATTERN.fullmatch(normalized) is None:
        raise ValueError(f"Unsupported debian-package tag format: {tag_name!r}")
    return normalized


def parse_version_key(tag_name: str) -> tuple[tuple[int, ...], int]:
    match = TAG_PATTERN.fullmatch(tag_name)
    if match is None:
        raise ValueError(f"Unsupported debian-package tag format: {tag_name!r}")

    release = tuple(int(part) for part in match.group("release").split("."))
    revision_text = match.group("revision")
    revision = int(revision_text) if revision_text is not None else 0
    return release, revision


def fetch_latest_release_tag() -> str:
    request = urllib.request.Request(
        DEBIAN_PACKAGE_TAGS_URL,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "saunafs-monitoring-ci",
        },
    )
    with closing(cast(HTTPResponse, urllib.request.urlopen(request, timeout=30))) as response:
        payload_raw = cast(object, json.loads(response.read().decode("utf-8")))

    if not isinstance(payload_raw, list):
        raise ValueError("GitHub tags payload was not a JSON array")

    payload = cast(list[object], payload_raw)
    normalized_tags: list[str] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        tag_data = cast(dict[str, object], item)
        tag_name = tag_data.get("name")
        if not isinstance(tag_name, str) or not tag_name.strip():
            continue
        try:
            normalized_tags.append(normalize_tag(tag_name))
        except ValueError:
            continue

    if not normalized_tags:
        raise ValueError("GitHub tags payload did not contain any usable debian-package tags")

    return max(normalized_tags, key=parse_version_key)


def main() -> None:
    print(fetch_latest_release_tag())


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)
