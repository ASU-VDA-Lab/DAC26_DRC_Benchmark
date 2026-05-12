#!/bin/bash
# /usr/local/bin/secured-exec.sh
#
# wrapper for `docker exec`:
#   - env -i sanitize: only forward env vars on the allowlist, to avoid host
#     PID 1 leak / agent rc-file injection.
#   - capsh --drop=all + re-add 6 required caps: prevent docker exec from
#     inheriting NET_ADMIN etc. via the container bounding set, which would
#     bypass the entrypoint's cap drop.
#
# placeholder: in `-- -c 'exec "$@"' bash "$@"`, the `bash` is the $0
# placeholder for the capsh-shell; the user command is fully preserved as
# $1..$N. Writing `-- "$@"` would consume the first token of the user
# command as $0.
#
# the wrapper centralizes env -i sanitize (single source) so
#   different docker exec call sites do not each re-implement and regress.
# add CLAUDE_CODE_MAX_OUTPUT_TOKENS to the allowlist; unify
#   codex naming to CODEX_EFFORT (consistent with run_pipeline_codex.sh) and
#   remove the old alias CODEX_REASONING_EFFORT.
# PYTHONDONTWRITEBYTECODE must appear in BOTH the default
#   `: "${VAR:=}"` block AND the env -i forwarding block, to avoid Python
#   in the container writing .pyc and polluting the mount point.

set -u

# ---- LD_PRELOAD / LD_LIBRARY_PATH belt-and-suspenders ---------------------
# entrypoint-firewall.sh already strips /etc/ld.so.preload; here we also
# unset inherited env to prevent docker exec from injecting new values.
unset LD_PRELOAD LD_LIBRARY_PATH

# ---- env allowlist: shared set across score / agent phase ----------------
# Default if missing; agent phase does not bring SEALED_OUTPUT_SHA256 /
# HARDENED_EVALUATION, score phase does not bring CLAUDE_EFFORT /
# CODEX_EFFORT / ANTHROPIC_API_KEY etc.
: "${HOME:=/root}"
: "${LANG:=C}"
: "${PATH:=/usr/local/bin:/usr/bin:/bin}"
: "${EVALUATOR_DIR:=}"
: "${EVALUATOR_HELPERS_DIR:=}"
: "${HARDENED_EVALUATION:=}"
: "${SEALED_OUTPUT_SHA256:=}"
: "${TRUSTED_PYTHON:=}"
: "${CLAUDE_EFFORT:=}"
: "${CLAUDE_CODE_MAX_OUTPUT_TOKENS:=}"
: "${CODEX_EFFORT:=}"
: "${PYTHONDONTWRITEBYTECODE:=}"
: "${ANTHROPIC_API_KEY:=}"
: "${OPENAI_API_KEY:=}"

# ---- After env -i, re-expand the allowlist; any env var not on the list is dropped ----
exec env -i \
    HOME="${HOME}" \
    LANG="${LANG}" \
    PATH="${PATH}" \
    EVALUATOR_DIR="${EVALUATOR_DIR}" \
    EVALUATOR_HELPERS_DIR="${EVALUATOR_HELPERS_DIR}" \
    HARDENED_EVALUATION="${HARDENED_EVALUATION}" \
    SEALED_OUTPUT_SHA256="${SEALED_OUTPUT_SHA256}" \
    TRUSTED_PYTHON="${TRUSTED_PYTHON}" \
    CLAUDE_EFFORT="${CLAUDE_EFFORT}" \
    CLAUDE_CODE_MAX_OUTPUT_TOKENS="${CLAUDE_CODE_MAX_OUTPUT_TOKENS}" \
    CODEX_EFFORT="${CODEX_EFFORT}" \
    PYTHONDONTWRITEBYTECODE="${PYTHONDONTWRITEBYTECODE}" \
    ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY}" \
    OPENAI_API_KEY="${OPENAI_API_KEY}" \
    capsh \
        --drop=cap_fsetid,cap_setpcap,cap_net_bind_service,cap_net_admin,cap_net_raw,cap_sys_chroot,cap_mknod,cap_audit_write,cap_setfcap,cap_dac_read_search,cap_linux_immutable,cap_net_broadcast,cap_ipc_lock,cap_ipc_owner,cap_sys_module,cap_sys_rawio,cap_sys_ptrace,cap_sys_pacct,cap_sys_admin,cap_sys_boot,cap_sys_nice,cap_sys_resource,cap_sys_time,cap_sys_tty_config,cap_lease,cap_audit_control,cap_mac_override,cap_mac_admin,cap_syslog,cap_wake_alarm,cap_block_suspend,cap_audit_read,cap_perfmon,cap_bpf,cap_checkpoint_restore \
        --caps='cap_chown,cap_dac_override,cap_fowner,cap_setuid,cap_setgid,cap_kill+ep' \
        --inh='' \
        --user=root \
        -- -c 'exec "$@"' bash "$@"
