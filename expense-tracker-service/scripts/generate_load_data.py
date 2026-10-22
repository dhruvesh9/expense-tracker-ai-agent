"""Generate a LARGE, realistic dataset for load testing: tens of thousands of users and
millions of expenses, modelled on a product with ~10,000 daily active users.

Unlike scripts/generate_seed.py (a small .sql file), this writes straight into the SQLite
database in bulk, because a millions-of-rows .sql file would be slow and huge.

How the simulation works (day by day over the chosen window):

* Users sign up over time (more recently than long ago); ids are assigned in signup order.
* Each user has an "activity propensity" (heavy-tailed: a few power users, many casual ones).
* Each day roughly `--dau` users are active (weekends a little busier; mild growth over the
  window). Active users are sampled by propensity from everyone signed up so far, and each
  logs 1-6 expenses that day.
* Every expense uses the same catalogs as the small seed: items with sensible prices, a
  merchant that fits the person's country, country-specific payment habits, home currency
  with occasional foreign travel spending.
* About 55% of users also track recurring items (rent, phone, broadband ...) monthly.
* Afterwards ~70% of users get a monthly budget close to what they really spend.

Usage (database must already be migrated: `make migrate`):

    python scripts/generate_load_data.py                       # defaults: 25k users, 180 days, 5k DAU
    python scripts/generate_load_data.py --users 20000 --days 90 --dau 4000
    python scripts/generate_load_data.py --seed 7 --wipe       # reproducible; replaces existing rows
    python scripts/generate_load_data.py --db /tmp/load.db --wipe

The generator refuses to run on a non-empty database unless --wipe is given.
"""

import argparse
import atexit
import bisect
import calendar
import os
import random
import sqlite3
import sys
import time
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))  # so `app` is importable
import generate_seed as g  # noqa: E402  (shared catalogs: countries, items, merchants, ...)
from people_data import pick_city, unique_person  # noqa: E402
from sqlalchemy.dialects import sqlite as sqlite_dialect  # noqa: E402
from sqlalchemy.schema import CreateIndex  # noqa: E402

from app.models import Expense  # noqa: E402

BATCH = 100_000


def default_db_path() -> str:
    url = os.environ.get("DATABASE_URL", "sqlite:///./data/expense_tracker.db")
    return url.removeprefix("sqlite:///")


