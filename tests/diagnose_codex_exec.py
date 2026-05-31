"""Diagnostic script for codex exec availability.

Checks environment, codex version, and runs a test execution.
Does not modify any files.
"""
import os
import subprocess
import json


def main():
    print("=== Codex Exec Diagnostic ===\n")

    # 1. which codex
    try:
        which = subprocess.run(["which", "codex"], capture_output=True, text=True)
        print("1. which codex:", which.stdout.strip() or "not found")
    except Exception as e:
        print("1. which codex: error", e)

    # 2. codex --version
    try:
        ver = subprocess.run(["codex", "--version"], capture_output=True, text=True, timeout=10)
        print("2. codex --version:", ver.stdout.strip() or ver.stderr.strip() or "unknown")
    except Exception as e:
        print("2. codex --version: error", e)

    # 3. Environment variables
    print("3. Environment variables:")
    for key in ["CODEX_PROFILE", "CODEX_WIKIGUARD_PROFILE", "CODEX_WIKIGUARD_CHILD"]:
        val = os.environ.get(key)
        print(f"   {key} = {val if val else '(not set)'}")

    # 4. Test codex exec
    print("\n4. Testing codex exec...")
    try:
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "hooks"))
        from codex_client import call_codex_default

        result = call_codex_default("只输出 JSON：{\"ok\":true}", timeout=120)
        print(f"   ok: {result.get('ok')}")
        print(f"   profile: {result.get('profile')}")
        print(f"   command_mode: {result.get('command_mode')}")

        if not result["ok"]:
            err = result.get("error", "")
            print(f"   error: {err[:200]}")

            if "not supported when using Codex with a ChatGPT account" in err:
                print("\n   DIAGNOSIS: ChatGPT account mode does not support this custom model. Use an API-key/local-compatible Codex profile or launch Codex with a compatible profile exposed via CODEX_PROFILE.")
            elif "legacy profile config is no longer supported" in err:
                print("\n   DIAGNOSIS: Legacy profile config detected. Use <profile>.config.toml and pass profile through CODEX_PROFILE or CODEX_WIKIGUARD_PROFILE.")
    except Exception as e:
        print(f"   Error during test: {e}")


if __name__ == "__main__":
    main()
