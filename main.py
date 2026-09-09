"""
main.py
-------
CLI entry point for the Aldi Budget Meal Planner.

Commands
--------
  setup              -- run the profile setup wizard
  profile            -- show current profile and budget status
  spend <EUR>        -- record a purchase against your budget
  reset-day          -- reset today's spending counter
  reset-week         -- reset the entire weekly spending counter
  ai-plan            -- generate an AI meal plan via Gemini (budget from profile)
  ai-plan --days N   -- plan for N days  (default: 3)
  ai-plan --dry-run  -- show the prompt without calling the API
"""

import io
import sys

# Ensure emoji and Unicode print cleanly on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf-8-sig"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() not in ("utf-8", "utf-8-sig"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from profile import UserProfile, setup_wizard

HELP = __doc__


def cmd_setup() -> None:
    setup_wizard()


def cmd_profile() -> None:
    profile = UserProfile.load()
    profile.display()


def cmd_spend(amount_str: str) -> None:
    try:
        amount = float(amount_str)
    except ValueError:
        print(f"❌ Invalid amount: '{amount_str}'")
        return
    profile = UserProfile.load()
    profile.record_spend(amount)
    profile.save()
    print(f"✅ Recorded €{amount:.2f} spend.")
    print(f"   Remaining today  : €{profile.remaining_today:.2f}")
    print(f"   Remaining week   : €{profile.remaining_this_week:.2f}")


def cmd_reset_day() -> None:
    profile = UserProfile.load()
    profile.reset_daily()
    profile.save()
    print("✅ Daily spending reset to €0.00.")


def cmd_reset_week() -> None:
    profile = UserProfile.load()
    profile.reset_weekly()
    profile.save()
    print("✅ Weekly spending reset to €0.00.")


def cmd_ai_plan(args_str: str) -> None:
    from ai_planner import run as ai_run

    parts = args_str.split() if args_str.strip() else []
    days: int | None = None
    dry_run = False

    i = 0
    while i < len(parts):
        if parts[i] == "--days" and i + 1 < len(parts):
            try:
                days = int(parts[i + 1])
            except ValueError:
                print(f"❌ --days requires an integer, got '{parts[i + 1]}'")
                return
            i += 2
        elif parts[i] == "--dry-run":
            dry_run = True
            i += 1
        else:
            print(f"⚠️  Unknown flag '{parts[i]}' — ignoring.")
            i += 1

    ai_run(days=days, dry_run=dry_run)


def print_help() -> None:
    print(HELP)


# ── dispatch ──────────────────────────────────────────────────────────────────

# Each entry: (function, n_required_positional_args, passes_extra_as_string)
COMMANDS = {
    "setup":      (cmd_setup,      0, False),
    "profile":    (cmd_profile,    0, False),
    "spend":      (cmd_spend,      1, True),
    "reset-day":  (cmd_reset_day,  0, False),
    "reset-week": (cmd_reset_week, 0, False),
    "ai-plan":    (cmd_ai_plan,    0, True),   # passes remaining flags as a string
}


def main() -> None:
    args = sys.argv[1:]

    if not args or args[0] in ("-h", "--help", "help"):
        print_help()
        return

    cmd = args[0].lower()
    if cmd not in COMMANDS:
        print(f"❌ Unknown command '{cmd}'.")
        print_help()
        return

    fn, n_args, pass_extra = COMMANDS[cmd]
    extra = args[1:]

    if len(extra) < n_args:
        print(f"❌ '{cmd}' requires {n_args} argument(s), got {len(extra)}.")
        return

    if pass_extra:
        fn(" ".join(extra))
    else:
        fn()


if __name__ == "__main__":
    main()
