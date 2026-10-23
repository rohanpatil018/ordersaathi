# 🧁 OrderSaathi — turn messy WhatsApp orders into a clean daily plan

> **Small Business Workflow Challenge submission**
> One user: a home baker / tiffin seller who takes orders on WhatsApp.
> One recurring task: turning a day of messy order chats into a prep list, a delivery sheet and the follow-up messages.

| | |
|---|---|
| **Live demo** | [ADD YOUR RENDER URL HERE] |
| **Video walkthrough** | [ADD YOUR VIDEO LINK HERE] |
| **GitHub repository** | https://github.com/rohanpatil018/ordersaathi |
| **Built by** | Rohan Patil |

> The demo may take up to a minute to wake up on the first visit (free hosting tier).

---

## Project summary

### Who it helps
Home bakers, tiffin services and small boutique sellers in India who take most of their orders through WhatsApp chats. They have no order system. Everything lives in the chat.

### The problem
Orders arrive as casual messages, in English and Hinglish, with typos and changes of mind:

```
[10:12] Asha: Hi! I need 2 chocolate cakes 1kg each for Saturday evening.
[11:03] Rahul: bhaiya 6 samosa extra kal morning
[11:10] Asha: actually make it 3 cakes, not 2.
[13:40] Nisha: 10 samosa for sat morning, actually 12. and also 1kg choco cake (if possible).
```

At the end of the day the baker has to scroll back through the chat to work out how much to bake, where to deliver and when, who has paid, and which customers still need to be asked something. Mistakes here mean a missed order, a wrong quantity or an unpaid delivery.

### What OrderSaathi does
Paste (or upload) the chat and get, in one screen:

1. **A clean order table** with one row per item: customer, item, quantity, date, time slot, payment status.
2. **Review flags**: anything uncertain (no date, "if possible", missing quantity) is marked *Needs review* instead of being silently guessed. Quantity corrections ("actually make it 3") are applied and shown as *Updated (2 → 3)*.
3. **A prep list** with the total of each item to make per day.
4. **A delivery sheet** sorted by date and time slot.
5. **Ready-to-send messages**: *Confirm order* for unclear orders and *Payment due* for unpaid ones, each with an "Open in WhatsApp" button.
6. **Export** as a print/PDF view or a CSV of the delivery sheet.

The baker can edit any row, press **Mark OK**, and everything below updates live.


## Screenshots

### 1. Main Dashboard
![OrderSaathi main dashboard](screenshots/01-home.png)

### 2. Extracted Orders
![Extracted orders and review flags](screenshots/02-extracted-orders.png)

### 3. Prep List and Delivery Sheet
![Prep list and delivery sheet](screenshots/03-prep-delivery.png)

### 4. Reminders and Export
![WhatsApp reminders and export options](screenshots/04-reminders-export.png)


### What I would improve next
- Connect the WhatsApp Business API so orders arrive without any copy-paste.
- Accept a screenshot of a chat (Gemini can read images) as an input.
- An in-app price list editor and customer phone book, so messages go straight to the right contact.
- Hindi/Marathi (Devanagari) message support and more regional phrases.
- Optional saved order history with explicit consent, plus weekly sales and repeat-customer summaries.

---

## How it works

```
Pasted chat ──► Gemini (JSON-schema extraction) ──► normalize + validate (plain Python) ──► editable table
                     │ if unavailable / fails                                                   │
                     └──► offline rule-based parser ──────────────────────────────────────────►│
                                                                                                ▼
                                                      prep list · delivery sheet · reminders · CSV/print
```

**Design decisions**

