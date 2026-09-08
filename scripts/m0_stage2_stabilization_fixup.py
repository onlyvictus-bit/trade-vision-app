from __future__ import annotations

from pathlib import Path

PATH = Path("apps/api/tests/test_api.py")


def replace_once(old: str, new: str) -> None:
    text = PATH.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"expected exactly one regression anchor, found {count}: {old!r}")
    PATH.write_text(text.replace(old, new, 1), encoding="utf-8")


def main() -> None:
    replace_once(
        '    assert first_row["source_mode"] == "real"\n'
        '    assert second_row["source_mode"] == "real"\n'
        '    assert first_row["runtime_status"] == "computed"',
        '    assert first_row["source_mode"] == "synthetic_fallback"\n'
        '    assert second_row["source_mode"] == "synthetic_fallback"\n'
        '    assert first_row["explanation_only"] is True\n'
        '    assert second_row["explanation_only"] is True\n'
        '    assert first_row["usable_for_probability"] is False\n'
        '    assert second_row["usable_for_probability"] is False\n'
        '    assert first_row["runtime_status"] == "computed"',
    )
    print("M0 synthetic provenance assertions aligned with fail-closed contract.")


if __name__ == "__main__":
    main()
