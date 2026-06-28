#!/usr/bin/env python3
"""Validate the udev rules syntax for the camera name pinning (no hardware).

`udevadm verify` only exists on systemd >= 250 (the OpenArm VM ships 249), so this
parses 99-openarm-cameras.rules the way udev does and checks:
  * every token is a well-formed  KEY[{attr}] OP "value"
  * match keys use comparison ops (==/!=); assignment keys use =/+=/:=/-=
    (a SYMLINK=="..." typo would silently never create the link)
  * all three expected camera symlinks are declared, each keyed on a USB port,
    on subsystem video4linux, selecting the index==0 capture node.

    python3 sim_verify_udev.py
"""
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
RULES = os.path.join(HERE, "99-openarm-cameras.rules")

TOKEN = re.compile(r'^([A-Z_]+)(\{[^}]+\})?\s*(==|!=|\+=|-=|:=|=)\s*"([^"]*)"$')
MATCH_KEYS = {"SUBSYSTEM", "KERNELS", "KERNEL", "ATTR", "ATTRS", "ENV", "SUBSYSTEMS", "DRIVERS"}
ASSIGN_KEYS = {"SYMLINK", "NAME", "OWNER", "GROUP", "MODE", "RUN", "TAG"}
MATCH_OPS = {"==", "!="}
ASSIGN_OPS = {"=", "+=", ":=", "-="}

EXPECTED_LINKS = {"cam_torso", "cam_grip_left", "cam_grip_right"}


def split_tokens(line):
    """Split a rule on commas that are not inside quotes."""
    return [t.strip() for t in re.split(r',(?=(?:[^"]*"[^"]*")*[^"]*$)', line) if t.strip()]


def main():
    assert os.path.exists(RULES), f"rules file missing: {RULES}"
    symlinks = []
    n_rules = 0
    with open(RULES) as f:
        for lineno, raw in enumerate(f, 1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            n_rules += 1
            keys = {}
            for tok in split_tokens(line):
                m = TOKEN.match(tok)
                assert m, f"line {lineno}: malformed token {tok!r}"
                key, attr, op, val = m.groups()
                if key in MATCH_KEYS:
                    assert op in MATCH_OPS, f"line {lineno}: {key} needs a match op, got {op!r}"
                elif key in ASSIGN_KEYS:
                    assert op in ASSIGN_OPS, f"line {lineno}: {key} needs an assign op, got {op!r}"
                else:
                    raise AssertionError(f"line {lineno}: unknown key {key!r}")
                keys[key + (attr or "")] = val
            # every camera rule must key on the USB port, subsystem + capture node
            assert keys.get("SUBSYSTEM") == "video4linux", f"line {lineno}: wrong subsystem"
            assert keys.get("ATTR{index}") == "0", f"line {lineno}: not the index==0 node"
            assert "KERNELS" in keys, f"line {lineno}: no USB port (KERNELS) match"
            assert "SYMLINK" in keys, f"line {lineno}: rule creates no symlink"
            symlinks.append(keys["SYMLINK"])
            print(f"  line {lineno}: SYMLINK={keys['SYMLINK']:14s} KERNELS={keys['KERNELS']}")

    print(f"parsed {n_rules} rules, {len(symlinks)} symlinks: {symlinks}")
    assert set(symlinks) == EXPECTED_LINKS, f"symlinks {set(symlinks)} != {EXPECTED_LINKS}"
    assert len(symlinks) == len(set(symlinks)), "duplicate symlink name"
    print("PASS: udev rules are well-formed and declare all three camera symlinks")


if __name__ == "__main__":
    main()
