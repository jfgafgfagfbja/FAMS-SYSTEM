"""Gom ket qua `flutter test --machine` thanh {"<file>_test.dart": "passed"|"failed"}.

Dung:  flutter test --machine > flutter_machine.jsonl
       python tool/flutter_results.py flutter_machine.jsonl flutter_results.json
"""
import json
import os
import sys


def main(src: str, dst: str) -> None:
    suites: dict[int, str] = {}
    test_suite: dict[int, int] = {}
    result: dict[str, str] = {}
    with open(src, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            kind = event.get("type")
            if kind == "suite":
                suite = event["suite"]
                suites[suite["id"]] = os.path.basename(suite.get("path") or "")
            elif kind == "testStart":
                test = event["test"]
                test_suite[test["id"]] = test["suiteID"]
            elif kind == "testDone" and not event.get("hidden"):
                name = suites.get(test_suite.get(event["testID"], -1))
                if not name:
                    continue
                ok = event.get("result") == "success" and not event.get("skipped")
                if not ok:
                    result[name] = "failed"
                else:
                    result.setdefault(name, "passed")
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    failed = [k for k, v in result.items() if v != "passed"]
    print(f"{len(result)} file test, {len(failed)} that bai: {failed}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
