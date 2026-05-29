"""Add German tmt_* keys"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import insert_tmt

insert_tmt.LANGS["de"] = {
    "tmt_bridge": "Ein tägliches Logikrätsel — wähle einen Schwierigkeitsgrad und lass die Zahlen dich leiten.",
    "tmt_my_history": "Mein Verlauf",
    "tmt_stat_mines": "Verbleibende Minen",
    "tmt_stat_time": "Vergangene Zeit",
    "tmt_overlay_solved": "🎉 Rätsel gelöst!",
    "tmt_retry": "🔄 Nochmal",
    "tmt_new_random": "🎲 Neues Zufallsrätsel",
    "tmt_start_hint": "Klicke auf eine Zelle zum Starten &middot; <strong>Linksklick</strong> aufdecken &middot; <strong>Rechtsklick</strong> markieren",
    "tmt_play_hint": "Fahre über eine Zahl, um ihre Region hervorzuheben &middot; jede Zahl zählt Minen in ihrer <strong>hervorgehobenen Region</strong>",
    "tmt_lb_today": "🏆 Heutige Bestenliste",
    "tmt_about_h2": "Über Tametsi",
    "tmt_what_h2": "Was ist Tametsi?",
    "tmt_what_p1": "Tametsi ist ein zahlenbasiertes Logikrätsel, bei dem du alle versteckten Minen auf einem Raster mithilfe regionaler Zahlenhinweise finden musst — nicht nur anhand benachbarter Felder.",
    "tmt_what_p2": "Jede aufgedeckte Zahl verlässt dich, wie viele Minen in einer <strong>definierten Region</strong> versteckt sind. Regionen können das gesamte Raster umspannen, Ränder umwickeln oder unregelmäßige Formen bilden.",
    "tmt_what_p3": "Jedes Rätsel auf dieser Seite ist garantiert durch reine Logik lösbar — kein Raten erforderlich.",
    "tmt_howto_h2": "Wie man Tametsi spielt",
    "tmt_howto_li1": "<strong>Linksklick</strong> auf eine Zelle deckt sie auf und zeigt ihre regionale Minenanzahl.",
    "tmt_howto_li2": "<strong>Rechtsklick</strong> auf eine Zelle platziert eine Flagge (🚩) auf einer verdächtigen Mine.",
    "tmt_howto_li3": "Fahre über eine aufgedeckte Zahl, um die Region hervorzuheben, die sie zählt.",
    "tmt_howto_li4": "Nutze die Zahlenhinweise, um abzuleiten, welche Felder sicher sind und welche Minen enthalten.",
    "tmt_howto_li5": "Gewinne, indem du alle Minen korrekt markierst und alle sicheren Felder aufdeckst.",
    "tmt_vs_ms_h2": "Tametsi vs. Minesweeper",
    "tmt_vs_ms_li1": "<strong>Regionale Hinweise:</strong> Zahlen zählen Minen in einer definierten Region, nicht nur in den 8 benachbarten Feldern.",
    "tmt_vs_ms_li2": "<strong>Kein Raten:</strong> Jedes Rätsel ist vollständig logisch lösbar — keine 50/50-Entscheidungen.",
    "tmt_vs_ms_li3": "<strong>Unregelmäßige Regionen:</strong> Hinweisregionen können jede Form haben, nicht nur eine feste 3×3-Nachbarschaft.",
    "tmt_vs_ms_li4": "<strong>Umlaufende Raster:</strong> Manche Raster haben verbundene Ränder, die neue Ableitungspfade eröffnen.",
    "tmt_vs_ms_li5": "<strong>Tägliches Rätsel:</strong> Jeden Tag um Mitternacht UTC eine neue garantiert lösbare Herausforderung.",
    "tmt_vs_tz_h2": "Tametsi vs. Tentaizu",
    "tmt_vs_tz_intro": 'Sowohl Tametsi als auch <a href="/tentaizu">Tentaizu</a> sind regionale Minesrätsel, unterscheiden sich jedoch in wesentlichen Punkten:',
    "tmt_vs_tz_li1": "<strong>Rastergröße:</strong> Tametsi verwendet größere mehrzeilige Raster; Tentaizu verwendet ein kompaktes 7×7-Raster.",
    "tmt_vs_tz_li2": "<strong>Minenanzahl:</strong> Tametsi hat viele Minen auf einem großen Feld; Tentaizu verbirgt genau 10.",
    "tmt_vs_tz_li3": "<strong>Schwierigkeitsstufen:</strong> Tametsi bietet Anfänger-, Mittel- und Expertenmodus.",
    "tmt_vs_tz_li4": "<strong>Aufdecken vs. Wechseln:</strong> In Tametsi deckst du Felder auf; in Tentaizu wechselst du Felder durch Zustände.",
    "tmt_strategy_h2": "Tametsi-Strategietipps",
    "tmt_strategy_li1": "<strong>Beginne mit vollständig eingeschränkten Regionen.</strong> Wenn die Minenanzahl einer Region gleich der Anzahl der versteckten Felder ist, markiere alle.",
    "tmt_strategy_li2": "<strong>Finde Null-Regionen.</strong> Eine Region mit 0 bedeutet, dass jedes versteckte Feld darin sicher ist — decke sie alle auf.",
    "tmt_strategy_li3": "<strong>Subtrahiere überlappende Regionen.</strong> Der Unterschied in den Zählungen zwischen überlappenden Regionen schränkt deren einzigartige Felder ein.",
    "tmt_strategy_li4": "<strong>Fahre zum Visualisieren darüber.</strong> Fahre über eine Zahl, um ihre Region zu sehen und Überlappungen mit Nachbarn zu finden.",
    "tmt_strategy_li5": "<strong>Früh markieren.</strong> Bestätigte, früh markierte Minen reduzieren die Unbekannten in jeder überlappenden Region.",
    "tmt_strategy_li6": "<strong>Von innen arbeiten.</strong> Kleinere Randregionen liefern oft die ersten sicheren Ableitungen.",
}

if __name__ == "__main__":
    ok = insert_tmt.insert_lang("de")
    sys.exit(0 if ok else 1)
