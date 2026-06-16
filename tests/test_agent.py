from unittest.mock import patch

import pytest

from agent import _parse_query, run_agent
from utils.data_loader import get_example_wardrobe


def test_parse_query_extracts_price_and_description():
    parsed = _parse_query("looking for a vintage graphic tee under $30")
    assert parsed["max_price"] == 30.0
    assert parsed["size"] is None
    assert "vintage graphic tee" in parsed["description"].lower()


def test_parse_query_extracts_size():
    parsed = _parse_query("90s track jacket in size M under $50")
    assert parsed["size"] == "M"
    assert parsed["max_price"] == 50.0


@patch("agent.create_fit_card", return_value="fit card caption")
@patch("agent.suggest_outfit", return_value="Pair with baggy jeans.")
@patch("agent.search_listings")
def test_run_agent_no_results_skips_llm_tools(mock_search, mock_suggest, mock_fit_card):
    mock_search.return_value = []

    session = run_agent("designer ballgown size XXS under $5", get_example_wardrobe())

    assert session["error"] is not None
    assert session["selected_item"] is None
    assert session["outfit_suggestion"] is None
    assert session["fit_card"] is None
    mock_suggest.assert_not_called()
    mock_fit_card.assert_not_called()


@patch("agent.create_fit_card", return_value="fit card caption")
@patch("agent.suggest_outfit", return_value="Pair with baggy jeans.")
@patch("agent.search_listings")
def test_run_agent_passes_state_between_tools(mock_search, mock_suggest, mock_fit_card):
    listing = {
        "id": "lst_033",
        "title": "Vintage Band Tee",
        "description": "A faded tee",
        "category": "tops",
        "style_tags": ["vintage"],
        "size": "L",
        "condition": "fair",
        "price": 19.0,
        "colors": ["grey"],
        "brand": None,
        "platform": "depop",
    }
    mock_search.return_value = [listing]

    session = run_agent("vintage tee under $30", get_example_wardrobe())

    assert session["error"] is None
    assert session["selected_item"] == listing
    mock_suggest.assert_called_once_with(listing, session["wardrobe"])
    mock_fit_card.assert_called_once_with("Pair with baggy jeans.", listing)
    assert session["outfit_suggestion"] == "Pair with baggy jeans."
    assert session["fit_card"] == "fit card caption"


@patch("agent.create_fit_card")
@patch("agent.suggest_outfit", return_value="   ")
@patch("agent.search_listings")
def test_run_agent_empty_outfit_stops_before_fit_card(mock_search, mock_suggest, mock_fit_card):
    listing = {"id": "lst_001", "title": "Test", "price": 10.0, "platform": "depop"}
    mock_search.return_value = [listing]

    session = run_agent("vintage tee under $30", get_example_wardrobe())

    assert session["error"] == "Could not generate an outfit suggestion."
    assert session["fit_card"] is None
    mock_fit_card.assert_not_called()
