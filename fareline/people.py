"""The people on the tab. Names stay fixed so the chat and the tests match."""

PEOPLE = ("Adrian", "Tessa", "John")


def canonical(name: object) -> str | None:
    if not isinstance(name, str):
        return None
    key = name.strip().lower()
    for person in PEOPLE:
        if person.lower() == key:
            return person
    return None
