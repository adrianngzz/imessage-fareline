"""Print the golden transcript against a fresh ledger."""

from pathlib import Path
import tempfile

from fareline.handle import handle
from fareline.ledger import Ledger

LINES = [
    ("Adrian", "I'm in"),
    ("Tessa", "I'm in"),
    ("John", "I'm in"),
    ("Adrian", "I paid $48, Tessa and John rode."),
    ("Tessa", "I just paid Adrian $16."),
    ("Tessa", "What do I owe?"),
]


def main() -> None:
    ledger = Ledger(Path(tempfile.mkdtemp()) / "ledger.json")
    for speaker, text in LINES:
        print(f"\n{speaker}: {text}")
        print(handle(text, speaker, ledger)["reply"])


if __name__ == "__main__":
    main()
