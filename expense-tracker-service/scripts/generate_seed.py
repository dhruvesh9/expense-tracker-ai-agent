"""Generate scripts/seed.sql: random but realistic, fully populated dummy data.

The cast is a global consumer user base: 20-30 people across ten countries. Every row is
complete (no missing merchants, categories or payment methods) and internally consistent:

* people spend in their home currency at local price levels; foreign currency appears
  only on travel (flights, hotels, transfers)
* every purchase has a price range that fits it, and a plausible merchant for the
  person's country (food delivery, supermarkets, ride apps, mobile carriers ...)
* payment habits follow the country (UPI-style wallets in India, cards in the US, ...);
  online purchases are never paid in cash
* rent, utilities and subscriptions recur monthly with the same merchant, amount and day
* history length grows with the number of expenses; users join shortly before their first
  expense; records are never "created" before the expense date or in the future
* about three in four people set a monthly budget close to what they really spend
* wholesome categories only (food, transport, shopping, travel, ...)

Run:
    python scripts/generate_seed.py              # new random dataset
    python scripts/generate_seed.py --seed 42    # reproduce a dataset
    python scripts/generate_seed.py --users 25   # fixed number of people

Amounts are integer minor units (cents), exactly like the real API stores them.
"""

import argparse
import calendar
import random
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from people_data import pick_city, unique_person

NOW = datetime.now(UTC).replace(tzinfo=None)  # timestamps are stored as naive UTC
TODAY = NOW.date()

# country -> (weight, home currency, price level vs INR, first names, last names)
COUNTRIES = {
    # country: (weight, home currency, price level vs INR). Names and cities: scripts/people_data.py
    "IN": (36, "INR", 1.0),
    "US": (16, "USD", 0.045),
    "GB": (10, "GBP", 0.036),
    "DE": (8, "EUR", 0.040),
    "FR": (5, "EUR", 0.040),
    "AE": (7, "AED", 0.17),
    "SG": (7, "SGD", 0.058),
    "AU": (6, "AUD", 0.065),
    "CA": (5, "CAD", 0.060),
    "BR": (4, "BRL", 0.12),
}
PRICE_LEVEL = {cur: level for _w, cur, level in COUNTRIES.values()}

# How people pay, per country (weights): cash, credit_card, debit_card, bank_transfer, digital_wallet
PAYMENT_HABITS = {
    "IN": {
        "digital_wallet": 50,
        "credit_card": 20,
        "debit_card": 15,
        "cash": 12,
        "bank_transfer": 3,
    },
    "US": {
        "credit_card": 48,
        "debit_card": 28,
        "digital_wallet": 14,
        "cash": 6,
        "bank_transfer": 4,
    },
    "GB": {
        "debit_card": 42,
        "credit_card": 25,
        "digital_wallet": 25,
        "cash": 5,
        "bank_transfer": 3,
    },
    "DE": {
        "debit_card": 40,
        "cash": 20,
        "bank_transfer": 15,
        "digital_wallet": 15,
        "credit_card": 10,
    },
    "FR": {
        "debit_card": 52,
        "credit_card": 15,
        "digital_wallet": 15,
        "cash": 14,
        "bank_transfer": 4,
    },
    "AE": {
        "credit_card": 40,
        "debit_card": 25,
        "digital_wallet": 20,
        "cash": 12,
        "bank_transfer": 3,
    },
    "SG": {
        "credit_card": 35,
        "digital_wallet": 30,
        "debit_card": 25,
        "cash": 7,
        "bank_transfer": 3,
    },
    "AU": {
        "debit_card": 45,
        "credit_card": 25,
        "digital_wallet": 22,
        "cash": 5,
        "bank_transfer": 3,
    },
    "CA": {
        "credit_card": 42,
        "debit_card": 30,
        "digital_wallet": 18,
        "cash": 6,
        "bank_transfer": 4,
    },
    "BR": {
        "digital_wallet": 40,
        "credit_card": 28,
        "debit_card": 17,
        "cash": 8,
        "bank_transfer": 7,
    },
}
# Only small, in-person purchases can be paid in cash.
CASH_OK = {
    "Coffee",
    "Breakfast",
    "Lunch",
    "Lunch with friends",
    "Snacks",
    "Taxi fare",
    "Bus ticket",
    "Parking",
    "Fresh produce",
    "Milk and eggs",
    "Gift",
    "Metro top-up",
}

