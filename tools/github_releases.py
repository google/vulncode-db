#!/usr/bin/env python3
# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

### WARNING: THIS IS FULL OF XSS ISSUES!!!!
### Release texts are as trusted as the source code itself, but sandboxing
### doesn't hurt

import datetime
import sys
import json
import io

import requests

try:
    import pycmarkgfm
except ImportError:
    print("pip install pycmarkgfm")
    exit()


class Release:
    def __init__(self, **kwargs):
        self._original = kwargs
        self.created_at = datetime.datetime.strptime(
            kwargs["created_at"], "%Y-%m-%dT%H:%M:%SZ"
        )
        self.published_at = datetime.datetime.strptime(
            kwargs["published_at"], "%Y-%m-%dT%H:%M:%SZ"
        )

    def __getattr__(self, name):
        return self._original[name]

    def __str__(self):
        return f"#{self.id} [{self.tag_name}] {self.name}"

    def to_html(self):
        if pycmarkgfm:
            # print("Using pycmarkgfm", file=sys.stderr)
            description = pycmarkgfm.gfm_to_html(self.body)
        else:
            # print("Using plain", file=sys.stderr)
            description = f'<pre id="desc-{self.id}"></pre><script>document.getElementById("desc-{self.id}").textContent = {json.dumps(self.body)};</script>'
        return f"""<div class="release" id="release-{self.id}">
    <h2>{self.name}</h2>
    <p>{self.published_at}</p>
    <div class="description">
    {description}
    </div>
</div>"""


def fetch(path, **kwargs):
    resp = requests.get(
        "https://api.github.com/repos/google/vulncode-db/" + path.lstrip("/"),
        params=kwargs,
        headers={"Accept": "application/vnd.github.v3+json"},
    )
    resp.raise_for_status()
    return resp.json()


def get_latest_n_releases(n=100):
    return [Release(**r) for r in fetch("/releases", per_page=n)]


def get_latest_release():
    return get_release("latest")


def get_release(release_id):
    return Release(**fetch(f"/releases/{release_id}"))


def to_html(releases):
    buf = io.StringIO()
    buf.write("<h1>Releases</h1>")
    buf.write("<ul>")
    for rel in releases:
        buf.write(f'<li><a href="#release-{rel.id}">{rel.name}</a></li>')
    buf.write("</ul>")
    for rel in releases:
        buf.write(rel.to_html())
    return buf.getvalue()


def main():
    releases = get_latest_n_releases()
    print(to_html(releases))


if __name__ == "__main__":
    main()
