from pathlib import Path

from countries import COUNTRIES, VALID_COUNTRY_CODES


def test_united_kingdom_constituent_flags_are_profile_choices(client):
    names_by_code = dict(COUNTRIES)

    assert names_by_code["gb"] == "United Kingdom"
    assert names_by_code["gb-eng"] == "England"
    assert names_by_code["gb-sct"] == "Scotland"
    assert names_by_code["gb-wls"] == "Wales"
    assert names_by_code["gb-nir"] == "Northern Ireland"
    assert names_by_code["ie"] == "Ireland"

    for code in ("gb", "gb-eng", "gb-sct", "gb-wls", "gb-nir", "ie"):
        assert code in VALID_COUNTRY_CODES


def test_every_profile_country_has_a_flag_asset(client):
    missing = [
        code
        for code, _name in COUNTRIES
        if not Path("static/img/country-flags", f"{code}.png").is_file()
    ]

    assert missing == []


def test_profile_country_codes_are_unique(client):
    codes = [code for code, _name in COUNTRIES]

    assert len(codes) == len(set(codes))
