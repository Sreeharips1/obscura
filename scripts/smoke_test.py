"""End-to-end check against a RUNNING Obscura.

    python scripts/smoke_test.py                       (http://localhost:8080)
    python scripts/smoke_test.py --base https://your-domain --auth user:pass
    python scripts/smoke_test.py --send                (also calls Gemini)
"""
import argparse
import base64
import json
import sys
import urllib.error
import urllib.request


def call(base, path, payload=None, auth=None):
    headers = {"Content-Type": "application/json"}

    if auth:
        token = base64.b64encode(auth.encode()).decode()
        headers["Authorization"] = f"Basic {token}"

    data = json.dumps(payload).encode() if payload is not None else None

    request = urllib.request.Request(base + path, data=data, headers=headers)

    with urllib.request.urlopen(request, timeout=300) as response:
        return json.loads(response.read())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://localhost:8080")
    parser.add_argument("--auth", default=None, help="user:password")
    parser.add_argument("--send", action="store_true")
    args = parser.parse_args()

    failures = []

    def check(name, ok):
        print(("PASS  " if ok else "FAIL  ") + name)
        if not ok:
            failures.append(name)

    try:
        health = call(args.base, "/api/health", auth=args.auth)
        check("health endpoint", health.get("status") == "ok")

        text = (
            "My name is Aaron Smith. Email aaron.smith@example.com "
            "and phone 9876543210. Write a job application email."
        )

        analysis = call(args.base, "/api/privacy/analyze", {"text": text}, args.auth)
        found = analysis["detections"]
        types = {d["type"] for d in found}

        check("detects an email", "EMAIL" in types)
        check("detects a phone number", "PHONE" in types)

        ids = [d["id"] for d in found if d["recommended_action"] != "BLOCK"]

        prepared = call(
            args.base,
            "/api/privacy/prepare",
            {"text": text, "selected_detection_ids": ids},
            args.auth,
        )

        sanitized = prepared["sanitized_text"]

        check("email is removed from the outgoing text", "aaron.smith@example.com" not in sanitized)
        check("phone is removed from the outgoing text", "9876543210" not in sanitized)
        check("placeholders were inserted", "<OBSCURA_" in sanitized)

        secret = call(
            args.base,
            "/api/privacy/analyze",
            {"text": "my password: hunter2xyz99"},
            args.auth,
        )
        blocked = call(
            args.base,
            "/api/privacy/prepare",
            {"text": "my password: hunter2xyz99", "selected_detection_ids": []},
            args.auth,
        )
        check("secret is detected", any(d["recommended_action"] == "BLOCK" for d in secret["detections"]))
        check("secret blocks the request", blocked.get("blocked") is True)

        if args.send:
            reply = call(
                args.base,
                "/api/chat/send",
                {"session_id": prepared["session_id"]},
                args.auth,
            )
            check("AI reply received", bool(reply.get("response")))
            print("      " + reply["response"][:100].replace("\n", " ") + "...")

    except urllib.error.HTTPError as error:
        print(f"FAIL  HTTP {error.code} from the server")
        sys.exit(1)
    except Exception as error:
        print(f"FAIL  could not run the checks: {error}")
        sys.exit(1)

    print()
    print("All checks passed." if not failures else f"{len(failures)} check(s) failed.")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
