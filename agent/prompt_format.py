#!/usr/bin/env python3
#BSD 3-Clause License
#
#Copyright (c) 2026, ASU-VDA-Lab
#
#Redistribution and use in source and binary forms, with or without
#modification, are permitted provided that the following conditions are met:
#
#1. Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
#
#2. Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
#3. Neither the name of the copyright holder nor the names of its
#   contributors may be used to endorse or promote products derived from
#   this software without specific prior written permission.
#
#THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
#AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
#IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
#DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
#FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
#DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
#SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
#CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
#OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
#OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#################################################################################
# JSON-template prompt renderer.
#
# Reads a structured prompt template (one of agent/prompts/*.json) plus a
# case info.json, renders ``${var}`` placeholders via
# ``string.Template.safe_substitute()``, and writes the assembled prompt
# (system + user) to stdout. Only the placeholders declared in the template's
# ``variables`` list are accepted; literal ``$`` characters in the body must
# be escaped to ``$$`` so they survive substitution unchanged.
#
# Usage:
#     python3 agent/prompt_format.py <info_json> <template_json>

import json
import re
import string
import sys


class _SafeDict(dict):
    # Returns the original ``${name}`` token verbatim when a variable is
    # missing from info.json, instead of raising KeyError. Combined with
    # ``string.Template.safe_substitute()`` this keeps rendering tolerant of
    # optional fields while still validating placeholder names against the
    # template's ``variables`` declaration.
    def __missing__(self, key):
        return "${" + key + "}"


_PLACEHOLDER_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def _validate_keys(template_body, declared_variables):
    # Ensure every ${var} placeholder in the body is declared in the
    # template's ``variables`` list. Catches typos and undeclared keys before
    # substitution silently leaves them in place.
    found = set(_PLACEHOLDER_RE.findall(template_body))
    declared = set(declared_variables or [])
    undeclared = sorted(found - declared)
    if undeclared:
        raise ValueError(
            "Template contains placeholders not declared in 'variables': "
            "{} (declared: {})".format(undeclared, sorted(declared))
        )


def render_prompt(info_path, template_path):
    # Load template + info, validate placeholder declarations, and return the
    # composed ``"<system>\n\n<user>"`` text.
    with open(template_path, "r", encoding="utf-8") as f:
        template = json.load(f)

    required_keys = {
        "task", "schema_version", "system", "user_template",
        "variables", "output_format",
    }
    missing = sorted(required_keys - set(template.keys()))
    if missing:
        raise ValueError(
            "Template '{}' missing keys: {}".format(template_path, missing)
        )

    user_body = template["user_template"]
    declared_vars = template.get("variables", [])
    _validate_keys(user_body, declared_vars)

    with open(info_path, "r", encoding="utf-8") as f:
        info = json.load(f)

    user_rendered = string.Template(user_body).safe_substitute(_SafeDict(info))

    system = template.get("system", "")
    if system:
        return "{}\n\n{}".format(system, user_rendered)
    return user_rendered


def main():
    if len(sys.argv) != 3:
        sys.stderr.write(
            "Usage: {} <info_json> <template_json>\n".format(sys.argv[0]))
        sys.exit(2)

    info_path = sys.argv[1]
    template_path = sys.argv[2]

    rendered = render_prompt(info_path, template_path)
    sys.stdout.write(rendered)
    if not rendered.endswith("\n"):
        sys.stdout.write("\n")


if __name__ == "__main__":
    main()
