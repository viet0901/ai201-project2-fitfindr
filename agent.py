"""
agent.py

The FitFindr planning loop. Orchestrates the three tools in response to a
natural language user query, passing state between them via a session dict.

Complete tools.py and test each tool in isolation before implementing this file.

Usage (once implemented):
    from agent import run_agent
    from utils.data_loader import get_example_wardrobe

    result = run_agent(
        query="vintage graphic tee under $30, size M",
        wardrobe=get_example_wardrobe(),
    )
    print(result["fit_card"])
    print(result["error"])   # None on success
"""

from tools import search_listings, suggest_outfit, create_fit_card

import re


def _parse_query(query: str) -> dict:
    """Extract description, size, and max_price from a natural language query."""
    text = query.strip()
    max_price = None
    size = None

    price_match = re.search(
        r"(?:under|below|max|<=?)\s*\$?\s*(\d+(?:\.\d+)?)",
        text,
        re.IGNORECASE,
    )
    if price_match:
        max_price = float(price_match.group(1))

    size_match = re.search(
        r"(?:size|sz)\.?\s*([a-z0-9/]+(?:\s*\([^)]+\))?)",
        text,
        re.IGNORECASE,
    )
    if not size_match:
        size_match = re.search(
            r"in size\s*([a-z0-9/]+)",
            text,
            re.IGNORECASE,
        )
    if size_match:
        size = size_match.group(1).strip()

    description = text
    description = re.sub(
        r"(?:under|below|max|<=?)\s*\$?\s*\d+(?:\.\d+)?",
        "",
        description,
        flags=re.IGNORECASE,
    )
    description = re.sub(
        r"(?:size|sz)\.?\s*[a-z0-9/]+(?:\s*\([^)]+\))?",
        "",
        description,
        flags=re.IGNORECASE,
    )
    description = re.sub(
        r"in size\s*[a-z0-9/]+",
        "",
        description,
        flags=re.IGNORECASE,
    )
    description = re.sub(
        r"^(?:i['']m looking for|looking for|find me|i want|i need)\s*",
        "",
        description,
        flags=re.IGNORECASE,
    )
    description = re.sub(r"\s+", " ", description).strip(" .?,!")

    if not description:
        description = text

    return {
        "description": description,
        "size": size,
        "max_price": max_price,
    }


# ── session state ─────────────────────────────────────────────────────────────

def _new_session(query: str, wardrobe: dict) -> dict:
    """
    Initialize and return a fresh session dict for one user interaction.

    The session dict is the single source of truth for everything that happens
    during a run — it stores the original query, parsed parameters, tool results,
    and any error that caused early termination.

    You may add fields to this dict as needed for your implementation.
    """
    return {
        "query": query,              # original user query
        "parsed": {},                # extracted description / size / max_price
        "search_results": [],        # list of matching listing dicts
        "selected_item": None,       # top result, passed into suggest_outfit
        "wardrobe": wardrobe,        # user's wardrobe dict
        "outfit_suggestion": None,   # string returned by suggest_outfit
        "fit_card": None,            # string returned by create_fit_card
        "error": None,               # set if the interaction ended early
    }


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Main agent entry point. Runs the FitFindr planning loop for a single
    user interaction and returns the completed session dict.

    Args:
        query:    Natural language user request
                  (e.g., "vintage graphic tee under $30, size M")
        wardrobe: User's wardrobe dict — use get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py

    Returns:
        The session dict after the interaction completes. Check session["error"]
        first — if it is not None, the interaction ended early and the other
        output fields (outfit_suggestion, fit_card) will be None.

    TODO — implement this function using the planning loop you designed in planning.md:

        Step 1: Initialize the session with _new_session().

        Step 2: Parse the user's query to extract a description, size, and
                max_price. You can use regex, string splitting, or ask the LLM
                to parse it — document your choice in planning.md.
                Store the result in session["parsed"].

        Step 3: Call search_listings() with the parsed parameters.
                Store results in session["search_results"].
                If no results: set session["error"] to a helpful message and
                return the session early. Do NOT proceed to suggest_outfit
                with empty input.

        Step 4: Select the item to use (e.g., the top result).
                Store it in session["selected_item"].

        Step 5: Call suggest_outfit() with the selected item and wardrobe.
                Store the result in session["outfit_suggestion"].

        Step 6: Call create_fit_card() with the outfit suggestion and selected item.
                Store the result in session["fit_card"].

        Step 7: Return the session.

    Before writing code, complete the Planning Loop and State Management sections
    of planning.md — your implementation should match what you described there.
    """
    session = _new_session(query, wardrobe)

    session["parsed"] = _parse_query(query)
    parsed = session["parsed"]

    session["search_results"] = search_listings(
        parsed["description"],
        parsed["size"],
        parsed["max_price"],
    )

    if not session["search_results"]:
        session["error"] = (
            f"No listings matched your search for '{parsed['description']}'"
            + (f" under ${parsed['max_price']:.0f}" if parsed["max_price"] else "")
            + (f" in size {parsed['size']}" if parsed["size"] else "")
            + ". Try raising your budget, trying a different size, or using broader keywords."
        )
        return session

    session["selected_item"] = session["search_results"][0]

    session["outfit_suggestion"] = suggest_outfit(
        session["selected_item"],
        session["wardrobe"],
    )

    if not session["outfit_suggestion"] or not session["outfit_suggestion"].strip():
        session["error"] = "Could not generate an outfit suggestion."
        return session

    session["fit_card"] = create_fit_card(
        session["outfit_suggestion"],
        session["selected_item"],
    )

    if session["fit_card"] == "Cannot create fit card without an outfit suggestion.":
        session["error"] = session["fit_card"]
        session["fit_card"] = None

    return session


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

    print("=== Happy path: graphic tee ===\n")
    session = run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    )
    if session["error"]:
        print(f"Error: {session['error']}")
    else:
        print(f"Found: {session['selected_item']['title']}")
        print(f"\nOutfit: {session['outfit_suggestion']}")
        print(f"\nFit card: {session['fit_card']}")

    print("\n\n=== No-results path ===\n")
    session2 = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )
    print(f"Error message: {session2['error']}")
    print(f"fit_card is None: {session2['fit_card'] is None}")
    print(f"outfit_suggestion is None: {session2['outfit_suggestion'] is None}")

    print("\n\n=== Planning.md walkthrough ===\n")
    session3 = run_agent(
        query="I'm looking for a vintage tee under $30. I mostly wear baggy jeans and chunky shoes. What's out there and how would I style it?",
        wardrobe=get_example_wardrobe(),
    )
    if session3["error"]:
        print(f"Error: {session3['error']}")
    else:
        print(f"parsed: {session3['parsed']}")
        print(f"selected_item id: {session3['selected_item']['id']}")
        print(f"outfit_suggestion (first 120 chars): {session3['outfit_suggestion'][:120]}...")
        print(f"fit_card (first 120 chars): {session3['fit_card'][:120]}...")
        print("State flow OK: selected_item -> suggest_outfit -> outfit_suggestion -> create_fit_card")
