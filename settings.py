# ── Site-wide theme settings ──────────────────────────────────────────────────
# DEFAULT_SKIN is the theme applied to visitors who have no stored preference.
# ALLOWED_SKINS are the valid values accepted by the profile settings API.
#
# Skin identifiers:
#   'dark'      — default dark theme
#   'tentaizu'  — star/space theme used on the Tentaizu pages
#   'diana'     — Lady Di's Mines classic skin (stored as 'classic' in CSS/DB)

from datetime import date, datetime, timedelta

DEFAULT_SKIN: str = 'dark'
ALLOWED_SKINS: tuple[str, ...] = ('dark', 'tentaizu', 'diana')

# ── PvP opponent board delay ───────────────────────────────────────────────────
# Seconds to delay showing the opponent's board moves to the player.
# 0 = real-time (no delay). Adjust to change competitive feel.
PVP_OPPONENT_BOARD_DELAY_SECS: int = 3

# ── Diana birthday theming ────────────────────────────────────────────────────
DIANA_BIRTHDAY_SKIN:   str = 'diana'
DIANA_BIRTHDAY_BANNER: str = "Happy birthday, Diana, Princess of Wales!"

# ── Solstice theming ──────────────────────────────────────────────────────────
SOLSTICE_SKIN: str = 'tentaizu'
SOLSTICE_BANNER: str = "Tentaizu theme is in celebration of the solstice!"

# ── Equinox theming ───────────────────────────────────────────────────────────
EQUINOX_BANNER: str = "In celebration of the Equinox, please enjoy the Tentaizu theme"


def _astronomical_dates(year: int) -> tuple[date, date, date, date]:
    """Return (march_equinox, june_solstice, september_equinox, december_solstice)
    for the given year (server time).

    Uses the Meeus simplified formula (Astronomical Algorithms, ch. 27).
    Accurate to within a few minutes for years near 2000, so the calendar
    date is always correct.
    """
    Y = (year - 2000) / 1000.0
    march_jde = (2451623.80984
                 + 365242.37404 * Y
                 + 0.05169      * Y ** 2
                 - 0.00411      * Y ** 3
                 - 0.00057      * Y ** 4)
    june_jde  = (2451716.567
                 + 365241.62603 * Y
                 + 0.00325      * Y ** 2
                 + 0.00888      * Y ** 3
                 - 0.00030      * Y ** 4)
    sep_jde   = (2451810.21715
                 + 365242.01767 * Y
                 - 0.11575      * Y ** 2
                 + 0.00337      * Y ** 3
                 + 0.00078      * Y ** 4)
    dec_jde   = (2451900.05952
                 + 365242.74049 * Y
                 - 0.06223      * Y ** 2
                 - 0.00823      * Y ** 3
                 + 0.00032      * Y ** 4)
    # JDE 2451545.0 == J2000.0 == 2000-01-01 12:00 TT (≈ UTC)
    epoch = datetime(2000, 1, 1, 12)
    to_date = lambda jde: (epoch + timedelta(days=jde - 2451545.0)).date()
    return to_date(march_jde), to_date(june_jde), to_date(sep_jde), to_date(dec_jde)


def is_solstice_today() -> bool:
    """Return True if today (server time) is a solstice."""
    today = date.today()
    _, june_sol, _, dec_sol = _astronomical_dates(today.year)
    return today in (june_sol, dec_sol)


def is_equinox_today() -> bool:
    """Return True if today (server time) is an equinox."""
    today = date.today()
    march_eq, _, sep_eq, _ = _astronomical_dates(today.year)
    return today in (march_eq, sep_eq)


def is_diana_birthday() -> bool:
    """Return True if today (server time) is July 1st — Diana's birthday."""
    today = date.today()
    return today.month == 7 and today.day == 1


def active_skin() -> str:
    """Return the skin that should be active today."""
    if is_diana_birthday():
        return DIANA_BIRTHDAY_SKIN
    if is_solstice_today() or is_equinox_today():
        return SOLSTICE_SKIN
    return DEFAULT_SKIN


def solstice_banner() -> str | None:
    """Return the solstice banner message, or None when not a solstice."""
    return SOLSTICE_BANNER if is_solstice_today() else None


def equinox_banner() -> str | None:
    """Return the equinox banner message, or None when not an equinox."""
    return EQUINOX_BANNER if is_equinox_today() else None


def diana_birthday_banner() -> str | None:
    """Return the Diana birthday banner message, or None when not July 1st."""
    return DIANA_BIRTHDAY_BANNER if is_diana_birthday() else None
