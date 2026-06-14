# FitFindr — planning.md

> Complete this document before writing any implementation code.
> Your spec and agent diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Your planning.md will be reviewed as part of your submission.
> Update it before starting any stretch features.

---

## Tools

List every tool your agent will use. For each tool, fill in all four fields.
You must have at least 3 tools. The three required tools are listed — add any additional tools below them.

### Tool 1: search_listings

**What it does:**
Looks through all listing data in data/listings.json and finds items that match what the user asked for. It filters by size and price if those are given, then ranks matches by how well they fit the description. Uses load_listings() from utils/data_loader.py.

**Input parameters:**
- `description` (str): The keywords the user is looking for, like "vintage graphic tee". The tool checks if these words show up in the listing title, description, or style_tags.
- `size` (str or None): The size the user wants, like "M" or "L". If None, skip size filtering. Matching is not strict, so "M" can match "S/M" or "M".
- `max_price` (float or None): The highest price the user will pay. If None, skip price filtering. Only returns listings where price is less than or equal to max_price.

**What it returns:**
A list of listing dicts, sorted best match first. Each dict has these fields:
- `id` (str): listing id like "lst_033"
- `title` (str): item name like "Vintage Band Tee in faded grey"
- `description` (str): full item details
- `category` (str): tops, bottoms, outerwear, shoes, or accessories
- `style_tags` (list[str]): style words like "vintage", "graphic tee", "grunge"
- `size` (str): size label like "L" or "S/M"
- `condition` (str): excellent, good, or fair
- `price` (float): price in dollars like 19.0
- `colors` (list[str]): colors like "grey" or "black"
- `brand` (str or None): brand name or null
- `platform` (str): depop, thredUp, or poshmark

Returns an empty list `[]` if nothing matches. Does not raise an error.

**What happens if it fails or returns nothing:**
The agent sets session["error"] to a helpful message telling the user nothing matched. It suggests trying a higher budget, a different size, or broader keywords. Then it returns the session early. It does not call suggest_outfit or create_fit_card.

---

### Tool 2: suggest_outfit

**What it does:**
Takes the listing the user might buy and their existing wardrobe, then uses the Groq LLM to suggest how to style the new item. If the wardrobe has items, it picks specific pieces from the closet. If the wardrobe is empty, it gives general styling advice instead.

**Input parameters:**
- `new_item` (dict): One full listing dict from search_listings (same fields as above: id, title, description, category, style_tags, size, condition, price, colors, brand, platform).
- `wardrobe` (dict): The user's closet. Has an `items` key with a list of wardrobe item dicts. Each wardrobe item has:
  - `id` (str): like "w_001"
  - `name` (str): like "Baggy straight leg jeans, dark wash"
  - `category` (str): tops, bottoms, outerwear, shoes, or accessories
  - `colors` (list[str])
  - `style_tags` (list[str])
  - `notes` (str or None): extra info about fit or how the user wears it

**What it returns:**
A non empty string with 1 to 2 outfit ideas written in plain English. Example: "Pair this band tee with your baggy straight leg jeans and chunky white sneakers. Roll the sleeves once for a cleaner look."

If the wardrobe is empty, still returns a string with general advice like what types of bottoms and shoes would go well with the item.

**What happens if it fails or returns nothing:**
If wardrobe["items"] is empty, the tool still runs and returns general styling tips for the new item. It does not crash or return an empty string. If the LLM call fails, the agent sets session["error"] to a message like "Could not generate outfit suggestion" and returns early without calling create_fit_card.

---

### Tool 3: create_fit_card

**What it does:**
Takes the outfit suggestion and the listing, then uses the Groq LLM to write a short social media caption. The caption should sound casual, like something someone would post on Instagram or TikTok after thrifting something.

**Input parameters:**
- `outfit` (str): The styling advice string returned by suggest_outfit. Must not be empty when passed in.
- `new_item` (dict): The same listing dict used in suggest_outfit (id, title, description, category, style_tags, size, condition, price, colors, brand, platform).

**What it returns:**
A string with 2 to 4 sentences that works as a post caption. It should mention the item name, price, and platform once each in a natural way. Example: "found this faded band tee on depop for $19 and it goes perfect with my baggy jeans, full fit on my story."

If outfit is empty or only whitespace, returns an error message string like "Cannot create fit card without an outfit suggestion." Does not raise an exception.