# --- merchants: either a list, or {country: list, "*": default list} -----------------------
GROCER = {
    "IN": ["BigBasket", "DMart", "Local grocer"],
    "US": ["Walmart", "Kroger", "Whole Foods", "Costco"],
    "GB": ["Tesco", "Sainsbury's", "Aldi"],
    "DE": ["Aldi", "Lidl", "REWE"],
    "FR": ["Carrefour", "Leclerc", "Monoprix"],
    "AE": ["Carrefour", "Lulu Hypermarket"],
    "SG": ["FairPrice", "Cold Storage"],
    "AU": ["Woolworths", "Coles", "Aldi"],
    "CA": ["Loblaws", "Costco", "Metro"],
    "BR": ["Pão de Açúcar", "Carrefour"],
    "*": ["Local supermarket"],
}
RIDE = {
    "IN": ["Uber", "Ola"],
    "US": ["Uber", "Lyft", "Yellow Cab"],
    "SG": ["Grab", "Gojek"],
    "GB": ["Uber", "Bolt", "Local taxi"],
    "DE": ["Uber", "Bolt", "Local taxi"],
    "FR": ["Uber", "Bolt", "Local taxi"],
    "BR": ["Uber", "99"],
    "AU": ["Uber", "DiDi"],
    "*": ["Uber"],
}
DELIVERY = {
    "IN": ["Swiggy", "Zomato"],
    "US": ["DoorDash", "Uber Eats"],
    "CA": ["DoorDash", "Uber Eats"],
    "AE": ["Talabat", "Deliveroo"],
    "SG": ["GrabFood", "foodpanda"],
    "BR": ["iFood", "Uber Eats"],
    "*": ["Deliveroo", "Uber Eats"],
}
MERCHANTS = {
    "Coffee": ["Starbucks", "Costa Coffee", "Local café"],
    "Breakfast": ["Local bakery", "Local café"],
    "Lunch": ["Subway", "Local restaurant", "Food court", "Local café"],
    "Lunch with friends": ["Local restaurant", "Food court"],
    "Food delivery": DELIVERY,
    "Dinner out": ["Local restaurant", "Domino's", "Pizza Hut"],
    "Celebration dinner": ["Local restaurant"],
    "Snacks": ["7-Eleven", "Local store", "Convenience store"],
    "Weekly groceries": GROCER,
    "Fresh produce": GROCER,
    "Milk and eggs": GROCER,
    "Household supplies": GROCER,
    "Online grocery order": {
        "IN": ["BigBasket", "Blinkit"],
        "US": ["Instacart", "Amazon Fresh"],
        "GB": ["Ocado", "Tesco"],
        "*": ["Amazon Fresh"],
    },
    "Taxi fare": RIDE,
    "Ride share": RIDE,
    "Metro top-up": {
        "GB": ["Transport for London"],
        "FR": ["RATP"],
        "DE": ["BVG"],
        "SG": ["EZ-Link"],
        "IN": ["Metro Card"],
        "*": ["City Metro"],
    },
    "Fuel": {
        "IN": ["Indian Oil", "Shell"],
        "US": ["Shell", "Chevron", "Exxon"],
        "*": ["Shell", "BP"],
    },
    "Parking": ["City Parking"],
    "Bus ticket": ["City Bus"],
    "Movie tickets": {
        "IN": ["PVR Cinemas", "INOX"],
        "US": ["AMC Theatres", "Regal"],
        "GB": ["Odeon", "Vue"],
        "*": ["Local cinema"],
    },
    "Concert tickets": {"IN": ["BookMyShow"], "*": ["Ticketmaster"]},
    "Sports event": ["Ticketmaster", "Stadium box office"],
    "Video game": ["Steam", "PlayStation Store", "Nintendo eShop"],
    "Books and magazines": ["Amazon", "Local bookstore", "Kindle Store"],
    "Museum entry": ["City Museum"],
    "T-shirt": ["Uniqlo", "H&M", "Zara"],
    "Shoes": ["Nike", "Adidas", "Puma"],
    "Headphones": ["Amazon", "Local electronics store"],
    "Backpack": ["Decathlon", "Amazon"],
    "Home decor": ["IKEA", "Local home store"],
    "Gift": ["Amazon", "Local gift shop"],
    "Sunglasses": ["Local optician", "Amazon"],
    "Phone accessories": ["Amazon", "Local electronics store"],
    "Yoga class": ["Local yoga studio"],
    "Fitness gear": ["Decathlon", "Amazon"],
    "Swimming pass": ["City Leisure Centre"],
    "Sports club fee": ["Local sports club"],
    "Train tickets": {
        "IN": ["IRCTC"],
        "GB": ["Trainline"],
        "DE": ["Deutsche Bahn"],
        "FR": ["SNCF"],
        "US": ["Amtrak"],
        "*": ["Rail operator"],
    },
    "Flight booking": ["Airline direct", "Expedia", "Skyscanner"],
    "Hotel stay": ["Booking.com", "Airbnb", "Marriott"],
    "Airport transfer": ["Uber", "Airport taxi"],
    "Weekend trip": ["Airbnb", "Booking.com", "Local tour operator"],
    "Online course": ["Coursera", "Udemy", "LinkedIn Learning"],
    "Textbooks": ["Amazon", "Local bookstore"],
    "Workshop fee": ["Eventbrite"],
    "Certification exam": ["Exam board"],
    "Language class": ["Local language school", "Preply"],
}

