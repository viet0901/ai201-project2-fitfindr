# FitFindr

FitFindr is a thrift shopping assistant that finds secondhand listings, suggests outfits using your existing wardrobe, and writes a social media fit card caption. The agent runs three tools in order through a planning loop in `agent.py`, passing state between each step via a session dict.

## Setup

```bash
pip install -r requirements.txt
```

Add your Groq API key to `.env`:
```
GROQ_API_KEY=your_key_here
```

Run the Gradio app:
```bash
python app.py
```

Run tests:
```bash
pytest tests/ -v
```

Trigger all failure modes for demo screenshots:
```bash
python test_failure_modes.py
python agent.py
```

---

## Tool Inventory

### 1. `search_listings(description, size, max_price)` → `list[dict]`

**Purpose:** Search mock listings in `data/listings.json` and return matches sorted by relevance.

**Inputs:**
- `description` (str): keywords to match against title, description, and style_tags
- `size` (str or None): size filter; case insensitive (`"M"` matches `"S/M"`)
- `max_price` (float or None): max price in dollars; listings above this are dropped

**Returns:** A list of listing dicts, best match first. Each dict contains:
`id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, `platform`.

Returns `[]` if nothing matches. Does not raise an exception.

**Failure mode:** If the list is empty, the agent sets `session["error"]` with a specific message (see Error Handling) and returns early without calling the other tools.

### 2. `suggest_outfit(new_item, wardrobe)` → `str`

**Purpose:** Use Groq (`llama-3.3-70b-versatile`) to suggest 1 to 2 outfits pairing the new listing with the user's wardrobe.

**Inputs:**
- `new_item` (dict): full listing dict from `search_listings`
- `wardrobe` (dict): closet with an `items` list; each item has `id`, `name`, `category`, `colors`, `style_tags`, `notes`

**Returns:** A non empty string with outfit ideas in plain English.

**Failure mode:** If `wardrobe["items"]` is empty, the tool still returns general styling advice (no crash). If the LLM returns an empty string, the agent sets `session["error"]` and stops before `create_fit_card`.

### 3. `create_fit_card(outfit, new_item)` → `str`

**Purpose:** Use Groq to write a casual 2 to 4 sentence Instagram/TikTok caption.

**Inputs:**
- `outfit` (str): styling advice from `suggest_outfit`
- `new_item` (dict): the same listing dict passed to `suggest_outfit`

**Returns:** A caption string mentioning item name, price, and platform once each. If `outfit` is blank, returns `"Cannot create fit card without an outfit suggestion."` (no exception).

**Failure mode:** Agent copies that error string into `session["error"]` and leaves `fit_card` as None.

---

## Planning Loop

The entry point is `run_agent(query, wardrobe)` in `agent.py`.

**Conditional logic:**

1. Parse query with regex → store `description`, `size`, `max_price` in `session["parsed"]`
2. Call `search_listings(parsed["description"], parsed["size"], parsed["max_price"])`
3. **If `search_results` is empty:** set `session["error"]` to a message naming the failed search and suggesting fixes (raise budget, change size, broader keywords). **Return immediately.** Do not call `suggest_outfit` or `create_fit_card`.
4. **If results exist:** set `session["selected_item"] = search_results[0]`
5. Call `suggest_outfit(selected_item, wardrobe)` → save to `session["outfit_suggestion"]`
6. **If outfit is empty/whitespace:** set error, return early (skip `create_fit_card`)
7. Call `create_fit_card(outfit_suggestion, selected_item)` → save to `session["fit_card"]`
8. Return session

The agent does **not** call all three tools unconditionally. A no results query stops after step 3.

**Example branch difference:**
- Happy path: `"vintage graphic tee under $30"` → all three tools run, three Gradio panels fill
- Failure path: `"designer ballgown size XXS under $5"` → only `search_listings` runs; user sees error in listing panel only

---

## State Management

Everything lives in one session dict from `_new_session()`:

| Field | Type | When set | Passed to |
|-------|------|----------|-----------|
| `query` | str | start | never changes |
| `parsed` | dict | after regex parse | `search_listings` inputs |
| `search_results` | list[dict] | after search | top item → `selected_item` |
| `selected_item` | dict or None | after search | `suggest_outfit`, `create_fit_card` |
| `wardrobe` | dict | start | `suggest_outfit` |
| `outfit_suggestion` | str or None | after suggest | `create_fit_card` |
| `fit_card` | str or None | after fit card | Gradio UI |
| `error` | str or None | on any failure | Gradio UI |

**State flow (no re entry):**
```
search_listings → search_results → selected_item
selected_item + wardrobe → suggest_outfit → outfit_suggestion
outfit_suggestion + selected_item → create_fit_card → fit_card
```

The exact same `selected_item` dict from search is passed into both LLM tools. The user never re types the item.

Verified in `tests/test_agent.py::test_run_agent_passes_state_between_tools` and by running `python agent.py`.

---

## Error Handling

| Tool | Failure mode | What the agent does |
|------|-------------|----------------------|
| `search_listings` | No matches | Sets error: `"No listings matched your search for 'designer ballgown' under $5 in size XXS. Try raising your budget, trying a different size, or using broader keywords."` Returns early. `fit_card` and `outfit_suggestion` stay None. |
| `suggest_outfit` | Empty wardrobe | Tool returns general advice; agent continues normally. |
| `suggest_outfit` | Empty LLM response | Sets `"Could not generate an outfit suggestion."` Returns early. |
| `create_fit_card` | Blank outfit input | Returns error string; agent sets `session["error"]`, no caption. |

**Concrete test example (deliberately triggered):**
```bash
python -c "from tools import search_listings; print(search_listings('designer ballgown', size='XXS', max_price=5))"
# → []