**What happens if it fails or returns nothing:**
If outfit is missing or blank, the tool returns an error message string instead of a caption. The agent checks if the fit_card looks like an error, sets session["error"], and returns early. If the LLM call fails, the agent sets session["error"] to "Could not generate fit card" and returns the session.

---

### Additional Tools (if any)

None. FitFindr uses only the three required tools above.

---

## Planning Loop

**How does your agent decide which tool to call next?**

The main function is run_agent(query, wardrobe) in agent.py. It always runs the same steps in order, but stops early if something goes wrong.

1. **Start session.** Call _new_session(query, wardrobe) to create a session dict with empty fields for results and error set to None.

2. **Parse the query.** Pull description, size, and max_price out of the user's message. Use simple regex to find things like "under $30" or "size M". Everything else becomes the description. Store in session["parsed"] as `{"description": "...", "size": "M", "max_price": 30.0}`. If size or price is not found, set that field to None.

3. **Run search_listings.** Call search_listings with session["parsed"]["description"], session["parsed"]["size"], and session["parsed"]["max_price"]. Save the return value in session["search_results"].

4. **Check search results.** If session["search_results"] is empty (length is 0):
   - Set session["error"] to a message like "No listings found for your search. Try raising your budget, trying a different size, or using broader keywords."
   - Return session immediately. Do not run suggest_outfit or create_fit_card.

5. **Pick the top item.** Set session["selected_item"] = session["search_results"][0] (the best match).

6. **Run suggest_outfit.** Call suggest_outfit(session["selected_item"], session["wardrobe"]). Save the string in session["outfit_suggestion"].

7. **Check outfit suggestion.** If session["outfit_suggestion"] is empty or only whitespace:
   - Set session["error"] to "Could not generate an outfit suggestion."
   - Return session immediately. Do not call create_fit_card.

8. **Run create_fit_card.** Call create_fit_card(session["outfit_suggestion"], session["selected_item"]). Save the string in session["fit_card"].

9. **Done.** Return session. If session["error"] is still None, the interaction succeeded. The caller can read selected_item, outfit_suggestion, and fit_card from the session.

---

## State Management

**How does information from one tool get passed to the next?**

Everything lives in one session dict created by _new_session(). Each tool step reads from and writes to this dict. No separate global state.

Fields tracked in the session:
- `query` (str): the original user message, never changes
- `parsed` (dict): extracted description, size, max_price from step 2
- `search_results` (list[dict]): all matching listings from search_listings
- `selected_item` (dict or None): the top listing picked from search_results, passed into suggest_outfit and create_fit_card
- `wardrobe` (dict): the user's closet, passed into suggest_outfit
- `outfit_suggestion` (str or None): styling advice from suggest_outfit, passed into create_fit_card
- `fit_card` (str or None): final caption from create_fit_card
- `error` (str or None): if set, something went wrong and the loop stopped early

Flow between tools:
- search_listings output → stored in search_results → top item copied to selected_item
- selected_item + wardrobe → suggest_outfit → outfit_suggestion
- outfit_suggestion + selected_item → create_fit_card → fit_card

If error is set at any checkpoint, later fields stay None and no more tools run.

---

## Error Handling

For each tool, describe the specific failure mode you're handling and what the agent does in response.

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query | Set session["error"] to: "No listings matched your search for 'vintage tee' under $30. Try raising your budget (for example under $40), dropping the size filter, or using broader keywords like 'graphic tee' or 'band tee'." Return session early. selected_item, outfit_suggestion, and fit_card stay None. Do not call suggest_outfit or create_fit_card. |
| suggest_outfit | Wardrobe is empty | Tool still runs and returns general styling advice, like "This tee would look good with wide leg jeans and chunky sneakers." Agent saves it to session["outfit_suggestion"] and continues to create_fit_card normally. |
| suggest_outfit | LLM returns empty string | Set session["error"] to: "Sorry, I could not put together an outfit suggestion right now. Try sending your message again." Return session early. fit_card stays None. Do not call create_fit_card. |
| create_fit_card | Outfit input is missing or incomplete | Tool returns: "Cannot create fit card without an outfit suggestion." Agent copies that into session["error"], leaves session["fit_card"] as None, and returns session. User sees the error message and no caption. |
| create_fit_card | LLM call fails | Set session["error"] to: "Sorry, I could not write a fit card caption right now. Your listing and outfit suggestion are still saved in the session. Try again in a moment." Return session with selected_item and outfit_suggestion filled but fit_card as None. |