# One-off purchases: category -> [(description, low, high, weight)] with prices in INR terms;
# they are converted to the person's currency with PRICE_LEVEL.
ITEMS = {
    "food": [
        ("Coffee", 120, 450, 3),
        ("Breakfast", 150, 500, 2),
        ("Lunch", 250, 900, 6),
        ("Lunch with friends", 600, 2500, 2),
        ("Food delivery", 250, 1200, 4),
        ("Dinner out", 600, 2500, 3),
        ("Celebration dinner", 1800, 6000, 1),
        ("Snacks", 60, 350, 2),
    ],
    "groceries": [
        ("Weekly groceries", 1200, 4500, 5),
        ("Fresh produce", 200, 900, 3),
        ("Milk and eggs", 120, 450, 2),
        ("Household supplies", 400, 2200, 2),
        ("Online grocery order", 800, 3500, 3),
    ],
    "transport": [
        ("Taxi fare", 120, 900, 5),
        ("Ride share", 100, 700, 5),
        ("Metro top-up", 200, 1000, 3),
        ("Fuel", 800, 3500, 3),
        ("Parking", 50, 400, 2),
        ("Bus ticket", 30, 300, 2),
    ],
    "entertainment": [
        ("Movie tickets", 300, 1400, 3),
        ("Concert tickets", 1500, 8000, 1),
        ("Sports event", 800, 4000, 1),
        ("Video game", 500, 3500, 1),
        ("Books and magazines", 250, 1500, 2),
        ("Museum entry", 200, 1200, 1),
    ],
    "shopping": [
        ("T-shirt", 500, 2500, 3),
        ("Shoes", 1800, 9000, 2),
        ("Headphones", 1500, 14000, 1),
        ("Backpack", 1200, 5000, 1),
        ("Home decor", 600, 6000, 2),
        ("Gift", 500, 5000, 3),
        ("Sunglasses", 800, 6000, 1),
        ("Phone accessories", 300, 2500, 2),
    ],
    "wellness": [
        ("Yoga class", 400, 1500, 3),
        ("Fitness gear", 600, 5000, 2),
        ("Swimming pass", 500, 2500, 1),
        ("Sports club fee", 1000, 5000, 1),
    ],
    "travel": [
        ("Train tickets", 400, 3500, 3),
        ("Flight booking", 4000, 45000, 2),
        ("Hotel stay", 3500, 30000, 2),
        ("Airport transfer", 600, 3000, 2),
        ("Weekend trip", 8000, 40000, 1),
    ],
    "education": [
        ("Online course", 1500, 8000, 3),
        ("Textbooks", 600, 5000, 2),
        ("Workshop fee", 2000, 12000, 1),
        ("Certification exam", 3000, 15000, 1),
        ("Language class", 1000, 6000, 1),
    ],
}
FOREIGN_TRAVEL_ITEMS = {"Flight booking", "Hotel stay", "Airport transfer", "Weekend trip"}

