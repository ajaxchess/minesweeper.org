# ── Site-wide theme settings ──────────────────────────────────────────────────
# DEFAULT_SKIN is the theme applied to visitors who have no stored preference.
# ALLOWED_SKINS are the valid values accepted by the profile settings API.
#
# Skin identifiers:
#   'dark'      — default dark theme
#   'tentaizu'  — star/space theme used on the Tentaizu pages
#   'diana'     — Lady Di's Mines classic skin (stored as 'classic' in CSS/DB)

DEFAULT_SKIN: str = 'dark'
ALLOWED_SKINS: tuple[str, ...] = ('dark', 'tentaizu', 'diana')