---

## Architecture

```
User
  │
  │  query (str), wardrobe (dict)
  ▼
Planning Loop (run_agent in agent.py)
  │
  ├─► Session State (_new_session)
  │       query, parsed={}, search_results=[], selected_item=None,
  │       wardrobe, outfit_suggestion=None, fit_card=None, error=None
  │
  ├─► Parse query (regex)
  │       │
  │       ▼
  │   Session: parsed = {description, size, max_price}
  │
  ├─► search_listings(description, size, max_price)
  │       │
  │       ▼
  │   Session: search_results = [listing dicts] or []
  │       │
  │       ├── results = []  ──────────────────────────────────────┐
  │       │       ▼                                                 │
  │       │   Session: error = "No listings matched your search..." │
  │       │       │                                                 │
  │       │       └──► RETURN session (early exit) ◄────────────────┤
  │       │                                                         │
  │       └── results = [item, item, ...]                           │
  │               ▼                                                 │
  │           Session: selected_item = search_results[0]            │
  │               │                                                 │
  ├─► suggest_outfit(selected_item, wardrobe)                       │
  │       │                                                         │
  │       ▼                                                         │
  │   Session: outfit_suggestion = "..." (str)                      │
  │       │                                                         │
  │       ├── outfit_suggestion is empty  ──────────────────────────┤
  │       │       ▼                                                 │
  │       │   Session: error = "Could not generate outfit..."       │
  │       │       │                                                 │
  │       │       └──► RETURN session (early exit) ◄────────────────┤
  │       │                                                         │
  │       └── outfit_suggestion has text                            │
  │               │                                                 │
  └─► create_fit_card(outfit_suggestion, selected_item)             │
          │                                                         │
          ▼                                                         │
      Session: fit_card = "..." (str)                               │
          │                                                         │
          ├── outfit was blank (tool error string)  ──────────────────┤
          │       ▼                                                 │
          │   Session: error = "Cannot create fit card..."          │
          │       │                                                 │
          │       └──► RETURN session (early exit) ◄────────────────┘
          │
          └── success
                  ▼
              RETURN session (error is still None)
                  │
                  ▼
              User sees: selected_item + outfit_suggestion + fit_card
```

**Components:**
- **User** sends a natural language query and a wardrobe dict.
- **Planning Loop** (`run_agent`) parses the query, calls tools in order, and decides when to stop.
- **Session State** is one dict that holds parsed inputs, every tool result, and any error message.
- **search_listings** reads listings.json via load_listings(), filters and ranks matches.
- **suggest_outfit** uses the Groq LLM to style the selected listing with the wardrobe.
- **create_fit_card** uses the Groq LLM to write a social media caption.

**Data flow:** query → parsed params → search_results → selected_item → outfit_suggestion → fit_card. The wardrobe goes directly from the user into suggest_outfit. Any error branch writes to session["error"] and returns immediately without running later tools.

---

## AI Tool Plan

**Milestone 3: Individual tool implementations**

**Tool: search_listings**
- **AI tool:** Cursor with Claude
- **Input I will give it:** The Tool 1 block from planning.md (what it does, input parameters, return value, failure mode), the Architecture diagram above, and the load_listings() docstring from utils/data_loader.py
- **Expected output:** A search_listings() function in tools.py that loads listings, filters by max_price and size when provided, scores by keyword overlap in title/description/style_tags, drops zero score matches, sorts by score, and returns listing dicts (or an empty list)
- **How I will verify:** Before running it, I will read the code and check that all three parameters are used and that it returns [] instead of crashing when nothing matches. Then I will test three queries in a Python shell: (1) `search_listings("vintage graphic tee", "M", 30.0)` should return at least one dict with id, title, and price fields, (2) `search_listings("designer ballgown", "XXS", 5.0)` should return `[]`, (3) `search_listings("grunge flannel", None, 25.0)` should return matches without size filtering