# Monthly recurring items: (description, category, low, high, chance, varies, merchants, payment choices)
BILL_PAY = ["debit_card", "bank_transfer", "digital_wallet"]
SUB_PAY = ["credit_card", "debit_card", "digital_wallet"]
CARRIERS = {
    "IN": ["Jio", "Airtel"],
    "US": ["Verizon", "T-Mobile", "AT&T"],
    "GB": ["Vodafone", "EE", "O2"],
    "DE": ["Telekom", "Vodafone"],
    "FR": ["Orange", "SFR"],
    "AE": ["Etisalat", "du"],
    "SG": ["Singtel", "StarHub"],
    "AU": ["Telstra", "Optus"],
    "CA": ["Rogers", "Bell"],
    "BR": ["Vivo", "Claro"],
    "*": ["Mobile carrier"],
}
RECURRING = [
    ("Monthly rent", "rent", 12000, 40000, 0.75, False, ["Landlord"], ["bank_transfer"]),
    ("Mobile plan", "bills", 300, 1200, 1.00, False, CARRIERS, BILL_PAY),
    ("Electricity bill", "bills", 600, 3500, 0.65, True, ["Electricity provider"], BILL_PAY),
    ("Broadband", "bills", 600, 2000, 0.70, False, ["Broadband provider"], BILL_PAY),
    (
        "Streaming subscription",
        "entertainment",
        150,
        800,
        0.60,
        False,
        ["Netflix", "Spotify", "Disney+", "YouTube Premium", "Amazon Prime"],
        SUB_PAY,
    ),
    ("Gym membership", "wellness", 800, 3500, 0.35, False, ["Local gym", "City Fitness"], SUB_PAY),
]

# personality -> (weights for one-off categories, spending multiplier, chance of renting)
PERSONAS = {
    "foodie": (
        {
            "food": 48,
            "groceries": 15,
            "entertainment": 10,
            "transport": 12,
            "shopping": 8,
            "wellness": 4,
            "travel": 2,
            "education": 1,
        },
        1.0,
        0.75,
    ),
    "commuter": (
        {
            "transport": 42,
            "food": 22,
            "groceries": 12,
            "shopping": 8,
            "entertainment": 6,
            "wellness": 5,
            "travel": 3,
            "education": 2,
        },
        0.8,
        0.75,
    ),
    "shopaholic": (
        {
            "shopping": 42,
            "food": 17,
            "entertainment": 13,
            "transport": 9,
            "groceries": 7,
            "wellness": 5,
            "travel": 6,
            "education": 1,
        },
        1.5,
        0.75,
    ),
    "globetrotter": (
        {
            "travel": 28,
            "food": 22,
            "transport": 16,
            "entertainment": 11,
            "shopping": 11,
            "groceries": 5,
            "wellness": 4,
            "education": 3,
        },
        1.3,
        0.8,
    ),
    "saver": (
        {
            "groceries": 32,
            "transport": 18,
            "food": 18,
            "wellness": 9,
            "education": 8,
            "shopping": 4,
            "entertainment": 3,
            "travel": 1,
        },
        0.6,
        0.7,
    ),
    "student": (
        {
            "food": 34,
            "education": 22,
            "transport": 17,
            "entertainment": 15,
            "shopping": 8,
            "groceries": 4,
        },
        0.5,
        0.2,
    ),
    "family-head": (
        {
            "groceries": 34,
            "food": 14,
            "wellness": 10,
            "education": 10,
            "transport": 10,
            "shopping": 8,
            "entertainment": 4,
            "travel": 3,
        },
        1.4,
        0.85,
    ),
}


def q(text: str | None) -> str:
    return "NULL" if text is None else "'" + text.replace("'", "''") + "'"


