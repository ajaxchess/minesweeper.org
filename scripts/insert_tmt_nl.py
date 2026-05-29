"""Add Dutch tmt_* keys"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import insert_tmt

insert_tmt.LANGS["nl"] = {
    "tmt_bridge": "Een dagelijks logisch puzzel — kies een moeilijkheidsgraad en laat de cijfers je leiden.",
    "tmt_my_history": "Mijn Geschiedenis",
    "tmt_stat_mines": "Resterende mijnen",
    "tmt_stat_time": "Verstreken tijd",
    "tmt_overlay_solved": "🎉 Puzzel Opgelost!",
    "tmt_retry": "🔄 Opnieuw Proberen",
    "tmt_new_random": "🎲 Nieuw Willekeurig",
    "tmt_start_hint": "Klik op een cel om te beginnen &middot; <strong>Linksklik</strong> onthullen &middot; <strong>Rechtsklik</strong> vlag",
    "tmt_play_hint": "Beweeg de muis over een getal om het gebied te markeren &middot; elk getal telt mijnen in zijn <strong>gemarkeerd gebied</strong>",
    "tmt_lb_today": "🏆 Scorebord van Vandaag",
    "tmt_about_h2": "Over Tametsi",
    "tmt_what_h2": "Wat Is Tametsi?",
    "tmt_what_p1": "Tametsi is een cijferlogisch puzzel waarbij je alle verborgen mijnen op een raster moet vinden met behulp van regionale cijferaanwijzingen — niet alleen tellingen van aangrenzende cellen.",
    "tmt_what_p2": "Elk onthuld getal vertelt je hoeveel mijnen er verborgen zijn in een <strong>gedefinieerd gebied</strong>. Gebieden kunnen het hele bord omspannen, langs de randen vouwen, of onregelmatige vormen vormen.",
    "tmt_what_p3": "Elke puzzel op deze site is gegarandeerd oplosbaar door pure logica — geen gokken nodig.",
    "tmt_howto_h2": "Hoe Tametsi te Spelen",
    "tmt_howto_li1": "<strong>Linksklik</strong> op een cel om het te onthullen en het regionale mijnentelsel te zien.",
    "tmt_howto_li2": "<strong>Rechtsklik</strong> op een cel om een vlag (🚩) op een verdachte mijn te plaatsen.",
    "tmt_howto_li3": "Beweeg de muis over een onthuld getal om het gebied dat het telt te markeren.",
    "tmt_howto_li4": "Gebruik de cijferaanwijzingen om af te leiden welke cellen veilig zijn en welke mijnen bevatten.",
    "tmt_howto_li5": "Win door alle mijnen correct te markeren en alle veilige cellen te onthullen.",
    "tmt_vs_ms_h2": "Tametsi vs. Mijnenveger",
    "tmt_vs_ms_li1": "<strong>Regionale aanwijzingen:</strong> Getallen tellen mijnen in een gedefinieerd gebied, niet alleen in de 8 aangrenzende cellen.",
    "tmt_vs_ms_li2": "<strong>Geen gokken:</strong> Elke puzzel is volledig oplosbaar door logica — geen 50/50-keuzes.",
    "tmt_vs_ms_li3": "<strong>Onregelmatige gebieden:</strong> Aanwijzingsgebieden kunnen elke vorm hebben, niet alleen een vast 3×3-buurt.",
    "tmt_vs_ms_li4": "<strong>Omhullende borden:</strong> Sommige rasters hebben verbonden randen, waardoor nieuwe deductiepadden worden geopend.",
    "tmt_vs_ms_li5": "<strong>Dagelijks nieuw puzzel:</strong> Een nieuw gegarandeerd oplosbaar uitdaging elke dag om middernacht UTC.",
    "tmt_vs_tz_h2": "Tametsi vs. Tentaizu",
    "tmt_vs_tz_intro": 'Zowel Tametsi als <a href="/tentaizu">Tentaizu</a> zijn regionale mijnzoekpuzzels, maar verschillen op belangrijke punten:',
    "tmt_vs_tz_li1": "<strong>Rastergrootte:</strong> Tametsi gebruikt grotere rasters met meerdere rijen; Tentaizu gebruikt een compact 7×7-raster.",
    "tmt_vs_tz_li2": "<strong>Mijnentelsel:</strong> Tametsi heeft veel mijnen op een groot bord; Tentaizu verbergt er precies 10.",
    "tmt_vs_tz_li3": "<strong>Moeilijkheidsgraden:</strong> Tametsi biedt Beginner-, Gemiddelde- en Expertmodi.",
    "tmt_vs_tz_li4": "<strong>Onthullen vs. doorlopen:</strong> In Tametsi onthul je cellen; in Tentaizu loop je cellen door statussen.",
    "tmt_strategy_h2": "Tametsi Strategietips",
    "tmt_strategy_li1": "<strong>Begin met volledig beperkte gebieden.</strong> Als de mijnentelsel van een gebied gelijk is aan het aantal verborgen cellen, markeer ze allemaal.",
    "tmt_strategy_li2": "<strong>Zoek nulgebieden.</strong> Een gebied dat 0 toont, betekent dat elke verborgen cel daarin veilig is — onthul ze allemaal.",
    "tmt_strategy_li3": "<strong>Trek overlappende gebieden af.</strong> Het verschil in tellingen tussen overlappende gebieden beperkt hun unieke cellen.",
    "tmt_strategy_li4": "<strong>Beweeg de muis om te visualiseren.</strong> Beweeg de muis over een getal om het gebied te zien en overlappingen met buren te vinden.",
    "tmt_strategy_li5": "<strong>Markeer vroeg.</strong> Bevestigde mijnen die snel worden gemarkeerd, verminderen de onbekenden in elk overlappend gebied.",
    "tmt_strategy_li6": "<strong>Werk naar binnen.</strong> Kleinere randgebieden bieden vaak de eerste zekere deducties.",
}

if __name__ == "__main__":
    ok = insert_tmt.insert_lang("nl")
    sys.exit(0 if ok else 1)