**Tool: suggest_outfit**
- **AI tool:** Cursor with Claude
- **Input I will give it:** The Tool 2 block from planning.md, the wardrobe item fields from State Management, and the suggest_outfit stub in tools.py
- **Expected output:** A suggest_outfit() function that calls Groq, handles empty wardrobe with general advice, names specific wardrobe pieces when items exist, and always returns a non empty string on success
- **How I will verify:** I will run it with one listing from search_listings plus get_example_wardrobe() and confirm the response mentions wardrobe item names like "baggy straight leg jeans." Then I will run it with get_empty_wardrobe() and confirm it still returns general styling tips without crashing

**Tool: create_fit_card**
- **AI tool:** Cursor with Claude
- **Input I will give it:** The Tool 3 block from planning.md, the Error Handling row for create_fit_card, and the create_fit_card stub in tools.py
- **Expected output:** A create_fit_card() function that guards against blank outfit input, calls Groq with item details and outfit text, and returns a 2 to 4 sentence casual caption mentioning title, price, and platform
- **How I will verify:** I will test with a real outfit string and lst_033 listing dict and check the caption mentions "depop" and "$19." Then I will call create_fit_card("", listing) and confirm it returns the error string instead of raising an exception

**Milestone 4: Planning loop and state management**

- **AI tool:** Cursor with Claude
- **Input I will give it:** The Planning Loop section, State Management section, Architecture diagram, Error Handling table, and the starter run_agent() / _new_session() code in agent.py
- **Expected output:** A completed run_agent() that creates a session, parses the query with regex, calls all three tools in order, saves each result to the correct session key, returns early on empty search results or empty outfit, and returns the full session on success
- **How I will verify:** I will run `python agent.py` and check two paths. Happy path: query "looking for a vintage graphic tee under $30" with get_example_wardrobe() should set session["error"] to None and fill selected_item, outfit_suggestion, and fit_card. Error path: query "designer ballgown size XXS under $5" should set session["error"] to a helpful message and leave outfit_suggestion and fit_card as None. I will also read the code and confirm it matches every branch shown in the Architecture diagram.

---

## A Complete Interaction (Step by Step)

**Example user query:** "I'm looking for a vintage tee under $30. I mostly wear baggy jeans and chunky shoes. What's out there and how would I style it?"

**Step 1:**
First the planning loop parses the query and saves `session["parsed"]` = `{description: "vintage tee", size: None, max_price: 30.0}` and loads the wardrobe with `get_example_wardrobe()`. Then it calls `search_listings("vintage tee", None, 30.0)`. The tool uses load_listings(), filters out anything over $30, and scores listings by keyword match in title, description, and style_tags. It returns a list of listing dicts sorted best match first, like lst_033 Vintage Band Tee ($19, depop), lst_006 Graphic Tee bootleg ($24), and lst_002 Y2K Baby Tee ($18). The agent saves the full list to `session["search_results"]` and sets `session["selected_item"]` = `search_results[0]` (lst_033, the top match).

**Step 2:**
The agent calls `suggest_outfit(session["selected_item"], session["wardrobe"])`. The `new_item` input is the full lst_033 dict (id, title, description, category "tops", style_tags, size "L", condition "fair", price 19.0, colors, brand null, platform "depop"). The `wardrobe` input is the example wardrobe with items like w_001 baggy straight leg jeans and w_007 chunky white sneakers. The tool returns a string like: "Pair this faded band tee with your baggy straight leg jeans and chunky white sneakers. Tuck the front slightly and roll the sleeves once for a relaxed streetwear look." The agent saves that to `session["outfit_suggestion"]`.

**Step 3:**
The agent calls `create_fit_card(session["outfit_suggestion"], session["selected_item"])`. The `outfit` input is the styling string from step 2. The `new_item` input is the same lst_033 listing from step 1. The tool returns a caption string like: "found this faded band tee on depop for $19 and it goes perfect with my baggy jeans, full fit on my story." The agent saves that to `session["fit_card"]` and returns the session with `session["error"]` still None.

**Final output to user:**
The user sees one reply with three parts: (1) the listing found, Vintage Band Tee in faded grey for $19 on Depop, size L, fair condition, (2) the outfit suggestion naming their baggy jeans and chunky sneakers, and (3) the fit card caption ready to post. If step 1 had returned an empty list instead, the user would only see an error like "No listings matched your search for 'vintage tee' under $30. Try raising your budget to $40 or searching for 'graphic tee' instead." In that case selected_item, outfit_suggestion, and fit_card stay None and steps 2 and 3 do not run.