def tidy_price(rng: random.Random, base_inr: float, currency: str) -> int:
    """Convert a price in INR terms to a tidy amount in `currency`; returns minor units.

    Shared with scripts/generate_load_data.py so both generators price things the same way.
    """
    value = base_inr * PRICE_LEVEL[currency]
    if currency == "INR":
        step = 10 if value < 1000 else 50
        major = max(10, round(value / step) * step)
        cents = 50 if (major < 500 and rng.random() < 0.1) else 0
    else:
        major = max(2, round(value / 5) * 5 if value >= 100 else round(value))
        roll = rng.random()
        cents = 0 if roll < 0.55 else 50 if roll < 0.70 else 99  # whole / half / x.99
        if cents == 99:
            major -= 1
    return major * 100 + cents


# (methods, cumulative weights) per (country, cash allowed): built once for speed.
PAYMENT_TABLES = {}
for _country, _habits in PAYMENT_HABITS.items():
    for _cash in (True, False):
        _usable = {m: w for m, w in _habits.items() if _cash or m != "cash"}
        _methods = list(_usable)
        _cum, _total = [], 0
        for _m in _methods:
            _total += _usable[_m]
            _cum.append(_total)
        PAYMENT_TABLES[(_country, _cash)] = (_methods, _cum)


def pick_payment(rng: random.Random, description: str, country: str) -> str:
    """Payment method following the country's habits; online items are never paid in cash."""
    methods, cum = PAYMENT_TABLES[(country, description in CASH_OK)]
    return rng.choices(methods, cum_weights=cum)[0]


