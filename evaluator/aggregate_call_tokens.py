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
# evaluator/aggregate_call_tokens.py
# Host-side trusted aggregator: sums per-call tokens.json files under one
# case dir into a canonical tokens JSON. Runs post-kill/disconnect/reinject.
# Stdlib-only. --output is atomic (.tmp + os.rename); the file is the
# canonical channel (the shell helper reads it; aggregator stdout is not
# eval'd). Fail-soft: zero valid call_ids -> source=marker_fallback. Symlink
# escapes (in-tree or out-of-tree), bad call_id names, malformed JSON, and
# fan-out floods are all skipped with WARN.
# Exit codes: 0 success / 1 output I/O error / 2 argparse / 3 --strict + WARN.

import argparse
import json
import os
import re
import stat
import sys


# Required four-key token schema (matches the TOKENS_JSON= marker).
TOKEN_KEYS = (
    "input_tokens",
    "output_tokens",
    "cache_read_tokens",
    "cache_write_tokens",
)

# call_id regex; period excluded so `.` / `..` are impossible.
CALL_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

# Int overflow ceiling = 2**31 - 1 (matches downstream CSV int range).
INT_CEIL = 2**31 - 1


def _zero_tokens():
    return {k: 0 for k in TOKEN_KEYS}


def _coerce_token_value(raw, key, call_id, warnings):
    """Sanitize one token-field; returns int in [0, INT_CEIL]; appends WARN(s) on issues."""
    if raw is None:
        return 0

    val = None
    if isinstance(raw, bool):
        # bool is a subclass of int; treat as non-numeric -> WARN + 0.
        warnings.append(
            f"WARN: call_id={call_id} field={key} bool not allowed; using 0"
        )
        return 0
    if isinstance(raw, int):
        val = raw
    elif isinstance(raw, float):
        try:
            val = int(round(raw))
        except (ValueError, OverflowError):
            warnings.append(
                f"WARN: call_id={call_id} field={key} float coerce failed; using 0"
            )
            return 0
    elif isinstance(raw, str):
        try:
            val = int(raw)
        except ValueError:
            warnings.append(
                f"WARN: call_id={call_id} field={key} str->int failed for {raw!r}; using 0"
            )
            return 0
    else:
        warnings.append(
            f"WARN: call_id={call_id} field={key} type={type(raw).__name__} not numeric; using 0"
        )
        return 0

    if val < 0:
        warnings.append(
            f"WARN: call_id={call_id} field={key} negative value {val}; clamped to 0"
        )
        return 0
    if val > INT_CEIL:
        warnings.append(
            f"WARN: call_id={call_id} field={key} value {val} exceeds {INT_CEIL}; clamped"
        )
        return INT_CEIL
    return val


