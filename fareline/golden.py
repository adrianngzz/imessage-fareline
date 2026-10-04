"""Print the golden transcript against a throwaway ledger."""

from pathlib import Path
from tempfile import TemporaryDirectory

from fareline.handle import handle
from fareline.ledger import Ledger

LINES = [
    ("Riley", "I'm in"),
    ("Alex", "I'm in"),
    ("Sam", "I'm in"),
    ("Jordan", "I'm out"),
    ("Riley", "I paid $48, Alex and Sam rode."),
    ("Alex", "I just paid Riley $16."),
    ("Alex", "What do I owe?"),
]


def main() -> None:
    with TemporaryDirectory() as tmp:
        ledger = Ledger(Path(tmp) / "ledger.json")
        for speaker, text in LINES:
            result = handle(text, speaker, ledger)
            print(f"\n{speaker}: {text}")
            print(result["reply"])


if __name__ == "__main__":
    main()