def pick_local(rng: random.Random, options, country: str) -> str:
    """Choose from a list, or from the country's list in a {country: [...], '*': [...]} dict."""
    if isinstance(options, dict):
        options = options.get(country, options["*"])
    return rng.choice(options)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=None, help="reproduce a previous dataset")
    parser.add_argument(
        "--users", type=int, default=None, help="number of people (default: random 20-30)"
    )
    parser.add_argument(
        "--max-expenses", type=int, default=500, help="max expenses per person (default 500)"
    )
    args = parser.parse_args()

    seed = args.seed if args.seed is not None else random.randrange(1_000_000)
    rng = random.Random(seed)
    n_users = args.users or rng.randint(20, 30)

    def stamp(day: date, extra_days: int = 0) -> str:
        """A UTC timestamp on `day` (+extra days), never later than 'now'."""
        moment = datetime.combine(
            day + timedelta(days=extra_days), datetime.min.time()
        ) + timedelta(
            hours=rng.randint(7, 22), minutes=rng.randint(0, 59), seconds=rng.randint(0, 59)
        )
        if moment > NOW:
            earliest = datetime.combine(day, datetime.min.time())
            moment = max(earliest, NOW - timedelta(minutes=rng.randint(1, 120)))
        return moment.strftime("%Y-%m-%d %H:%M:%S.000000")

    def price(base_inr: float, currency: str) -> int:
        return tidy_price(rng, base_inr, currency)

    def payment_for(description: str, country: str) -> str:
        return pick_payment(rng, description, country)

    # ---- people: unique names, each with a home country
    codes = list(COUNTRIES)
    code_weights = [COUNTRIES[c][0] for c in codes]
    people, taken = [], set()
    while len(people) < n_users:
        country = rng.choices(codes, code_weights)[0]
        people.append((unique_person(rng, country, taken), country, pick_city(rng, country)))

    lines = [
        f"-- Generated by scripts/generate_seed.py (seed={seed}). For a freshly migrated DB.",
        "BEGIN;",
    ]
    cast, total_rows = [], 0

    for user_id, (name, country, city) in enumerate(people, start=1):
        home = COUNTRIES[country][1]
        persona = rng.choice(list(PERSONAS))
        weights, spend_factor, rent_chance = PERSONAS[persona]
        spend_factor *= rng.uniform(0.8, 1.25)  # individual quirk
        count = rng.randint(min(10, args.max_expenses), args.max_expenses)
        travels_abroad = persona == "globetrotter" or rng.random() < 0.2

        # history grows with activity: 10 expenses ~ 45 days, 170+ expenses ~ a full year
        span_days = max(45, min(365, int(count * 2.2)))
        span_start = TODAY - timedelta(days=span_days)

        rows = []  # (date, entered_extra_days, amount_minor, currency, description, category, merchant, payment, recurring)

        # recurring monthly items, capped to ~40% of this person's expenses
        recurring_rows = []
        for description, category, low, high, chance, varies, merchants, payments in RECURRING:
            if description == "Monthly rent":
                chance = rent_chance
            if rng.random() > chance:
                continue
            base = rng.randint(low, high)
            day = rng.randint(1, 28)
            merchant = pick_local(rng, merchants, country)  # same provider every month
            payment = rng.choice(payments)  # same way of paying every month
            fixed_amount = price(base, home)  # same every month unless the item "varies"
            item_rows = []
            year, month = span_start.year, span_start.month
            while date(year, month, 1) <= TODAY:
                due = date(year, month, min(day, calendar.monthrange(year, month)[1]))
                if span_start <= due <= TODAY:
                    amount = price(base * rng.uniform(0.8, 1.25), home) if varies else fixed_amount
                    item_rows.append(
                        (due, 0, amount, home, description, category, merchant, payment, 1)
                    )
                year, month = (year + 1, 1) if month == 12 else (year, month + 1)
            if len(recurring_rows) + len(item_rows) <= count * 0.4:
                recurring_rows += item_rows
        rows += recurring_rows

        # one-off purchases fill the rest
        categories = list(weights)
        for _ in range(count - len(rows)):
            category = rng.choices(categories, [weights[c] for c in categories])[0]
            catalog = ITEMS[category]
            description, low, high, _w = rng.choices(catalog, [item[3] for item in catalog])[0]
            currency = home
            if (
                category == "travel"
                and travels_abroad
                and description in FOREIGN_TRAVEL_ITEMS
                and rng.random() < 0.5
            ):
                currency = rng.choice([c for c in PRICE_LEVEL if c != home])
            amount = price(rng.randint(low, high) * spend_factor, currency)
            when = TODAY - timedelta(days=rng.randint(0, span_days))
            merchant = pick_local(rng, MERCHANTS[description], country)
            rows.append(
                (
                    when,
                    rng.choice([0, 0, 0, 1, 2]),
                    amount,
                    currency,
                    description,
                    category,
                    merchant,
                    payment_for(description, country),
                    0,
                )
            )

        # ~3 in 4 people set a budget near their real average monthly spend (home currency only)
        budget_minor = "NULL"
        if rng.random() < 0.75:
            home_total = sum(r[2] for r in rows if r[3] == home)
            monthly = home_total / (span_days / 30.4)
            step = 500 if home == "INR" else 50
            budget_major = max(step, round(monthly * rng.uniform(0.85, 1.2) / 100 / step) * step)
            budget_minor = str(budget_major * 100)

        joined = stamp(span_start, -rng.randint(5, 60))
        lines.append(
            "INSERT INTO users (id, name, country, city, default_currency, monthly_budget_minor, created_at, updated_at) "
            f"VALUES ({user_id}, {q(name)}, {q(country)}, {q(city)}, {q(home)}, {budget_minor}, '{joined}', '{joined}');"
        )
        for (
            when,
            later,
            amount,
            currency,
            description,
            category,
            merchant,
            payment,
            recurring,
        ) in sorted(rows, key=lambda r: r[0]):
            created = stamp(when, later)
            lines.append(
                "INSERT INTO expenses (user_id, amount_minor, currency, description, category, merchant, "
                "payment_method, is_recurring, expense_date, created_at, updated_at) "
                f"VALUES ({user_id}, {amount}, '{currency}', {q(description)}, {q(category)}, {q(merchant)}, "
                f"{q(payment)}, {recurring}, '{when.isoformat()}', '{created}', '{created}');"
            )
        cast.append((user_id, name, country, persona, budget_minor, len(rows)))
        total_rows += len(rows)

    lines.append("COMMIT;")
    out = Path(__file__).with_name("seed.sql")
    out.write_text("\n".join(lines) + "\n")

    print(f"seed={seed}  ->  {out}\n{n_users} users, {total_rows} expenses\n")
    for user_id, name, country, persona, budget, count in cast:
        budget_text = (
            f"budget {int(budget) / 100:>9,.0f}" if budget != "NULL" else "no budget        "
        )
        print(
            f"  {user_id:>2}  {name:<20} {country}  {persona:<13} {budget_text}  {count:>3} expenses"
        )


if __name__ == "__main__":
    main()