def _parse_call_tokens(call_id, tokens_path, calls_dir_real, warnings):
    """Load + sanitize one per-call <ID>.json. Returns (tokens_dict,
    by_model_dict) or None on skip.

    ``tokens_path`` is the full path to ``<calls_dir>/<call_id>.json``
    (flat layout — no per-call subdirectory). ``calls_dir_real`` is
    ``realpath(calls_dir)`` for the symlink-escape defense.
    """
    # Symlink-escape defense: realpath must stay under calls_dir_real.
    try:
        tokens_real = os.path.realpath(tokens_path)
    except OSError as e:
        warnings.append(
            f"WARN: call_id={call_id} realpath failed: {e!r}; skipped"
        )
        return None
    # Sep-aware prefix to avoid calls_dir_real being a substring of a sibling.
    calls_dir_with_sep = calls_dir_real
    if not calls_dir_with_sep.endswith(os.sep):
        calls_dir_with_sep = calls_dir_with_sep + os.sep
    if not tokens_real.startswith(calls_dir_with_sep):
        warnings.append(
            f"WARN: call_id={call_id} per-call json realpath escapes calls_dir; skipped"
        )
        return None

    if not os.path.isfile(tokens_real):
        warnings.append(
            f"WARN: call_id={call_id} per-call json missing; skipped"
        )
        return None

    try:
        with open(tokens_real, "r") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as e:
        warnings.append(
            f"WARN: call_id={call_id} json load failed: {e!r}; skipped"
        )
        return None

    if not isinstance(data, dict):
        warnings.append(
            f"WARN: call_id={call_id} top-level json not an object; skipped"
        )
        return None

    # schema_version: missing -> assume 1 with WARN. Unknown -> WARN +
    # parse as v1 (legacy fail-open; per round 6 architect decision).
    sv = data.get("schema_version", None)
    if sv is None:
        warnings.append(
            f"WARN: call_id={call_id} schema_version missing; assuming 1"
        )
    else:
        try:
            sv_str = str(sv)
        except Exception:
            sv_str = ""
        if sv_str != "1":
            warnings.append(
                f"WARN: call_id={call_id} unknown schema_version={sv_str!r}; "
                f"parsing as v1 (legacy fail-open)"
            )

    # Top-level four token fields.
    out = {}
    for k in TOKEN_KEYS:
        out[k] = _coerce_token_value(data.get(k, None), k, call_id, warnings)

    # by_model: dict keyed by model id, each value a four-key sub-dict.
    # Missing / empty / wrong-type -> WARN; skip the file.
    by_model_raw = data.get("by_model", None)
    by_model_clean = {}
    if not isinstance(by_model_raw, dict) or not by_model_raw:
        warnings.append(
            f"WARN: call_id={call_id} by_model missing or empty; skipped"
        )
        return None
    for model_name, mu in by_model_raw.items():
        if not isinstance(mu, dict):
            warnings.append(
                f"WARN: call_id={call_id} by_model[{model_name!r}] not dict; skipped entry"
            )
            continue
        entry = {}
        for k in TOKEN_KEYS:
            entry[k] = _coerce_token_value(
                mu.get(k, None), k, f"{call_id}/{model_name}", warnings)
        by_model_clean[str(model_name)] = entry

    if not by_model_clean:
        warnings.append(
            f"WARN: call_id={call_id} by_model has no valid entries; skipped"
        )
        return None

    # Advisory cross-check: top-level four-key totals should equal
    # sum over by_model. Top-level wins on mismatch.
    sums = {k: 0 for k in TOKEN_KEYS}
    for entry in by_model_clean.values():
        for k in TOKEN_KEYS:
            sums[k] += entry[k]
    for k in TOKEN_KEYS:
        if sums[k] != out[k]:
            warnings.append(
                f"WARN: call_id={call_id} top-level {k}={out[k]} != "
                f"sum(by_model.{k})={sums[k]}; top-level wins"
            )

    # call_id in-file matches filename stem (filename canonical).
    in_file_id = data.get("call_id")
    if isinstance(in_file_id, str) and in_file_id != call_id:
        warnings.append(
            f"WARN: call_id={call_id} in-file call_id={in_file_id!r} differs; "
            f"filename canonical"
        )

    return out, by_model_clean


def _load_fallback_tokens(fallback_str, warnings):
    """Parse --fallback-tokens-json into a sanitized dict + source label."""
    if not fallback_str:
        return _zero_tokens(), "zero_default"
    try:
        data = json.loads(fallback_str)
    except (json.JSONDecodeError, TypeError):
        warnings.append("WARN: --fallback-tokens-json malformed; using zero_default")
        return _zero_tokens(), "zero_default"
    if not isinstance(data, dict):
        warnings.append("WARN: --fallback-tokens-json not an object; using zero_default")
        return _zero_tokens(), "zero_default"
    out = {}
    for k in TOKEN_KEYS:
        out[k] = _coerce_token_value(data.get(k, None), k, "<marker>", warnings)
    return out, "marker_fallback"


