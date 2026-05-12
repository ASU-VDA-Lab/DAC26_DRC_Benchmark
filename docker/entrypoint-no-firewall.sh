#!/bin/bash
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
# entrypoint (no firewall): ld.so.preload sanitize + IPv6 fail-closed + capsh
# irreversibly drop=all + re-add 6 required caps, then exec the real CMD.
#
# Used by Dockerfile.repair. Repair runs KLayout DRC engine but does NOT
# program an iptables egress blocklist (the paper documents internet
# restriction only for the detection task). The Phase-2 capability drop is
# still applied here because it is independent of network filtering and
# closes off kernel/host-level attack surface from inside the container.
#
# Image-side dependencies:
#   - libcap (capsh)               (drop caps)
#   - tini                         (PID 1 init reaping zombies)
#   - ip / iproute                 (IPv6 interface detection)
#
# This script is invoked as PID 2 by tini:
#   ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/entrypoint-no-firewall.sh"]
#   CMD ["sleep", "infinity"]
#
# placeholder bug fix:
#   In `-- -c 'exec "$@"' bash "$@"`, the `bash` is the $0 placeholder for
#   the capsh-shell; the user command is fully preserved as $1..$N. If we
#   wrote `-- "$@"`, the first token of the user command would be consumed
#   as $0.

set -euo pipefail

# ---- ld.so.preload sanitize (defense-in-depth) ---------------------------
# Prior to any subsequent exec, strip a possible mutable-rootfs `ld.so.preload`
# hijack (even if the image has no LD_PRELOAD-based rootkit installed, still
# fail-closed strip).
# After rm, ldconfig regenerates the cache to avoid stale preload entries.
if [[ -f /etc/ld.so.preload ]]; then
    rm -f /etc/ld.so.preload 2>/dev/null || true
fi
# Strip drop-in conf files that could re-inject preload paths.
if [[ -d /etc/ld.so.conf.d ]]; then
    find /etc/ld.so.conf.d -type f -name '*.conf' -delete 2>/dev/null || true
fi
ldconfig 2>/dev/null || true

# ---- IPv6 fail-closed ----------------------------------------------------
# Even though this container has no iptables blocklist, a global IPv6
# interface in a hardened deployment is unexpected; fail closed to keep the
# repair environment's network surface in line with detection's assumptions.
if ip -6 addr show 2>/dev/null | grep -q 'inet6 .* scope global'; then
    echo "[entrypoint] FATAL: IPv6 interface present in repair container; expected only loopback." >&2
    exit 1
fi

# ---- Irreversible drop ALL caps + add back essentials ---------------------
# drop=all + re-add only required caps; future PRs adding caps will not
#      silently fail-open.
# In `-- -c 'exec "$@"' bash "$@"`, the `bash` is the placeholder; the
#       shell treats it as $0 so the trailing "$@" is fully preserved as
#       $1..$N.
echo "[entrypoint] Dropping all capabilities except CAP_CHOWN/CAP_DAC_OVERRIDE/CAP_FOWNER/CAP_SETUID/CAP_SETGID/CAP_KILL (irreversible)..."
# capsh `--drop=all` clears the bounding set first,
# which then makes the subsequent `--caps='...+eip'` reject every cap (cannot
# raise a cap not in bounding). Likewise `+i` (inheritable) needs ambient or
# CAP_SETPCAP and would fail under no-new-privileges. Replace with explicit
# `--drop=<everything-except-the-6>` and `+ep` (no inheritable). Final
# bounding/permitted/effective set is 0xeb (chown/dac_override/fowner/kill/
# setgid/setuid). This matches the original intent and is verifiable via
# `grep Cap /proc/self/status` after entrypoint.
exec capsh \
    --drop=cap_fsetid,cap_setpcap,cap_net_bind_service,cap_net_admin,cap_net_raw,cap_sys_chroot,cap_mknod,cap_audit_write,cap_setfcap,cap_dac_read_search,cap_linux_immutable,cap_net_broadcast,cap_ipc_lock,cap_ipc_owner,cap_sys_module,cap_sys_rawio,cap_sys_ptrace,cap_sys_pacct,cap_sys_admin,cap_sys_boot,cap_sys_nice,cap_sys_resource,cap_sys_time,cap_sys_tty_config,cap_lease,cap_audit_control,cap_mac_override,cap_mac_admin,cap_syslog,cap_wake_alarm,cap_block_suspend,cap_audit_read,cap_perfmon,cap_bpf,cap_checkpoint_restore \
    --caps='cap_chown,cap_dac_override,cap_fowner,cap_setuid,cap_setgid,cap_kill+ep' \
    --inh='' \
    --user=root \
    -- -c 'exec "$@"' bash "$@"
