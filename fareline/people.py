"""The four interns in the demo. Names stay fixed so the videos match the tests."""

PEOPLE = ("Riley", "Alex", "Sam", "Jordan")


def canonical(name: object) -> str | None:
    if not isinstance(name, str):
        return None
    key = name.strip().lower()
    for person in PEOPLE:
        if person.lower() == key:
            return person
    return None