def _write_output_atomic(out_path, payload):
    """Atomic write via .tmp + os.rename. Raises OSError."""
    out_dir = os.path.dirname(out_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    tmp_path = out_path + ".tmp"
    data = json.dumps(payload, indent=2)
    with open(tmp_path, "w") as f:
        f.write(data)
        f.flush()
        try:
            os.fsync(f.fileno())
        except OSError:
            # fsync best-effort; rename is the durability point.
            pass
    os.rename(tmp_path, out_path)


def _append_report(report_path, warnings):
    if not report_path or not warnings:
        return
    try:
        report_dir = os.path.dirname(report_path)
        if report_dir:
            os.makedirs(report_dir, exist_ok=True)
        with open(report_path, "a") as f:
            for w in warnings:
                f.write(w + "\n")
    except OSError:
        # Logging is best-effort; never fail the aggregator on report error.
        pass


def main():
    parser = argparse.ArgumentParser(
        description="Aggregate per-call <ID>.json files into a single "
                    "canonical tokens JSON (host-side, trusted)."
    )
    parser.add_argument("--calls-dir", required=True,
                        help="Absolute path to ${score_dir}/calls (flat, "
                             "file-per-call layout shared across cases).")
    parser.add_argument("--case-name", required=True,
                        help="Case name prefix; the aggregator only "
                             "matches files named ${case_name}_*.json.")
    parser.add_argument("--output", required=True,
                        help="Absolute path to write tokens_combined.json "
                             "(atomic).")
    parser.add_argument("--fallback-tokens-json", default="",
                        help="Marker tokens JSON used when no valid per-call "
                             "files are found.")
    parser.add_argument("--report", default="",
                        help="Optional append-mode log path for WARN lines.")
    parser.add_argument("--max-files", type=int, default=1024,
                        help="Maximum number of per-call files processed "
                             "(DOS cap; default 1024).")
    parser.add_argument("--require-files", action="store_true",
                        help="Mandatory recording: exit non-zero when zero "
                             "valid per-call files are found. Host sets "
                             "this when STATUS=success; omits it when "
                             "STATUS=fail (marker_fallback path).")
    parser.add_argument("--strict", action="store_true",
                        help="Exit 3 if any WARN was emitted (unit-test use).")
    args = parser.parse_args()

    if not args.calls_dir or not args.output or not args.case_name:
        print("ERROR: --calls-dir, --case-name, and --output are required",
              file=sys.stderr)
        sys.exit(2)

    warnings = []

    fallback_tokens, fallback_source = _load_fallback_tokens(
        args.fallback_tokens_json, warnings
    )

    calls_dir = args.calls_dir
    case_name = args.case_name
    calls_dir_exists = os.path.isdir(calls_dir)
    n_discovered = 0
    n_valid = 0
    n_skipped = 0
    valid_call_ids = []
    summed = _zero_tokens()
    by_model_total = {}  # {model_name: {four-keys-int}}

    if calls_dir_exists:
        try:
            calls_dir_real = os.path.realpath(calls_dir)
        except OSError as e:
            warnings.append(f"WARN: realpath({calls_dir!r}) failed: {e!r}")
            calls_dir_real = calls_dir

        try:
            entries = sorted(os.listdir(calls_dir))
        except OSError as e:
            warnings.append(
                f"WARN: listdir({calls_dir!r}) failed: {e!r}; treating as empty"
            )
            entries = []

        # Filter by case_name prefix + .json suffix; flat one-level (no
        # recursion). Skip symlinks. Cap before per-entry lstat to bound DOS.
        prefix = f"{case_name}_"
        suffix = ".json"
        matched = [n for n in entries
                   if n.startswith(prefix) and n.endswith(suffix)]
        if args.max_files is not None and len(matched) > args.max_files:
            extra = len(matched) - args.max_files
            warnings.append(
                f"WARN: file cap ({args.max_files}) exceeded; "
                f"{extra} additional files skipped"
            )
            matched = matched[: args.max_files]

        candidate_files = []
        for name in matched:
            full = os.path.join(calls_dir, name)
            try:
                st = os.lstat(full)
            except OSError:
                continue
            if stat.S_ISLNK(st.st_mode):
                warnings.append(
                    f"WARN: per-call file={name!r} is a symlink; skipped"
                )
                continue
            if not stat.S_ISREG(st.st_mode):
                continue
            candidate_files.append(name)

        n_discovered = len(candidate_files)

        for fname in candidate_files:
            call_id = fname[:-len(suffix)]  # strip .json
            if not CALL_ID_RE.fullmatch(call_id):
                warnings.append(
                    f"WARN: call_id={call_id!r} fails regex; skipped"
                )
                n_skipped += 1
                continue
            tokens_path = os.path.join(calls_dir, fname)
            parsed = _parse_call_tokens(
                call_id, tokens_path, calls_dir_real, warnings
            )
            if parsed is None:
                n_skipped += 1
                continue
            tokens_dict, by_model_dict = parsed
            # Clamp after add to honour INT_CEIL.
            for k in TOKEN_KEYS:
                s = summed[k] + tokens_dict[k]
                if s > INT_CEIL:
                    warnings.append(
                        f"WARN: aggregate field={k} sum exceeded {INT_CEIL}; clamped"
                    )
                    s = INT_CEIL
                summed[k] = s
            # Aggregate by_model across calls.
            for model_name, entry in by_model_dict.items():
                bucket = by_model_total.setdefault(
                    model_name, {k: 0 for k in TOKEN_KEYS})
                for k in TOKEN_KEYS:
                    s = bucket[k] + entry[k]
                    if s > INT_CEIL:
                        warnings.append(
                            f"WARN: aggregate by_model[{model_name!r}].{k} "
                            f"exceeded {INT_CEIL}; clamped"
                        )
                        s = INT_CEIL
                    bucket[k] = s
            valid_call_ids.append(call_id)
            n_valid += 1

    if n_valid == 0:
        # Fail-soft: marker_fallback (or zero_default if marker malformed).
        source = fallback_source
        tokens_final = fallback_tokens
    else:
        source = "per_call_files"
        tokens_final = summed

    # Cross-check: aggregated top-level == sum(aggregated by_model).
    if n_valid > 0:
        bm_sums = {k: 0 for k in TOKEN_KEYS}
        for entry in by_model_total.values():
            for k in TOKEN_KEYS:
                bm_sums[k] += entry[k]
                if bm_sums[k] > INT_CEIL:
                    bm_sums[k] = INT_CEIL
        for k in TOKEN_KEYS:
            if bm_sums[k] != tokens_final[k]:
                warnings.append(
                    f"WARN: aggregate top-level {k}={tokens_final[k]} != "
                    f"sum(aggregated by_model.{k})={bm_sums[k]}; top-level wins"
                )

    payload = {
        # OUTPUT schema version of tokens_combined.json. Output schema
        # stays "1" until the combined-output payload itself changes shape.
        "schema_version": "1",
        "source": source,
        "n_call_ids_discovered": n_discovered,
        "n_call_ids_valid": n_valid,
        "n_call_ids_skipped": n_skipped,
        "call_ids": valid_call_ids,
        "tokens": tokens_final,
        "by_model": by_model_total,
        "warnings": list(warnings),
    }
    try:
        _write_output_atomic(args.output, payload)
    except OSError as e:
        print(f"ERROR: cannot write {args.output}: {e!r}", file=sys.stderr)
        # Best-effort report log (so operator sees what we tried).
        _append_report(args.report, warnings + [
            f"WARN: output write failed: {e!r}",
        ])
        sys.exit(1)

    _append_report(args.report, warnings)

    # Debug-only stdout (shell does NOT consume; --output FILE is canonical).
    try:
        sys.stdout.write(json.dumps(payload) + "\n")
    except OSError:
        pass

    # Mandatory recording fail-closed path: when --require-files is set
    # and zero valid files were found, exit non-zero. The host helper
    # (lib_helpers.sh::aggregate_call_tokens_for_case) intercepts this
    # signal and writes a fail-closed null score JSON via
    # write_invalid_score.py --invalid-reason mandatory_calls_recording_missing.
    if args.require_files and n_valid == 0:
        print(
            f"ERROR: mandatory per-call recording required but no valid "
            f"{case_name}_*.json files found under {calls_dir}",
            file=sys.stderr,
        )
        sys.exit(4)

    if args.strict and warnings:
        sys.exit(3)
    sys.exit(0)


if __name__ == "__main__":
    main()
