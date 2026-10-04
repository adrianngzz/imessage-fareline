from agent import strip_routing


def test_strip_asi_one_mention() -> None:
    raw = (
        "@agent1qt4svle0njg43593l69cp0xt3366d9d6r99wpkfj2sl0mjf02uj9unaplud "
        "Riley: What do I owe?"
    )
    assert strip_routing(raw) == "Riley: What do I owe?"
