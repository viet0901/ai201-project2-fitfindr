import os
from unittest.mock import patch

import pytest

from tools import create_fit_card, search_listings, suggest_outfit
from utils.data_loader import get_empty_wardrobe, get_example_wardrobe

SAMPLE_ITEM = {
    "id": "lst_033",
    "title": "Vintage Band Tee — Faded Grey",
    "description": "Faded grey band-style tee with distressed graphic.",
    "category": "tops",
    "style_tags": ["vintage", "grunge", "band tee", "graphic tee"],
    "size": "L",
    "condition": "fair",
    "price": 19.0,
    "colors": ["grey", "charcoal"],
    "brand": None,
    "platform": "depop",
}


# ── search_listings ───────────────────────────────────────────────────────────

def test_search_returns_results():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert isinstance(results, list)
    assert len(results) > 0
    assert "id" in results[0]
    assert "title" in results[0]
    assert "price" in results[0]


def test_search_empty_results():
    results = search_listings("designer ballgown", size="XXS", max_price=5)
    assert results == []


def test_search_price_filter():
    results = search_listings("jacket", size=None, max_price=10)
    assert all(item["price"] <= 10 for item in results)


def test_search_size_filter():
    results = search_listings("vintage", size="M", max_price=50)
    assert all("m" in item["size"].lower() for item in results)


# ── suggest_outfit ──────────────────────────────────────────────────────────────

@patch("tools._call_groq", return_value="Try wide leg jeans and chunky sneakers for a grunge vibe.")
def test_suggest_outfit_empty_wardrobe(mock_groq):
    """Failure mode: wardrobe is empty — should not crash, returns general advice."""
    result = suggest_outfit(SAMPLE_ITEM, get_empty_wardrobe())
    assert isinstance(result, str)
    assert result.strip() != ""
    prompt = mock_groq.call_args[0][0]
    assert "empty" in prompt.lower()
    mock_groq.assert_called_once()


@patch("tools._call_groq", return_value="Pair this tee with your baggy straight leg jeans.")
def test_suggest_outfit_with_wardrobe(mock_groq):
    result = suggest_outfit(SAMPLE_ITEM, get_example_wardrobe())
    assert isinstance(result, str)
    assert result.strip() != ""
    prompt = mock_groq.call_args[0][0]
    assert "Baggy straight leg jeans" in prompt or "THEIR CLOSET" in prompt


@patch("tools._call_groq", return_value="General styling tips.")
def test_suggest_outfit_missing_items_key(mock_groq):
    """Wardrobe dict with no items key should not crash."""
    result = suggest_outfit(SAMPLE_ITEM, {})
    assert isinstance(result, str)
    assert result.strip() != ""


# ── create_fit_card ─────────────────────────────────────────────────────────────

def test_create_fit_card_empty_outfit():
    """Failure mode: outfit is blank — return error string, no exception."""
    result = create_fit_card("", SAMPLE_ITEM)
    assert result == "Cannot create fit card without an outfit suggestion."


def test_create_fit_card_whitespace_outfit():
    result = create_fit_card("   ", SAMPLE_ITEM)
    assert result == "Cannot create fit card without an outfit suggestion."


@patch("tools._call_groq", return_value="thrifted this band tee off depop for $19, full fit on my story")
def test_create_fit_card_success(mock_groq):
    outfit = "Pair with baggy jeans and chunky sneakers."
    result = create_fit_card(outfit, SAMPLE_ITEM)
    assert isinstance(result, str)
    assert result.strip() != ""
    assert mock_groq.call_args[1]["temperature"] >= 0.9


@patch("tools._call_groq")
def test_create_fit_card_uses_both_arguments(mock_groq):
    mock_groq.return_value = "caption"
    outfit = "Pair with baggy jeans."
    create_fit_card(outfit, SAMPLE_ITEM)
    prompt = mock_groq.call_args[0][0]
    assert SAMPLE_ITEM["title"] in prompt
    assert outfit in prompt


@pytest.mark.skipif(not os.getenv("GROQ_API_KEY"), reason="GROQ_API_KEY not set")
def test_create_fit_card_outputs_vary():
    """Integration: captions should differ across runs (temperature >= 0.9)."""
    outfit = "Pair with baggy jeans and chunky sneakers for a relaxed look."
    captions = [create_fit_card(outfit, SAMPLE_ITEM) for _ in range(4)]
    assert len(set(captions)) > 1, "Expected varied captions; try raising temperature"