def cumulative(weights) -> list[float]:
    total, out = 0.0, []
    for w in weights:
        total += w
        out.append(total)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--db", default=default_db_path(), help="SQLite file (default: DATABASE_URL / dev DB)"
    )
    parser.add_argument(
        "--users", type=int, default=25_000, help="registered users (default 25,000)"
    )
    parser.add_argument("--days", type=int, default=180, help="days of history (default 180)")
    parser.add_argument(
        "--dau", type=int, default=5_000, help="target daily active users (default 5,000)"
    )
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument(
        "--wipe", action="store_true", help="delete existing users and expenses first"
    )
    args = parser.parse_args()

    seed = args.seed if args.seed is not None else random.randrange(1_000_000)
    rng = random.Random(seed)
    started = time.time()
    now = datetime.now(UTC).replace(tzinfo=None)
    today = now.date()
    window_start = today - timedelta(days=args.days - 1)

    conn = sqlite3.connect(args.db)
    conn.execute("PRAGMA journal_mode=OFF")  # bulk load: no rollback journal needed
    conn.execute("PRAGMA synchronous=OFF")
    conn.execute("PRAGMA cache_size=-400000")  # ~400 MB page cache
    conn.execute("PRAGMA temp_store=MEMORY")

    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if not {"users", "expenses"} <= tables:
        sys.exit(f"{args.db} has no users/expenses tables. Run `make migrate` first.")
    existing = conn.execute(
        "SELECT (SELECT COUNT(*) FROM users), (SELECT COUNT(*) FROM expenses)"
    ).fetchone()
    if any(existing):
        if not args.wipe:
            sys.exit(
                f"{args.db} already has {existing[0]:,} users and {existing[1]:,} expenses. Use --wipe to replace them."
            )
        print("wiping existing rows...")
        conn.execute("DELETE FROM expenses")
        conn.execute("DELETE FROM users")
        conn.commit()

    # Inserting millions of rows is far faster without indexes: drop them, rebuild at the end.
    # The definitions come from the MODELS (not from whatever the database currently has), and
    # an atexit hook rebuilds them even if this script crashes half-way: a database must never
    # be left without its indexes (queries would silently turn into full table scans).
    index_ddl = {
        i.name: str(
            CreateIndex(i, if_not_exists=True).compile(dialect=sqlite_dialect.dialect())
        ).strip()
        for i in Expense.__table__.indexes
    }
    rebuilt = {"done": False}

    def rebuild_indexes() -> None:
        if rebuilt["done"]:
            return
        rebuilt["done"] = True
        for name, ddl in index_ddl.items():
            t = time.time()
            conn.execute(ddl)
            print(f"  index {name} rebuilt ({time.time() - t:.1f}s)")
        conn.execute("ANALYZE")
        conn.commit()

    atexit.register(rebuild_indexes)
    for name in index_ddl:
        conn.execute(f'DROP INDEX IF EXISTS "{name}"')

    # ------------------------------------------------------------------ catalogs (precomputed)
    country_codes = list(g.COUNTRIES)
    country_cum = cumulative([g.COUNTRIES[c][0] for c in country_codes])
    persona_names = list(g.PERSONAS)
    persona_tables = {}
    for name, (weights, factor, rent_chance) in g.PERSONAS.items():
        cats = [c for c in weights if weights[c] > 0]
        persona_tables[name] = (cats, cumulative([weights[c] for c in cats]), factor, rent_chance)
    item_tables = {
        cat: (
            [i[0] for i in items],
            cumulative([i[3] for i in items]),
            {i[0]: (i[1], i[2]) for i in items},
        )
        for cat, items in g.ITEMS.items()
    }
    other_currencies = {c: [x for x in g.PRICE_LEVEL if x != c] for c in g.PRICE_LEVEL}

    # ------------------------------------------------------------------ users
    n_users = args.users
    window = args.days + 150  # some users signed up before the window
    raw = []
    for _ in range(n_users):
        fraction = rng.random() ** 0.7  # skew towards recent signups
        raw.append(int(fraction * window) - 150)  # days relative to window_start
    raw.sort()

    users = []  # tuples: (country, currency, persona, spend_factor, travels, has_recurring, signup_offset)
    user_rows = []
    taken_names: set[str] = set()
    for i, offset in enumerate(raw, start=1):
        country = rng.choices(country_codes, cum_weights=country_cum)[0]
        name = unique_person(rng, country, taken_names)
        city = pick_city(rng, country)
        currency = g.COUNTRIES[country][1]
        persona = rng.choice(persona_names)
        factor = persona_tables[persona][2] * rng.uniform(0.8, 1.25)
        travels = persona == "globetrotter" or rng.random() < 0.2
        recurring = rng.random() < 0.55
        users.append((country, currency, persona, factor, travels, recurring, offset))
        signup_day = window_start + timedelta(days=offset)
        stamp = datetime.combine(signup_day, datetime.min.time()) + timedelta(
            seconds=rng.randint(0, 86399)
        )
        stamp = min(stamp, now - timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S.000000")
        user_rows.append((i, name, country, city, currency, None, stamp, stamp))
    conn.executemany(
        "INSERT INTO users (id, name, country, city, default_currency, monthly_budget_minor, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?)",
        user_rows,
    )
    conn.commit()
    print(f"{n_users:,} users inserted ({time.time() - started:.1f}s)")

    # Activity propensity: heavy tailed (a few power users, many casual ones).
    propensity = [min(rng.paretovariate(1.6), 40.0) for _ in range(n_users)]
    propensity_cum = cumulative(propensity)

    # ------------------------------------------------------------------ expense generation
    insert_sql = (
        "INSERT INTO expenses (user_id, amount_minor, currency, description, category, merchant, "
        "payment_method, is_recurring, expense_date, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)"
    )
    batch: list[tuple] = []
    total_rows = 0
    choices, randint, uniform, rand = rng.choices, rng.randint, rng.uniform, rng.random
    tidy_price, pick_payment, pick_local = g.tidy_price, g.pick_payment, g.pick_local
    merchants = g.MERCHANTS
    foreign_items = g.FOREIGN_TRAVEL_ITEMS
    count_choices = [1, 2, 3, 4, 5, 6]
    count_cum = cumulative([35, 28, 18, 10, 6, 3])
    day_iso = [(window_start + timedelta(days=d)).isoformat() for d in range(args.days)]
    max_hour_today = max(0, now.hour - 1)

    def flush() -> None:
        nonlocal batch, total_rows
        conn.executemany(insert_sql, batch)
        total_rows += len(batch)
        batch = []

    def stamp_for(day_index: int, extra: int) -> str:
        """created_at: usually that day, sometimes entered a day or two later; never in the future."""
        target = day_index + extra
        if target >= args.days:
            target, extra = day_index, 0
        hour = randint(7, 22)
        if target == args.days - 1:  # today: stay before "now"
            hour = randint(0, max_hour_today)
        return f"{day_iso[target]} {hour:02d}:{randint(0, 59):02d}:{randint(0, 59):02d}.000000"

    for d in range(args.days):
        weekday = (window_start + timedelta(days=d)).weekday()
        weekend_boost = 1.12 if weekday >= 5 else 1.0
        growth = 0.8 + 0.2 * (d / max(1, args.days - 1))  # mild growth towards the target
        target = int(args.dau * weekend_boost * growth)
        signed_up = bisect.bisect_right(raw, d)  # users with signup_offset <= d (ids 1..signed_up)
        if signed_up == 0:
            continue
        target = min(target, int(signed_up * 0.9))
        draws = choices(
            range(signed_up), cum_weights=propensity_cum[:signed_up], k=int(target * 1.2)
        )
        active = list(dict.fromkeys(draws))[:target]  # de-duplicate, keep order, cap at target

        for idx in active:
            country, currency, persona, factor, travels, _rec, _off = users[idx]
            cats, cat_cum, _f, _r = persona_tables[persona]
            for _ in range(choices(count_choices, cum_weights=count_cum)[0]):
                category = choices(cats, cum_weights=cat_cum)[0]
                names, cum, ranges = item_tables[category]
                description = choices(names, cum_weights=cum)[0]
                low, high = ranges[description]
                use_currency = currency
                if (
                    category == "travel"
                    and travels
                    and description in foreign_items
                    and rand() < 0.5
                ):
                    use_currency = rng.choice(other_currencies[currency])
                amount = tidy_price(rng, randint(low, high) * factor, use_currency)
                created = stamp_for(d, 0 if rand() < 0.85 else randint(1, 2))
                batch.append(
                    (
                        idx + 1,
                        amount,
                        use_currency,
                        description,
                        category,
                        pick_local(rng, merchants[description], country),
                        pick_payment(rng, description, country),
                        0,
                        day_iso[d],
                        created,
                        created,
                    )
                )
            if len(batch) >= BATCH:
                flush()
        if (d + 1) % 20 == 0 or d == args.days - 1:
            print(
                f"  day {d + 1}/{args.days}  active={len(active):,}  rows so far={total_rows + len(batch):,}  ({time.time() - started:.0f}s)"
            )

    # ---- recurring monthly items (rent, phone, broadband, ...) for users who track them
    for idx, (country, currency, _persona, _factor, _travels, has_recurring, offset) in enumerate(
        users
    ):
        if not has_recurring:
            continue
        first_day = max(window_start, window_start + timedelta(days=offset))
        persona = users[idx][2]
        for (
            description,
            category,
            low,
            high,
            chance,
            varies,
            merchant_options,
            pay_options,
        ) in g.RECURRING:
            if description == "Monthly rent":
                chance = persona_tables[persona][3]
            if rand() > chance:
                continue
            base = randint(low, high)
            day = randint(1, 28)
            merchant = pick_local(rng, merchant_options, country)
            payment = rng.choice(pay_options)
            fixed = tidy_price(rng, base, currency)
            year, month = first_day.year, first_day.month
            while date(year, month, 1) <= today:
                due = date(year, month, min(day, calendar.monthrange(year, month)[1]))
                if first_day <= due <= today:
                    amount = (
                        tidy_price(rng, base * uniform(0.8, 1.25), currency) if varies else fixed
                    )
                    di = (due - window_start).days
                    created = stamp_for(di, 0)
                    batch.append(
                        (
                            idx + 1,
                            amount,
                            currency,
                            description,
                            category,
                            merchant,
                            payment,
                            1,
                            due.isoformat(),
                            created,
                            created,
                        )
                    )
                year, month = (year + 1, 1) if month == 12 else (year, month + 1)
            if len(batch) >= BATCH:
                flush()
    flush()
    conn.commit()
    print(f"{total_rows:,} expenses inserted ({time.time() - started:.0f}s)")

    # ---- budgets: ~70% of users, close to their real monthly spend in their home currency
    print("computing budgets...")
    spend = conn.execute(
        "SELECT e.user_id, SUM(e.amount_minor), MIN(e.expense_date), MAX(e.expense_date) "
        "FROM expenses e JOIN users u ON u.id = e.user_id AND e.currency = u.default_currency GROUP BY e.user_id"
    ).fetchall()
    updates = []
    for user_id, total, first_date, last_date in spend:
        if rand() > 0.70:
            continue
        months = max(
            1.0, (date.fromisoformat(last_date) - date.fromisoformat(first_date)).days / 30.4
        )
        currency = users[user_id - 1][1]
        step = 500 if currency == "INR" else 50
        budget_major = max(step, round(total / months * uniform(0.85, 1.2) / 100 / step) * step)
        updates.append((budget_major * 100, user_id))
    conn.executemany("UPDATE users SET monthly_budget_minor = ? WHERE id = ?", updates)
    conn.commit()

    # ---- rebuild indexes, refresh planner statistics
    rebuild_indexes()

    dau = conn.execute(
        "SELECT AVG(c) FROM (SELECT COUNT(DISTINCT user_id) c FROM expenses WHERE expense_date >= date('now','-30 day') GROUP BY expense_date)"
    ).fetchone()[0]
    size_mb = Path(args.db).stat().st_size / 1_048_576
    print(f"\nseed={seed}  done in {time.time() - started:.0f}s")
    print(
        f"users={n_users:,}  expenses={total_rows:,}  budgets={len(updates):,}  avg DAU (last 30 days)={dau:,.0f}  db size={size_mb:,.0f} MB"
    )
    conn.close()


if __name__ == "__main__":
    main()
