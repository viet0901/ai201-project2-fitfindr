"""
Milestone 5: Deliberately trigger each failure mode and print results.

Run from project root:
    .venv/bin/python test_failure_modes.py

Use the terminal output for demo screenshots or screen recording.
"""

from agent import run_agent
from tools import create_fit_card, search_listings, suggest_outfit
from utils.data_loader import get_empty_wardrobe, get_example_wardrobe


def main():
    print("=" * 60)
    print("FAILURE MODE 1: search_listings returns []")
    print("=" * 60)
    results = search_listings("designer ballgown", size="XXS", max_price=5)
    print(f"search_listings result: {results!r}")
    assert results == [], "Expected empty list"
    print("OK: returned [] with no exception\n")

    print("=" * 60)
    print("FAILURE MODE 1 (full agent): impossible query")
    print("=" * 60)
    session = run_agent(
        "designer ballgown size XXS under $5",
        get_example_wardrobe(),
    )
    print(f"session['error']: {session['error']}")
    print(f"session['fit_card']: {session['fit_card']}")
    print(f"session['outfit_suggestion']: {session['outfit_suggestion']}")
    assert session["error"] is not None
    assert session["fit_card"] is None
    assert session["outfit_suggestion"] is None
    print("OK: agent stopped early with helpful error\n")

    print("=" * 60)
    print("FAILURE MODE 2: suggest_outfit with empty wardrobe")
    print("=" * 60)
    items = search_listings("vintage graphic tee", size=None, max_price=50)
    advice = suggest_outfit(items[0], get_empty_wardrobe())
    print(f"Returned string ({len(advice.strip())} chars):")
    print(advice)
    assert isinstance(advice, str) and advice.strip() != ""
    print("OK: general styling advice, no exception\n")

    print("=" * 60)
    print("FAILURE MODE 3: create_fit_card with empty outfit")
    print("=" * 60)
    err = create_fit_card("", items[0])
    print(f"Returned: {err!r}")
    assert err == "Cannot create fit card without an outfit suggestion."
    print("OK: error message string, no exception\n")

    print("=" * 60)
    print("All failure modes passed.")
    print("=" * 60)


if __name__ == "__main__":
    main()
