import subprocess
import re
import os

def run_scan():
    cmd = ["git", "ls-files"]
    files = subprocess.check_output(cmd, text=True).splitlines()

    cred_pattern = re.compile(
        r"(password\s*[:=]\s*['\"]?([^'\"\s]+)['\"]?|postgres:([^@\s]+)@|postgresql\+?[^:]*://([^:]+):([^@\s]+)@)",
        re.IGNORECASE,
    )

    print("=== TRACKED FILES CREDENTIAL SCAN ===")
    matches_found = 0
    for f in files:
        if any(f.endswith(ext) for ext in [".pdf", ".docx", ".png", ".jpg", ".ico", ".woff", ".woff2", ".svg"]):
            continue
        try:
            with open(f, "r", encoding="utf-8", errors="ignore") as fp:
                for lno, line in enumerate(fp, 1):
                    if cred_pattern.search(line):
                        # Mask password/credentials
                        masked = re.sub(
                            r"(://[^:]+:)([^@]+)(@)",
                            r"\1<password>\3",
                            line.strip()
                        )
                        masked = re.sub(
                            r"(password\s*[:=]\s*['\"]?)([^'\"\s,]+)(['\"]?)",
                            r"\1<password>\3",
                            masked,
                            flags=re.IGNORECASE
                        )
                        print(f"{f}:{lno}: {masked}")
                        matches_found += 1
        except Exception:
            pass

    print(f"\nScan completed. Total matched lines: {matches_found}")

if __name__ == "__main__":
    run_scan()