- **The LLM only extracts raw facts** (who, what, how many, the customer's own date words, payment words). It never does date math.
- **Plain Python does the rest**: it turns "kal", "Sat" and "sunday" into real dates using a *chat date* the user can set, resolves time slots, merges item names, and assigns the review flags. This keeps the output predictable and testable.
- **Structured output**: Gemini is called with a Pydantic schema, and the response is validated before use.
- **Graceful fallback**: if Gemini is unavailable, errors or returns nothing, an offline rule-based parser handles the chat and the UI shows a visible warning. The app keeps working.
- **Human in the loop**: nothing is trusted blindly. Uncertain rows are highlighted and the baker confirms them.

---

## Tech stack

- **Backend:** Python, FastAPI, Pydantic
- **AI:** Google Gemini API (`google-genai` SDK) with JSON-schema structured output
- **Frontend:** a single HTML page with vanilla JavaScript and Tailwind (CDN), mobile-friendly
- **Tests:** pytest

## Project structure

```
ordersaathi/
├── app/
│   ├── main.py            # FastAPI routes + serves the frontend
│   ├── schemas.py         # Pydantic models (Gemini schema + app models)
│   ├── prompts.py         # extraction prompt
│   ├── extractor/
│   │   ├── llm.py         # Gemini call with structured output
│   │   ├── rules.py       # offline rule-based fallback parser
│   │   ├── normalize.py   # dates, time slots, item names, review flags
│   │   └── pipeline.py    # Gemini first, rules as fallback
│   ├── aggregate.py       # prep list, delivery sheet, summary
│   └── messages.py        # reminder messages + wa.me links
├── static/index.html      # the UI
├── data/
│   ├── sample_chat.txt    # synthetic sample chat
│   └── price_list.json    # example prices
├── tests/
└── requirements.txt
```

## API

| Endpoint | Purpose |
|---|---|
| `GET /api/sample` | Returns the synthetic sample chat |
| `POST /api/extract` | `{chat_text, reference_date, seller_name}` → order rows, engine used, optional warning |
| `POST /api/plan` | `{lines}` → summary, prep list, delivery sheet, reminder messages |

Interactive docs are available at `/docs` when the server is running.

---

## Run it locally

Requires Python 3.10+ and a Gemini API key from [Google AI Studio](https://aistudio.google.com/).

```bash
git clone https://github.com/rohanpatil018/ordersaathi.git
cd ordersaathi
python -m venv venv
# Windows: .\venv\Scripts\Activate.ps1      macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-2.5-flash
```

If the model name is unavailable for your key, pick a current Flash model in AI Studio and update `GEMINI_MODEL`.

Start the app:

```bash
python -m uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000, click **Load sample chat**, then **Extract orders**.

**Offline mode** (no API key, uses the rule-based parser only): set `USE_GEMINI=0` before starting.

**Run the tests:**

```bash
python -m pytest -q
```

---

## Testing

- `tests/` runs the extraction pipeline on the sample chat in offline mode and checks quantities, corrections, dates, time slots, payment types, review flags and prep-list totals.
- The app was also tried with inputs that should not crash it: an empty chat, gibberish, and an invalid API key (the UI shows an error or the offline-mode banner).

## Privacy

- **Only synthetic data is used.** The sample chats contain made-up names and no phone numbers or addresses. Please do not paste real customer chats into the public demo.
- **The app has no database and stores nothing.** Chats and orders live in your browser tab and are gone when you close it.
- When Gemini mode is on, the pasted chat text is sent to the Gemini API for extraction. Offline mode (`USE_GEMINI=0`) keeps everything on your machine.
- WhatsApp message buttons open `wa.me` with the text pre-filled and let the user choose the contact, so no phone numbers are collected.

## Limitations

- Item names in the offline fallback come from a small built-in menu list (cakes, cupcakes, samosa, cookies, brownies and similar). Gemini mode handles any item.
- "kal" is treated as tomorrow relative to the chat date set in the app, so set that date correctly.
- Tested with English and Hinglish in Latin script. Devanagari text is not yet covered.
- Prices come from `data/price_list.json`, and items without a price are listed so the user can add them.
- Free-tier Gemini quotas and free hosting limits apply to the demo.

---

## How this maps to the judging criteria

| Criterion | How OrderSaathi addresses it |
|---|---|
| **Impact and usefulness (25)** | Replaces the daily job of scrolling through chats to build a bake list, delivery run and payment follow-ups for a real, common small business user. |
| **Completeness and functionality (30)** | The whole workflow runs from paste/upload to prep list, delivery sheet, messages and export, with editing in between. |
| **Technical execution (20)** | Schema-validated LLM output, deterministic date and flag logic, offline fallback, a typed API and automated tests. |
| **User experience (25)** | A single mobile-friendly page, uncertain rows highlighted instead of guessed, one-click Mark OK, live updates, and a visible privacy note. |

---

*Built for the Small Business Workflow Challenge. Uses synthetic sample data only.*