python test_failure_modes.py
# prints all three failure modes with OK confirmations
```

Screenshot `test_failure_modes.py` output or run `"designer ballgown size XXS under $5"` in the Gradio app for your demo video.

---

## Complete Interaction Walkthrough

**Query:** `"I'm looking for a vintage tee under $30. I mostly wear baggy jeans and chunky shoes."`

1. **Parse:** `description="vintage tee"`, `size=None`, `max_price=30.0`
2. **`search_listings("vintage tee", None, 30.0)`** → list of matching tees; agent picks top result (e.g. lst_006 Graphic Tee, $24)
3. **`suggest_outfit(selected_item, wardrobe)`** → outfit string naming baggy jeans and chunky sneakers from example wardrobe
4. **`create_fit_card(outfit_suggestion, selected_item)`** → casual caption for Instagram/TikTok

User sees three panels: listing details, outfit idea, fit card.

Full step by step trace is in `planning.md` under **A Complete Interaction**.

---

## Project Structure

```
ai201-project2-fitfindr/
├── agent.py              # planning loop (run_agent)
├── app.py                # Gradio UI
├── tools.py              # search_listings, suggest_outfit, create_fit_card
├── planning.md           # spec, diagram, walkthrough
├── test_failure_modes.py # deliberate failure mode script for demo
├── tests/
│   ├── test_tools.py
│   └── test_agent.py
├── data/
│   ├── listings.json
│   └── wardrobe_schema.json
└── utils/
    └── data_loader.py
```

Architecture diagram and AI Tool Plan are in `planning.md`.

---

## AI Usage Transparency

### Instance 1: Implementing `search_listings` and LLM tools

**What I directed AI to do:** Paste the Tool 1 block from `planning.md` (inputs, return value, failure mode) and ask it to implement `search_listings()` using `load_listings()`. Same for `suggest_outfit` and `create_fit_card` one at a time.

**What I reviewed/revised:** Checked that all three parameters are used in search, that empty results return `[]` not an exception, that `create_fit_card` takes both `outfit` and `new_item`, and that empty wardrobe does not crash. Ran `pytest tests/` after each tool.

### Instance 2: Planning loop in `agent.py`

**What I directed AI to do:** Shared the Architecture diagram, Planning Loop, and State Management sections from `planning.md` plus the `run_agent()` stub. Asked for early return when search is empty.

**What I reviewed/revised:** Confirmed the code branches on empty `search_results` before calling LLM tools (verified with mocked tests). Adjusted the error message to include the parsed description, price, and size so the user knows what failed. Added `test_failure_modes.py` for demo documentation.

---

## Spec Reflection

**One way the spec helped:** Writing the Architecture diagram with explicit error branches before coding made it obvious that `suggest_outfit` must not run when search returns `[]`. The diagram caught a common mistake (calling all three tools every time) before implementation.

**One divergence:** The planning.md walkthrough assumes lst_033 (Vintage Band Tee) is the top search result, but keyword scoring sometimes ranks lst_006 or lst_002 higher. The agent still works correctly; only the example listing in the walkthrough varies. I kept the walkthrough descriptive ("top result") rather than hardcoding one listing id.

---

## Stretch Features

Not implemented.
