"""Add Esperanto tmt_* keys then run insert_tmt.py eo"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import insert_tmt

insert_tmt.LANGS["eo"] = {
    "tmt_bridge": "Ĉiutaga logika enigmo — elektu malfacilecon kaj lasu la nombrojn gvidi vin.",
    "tmt_my_history": "Mia Historio",
    "tmt_stat_mines": "Restantaj minoj",
    "tmt_stat_time": "Pasinta tempo",
    "tmt_overlay_solved": "🎉 Enigmo Solvita!",
    "tmt_retry": "🔄 Reprovi",
    "tmt_new_random": "🎲 Nova Hazarda",
    "tmt_start_hint": "Alklaku ajnan ĉelon por komenci &middot; <strong>Maldekstra klako</strong> malkovras &middot; <strong>Dekstra klako</strong> flagas",
    "tmt_play_hint": "Ŝvebu super nombro por reliefigi ĝian regionon &middot; ĉiu nombro kalkulas minojn en sia <strong>reliefigita regiono</strong>",
    "tmt_lb_today": "🏆 Hodiaŭa Tabelo",
    "tmt_about_h2": "Pri Tametsi",
    "tmt_what_h2": "Kio Estas Tametsi?",
    "tmt_what_p1": "Tametsi estas nombra logika enigmo, kie vi devas trovi ĉiujn kaŝitajn minojn en krado uzante regionajn nombrajn indikojn — ne nur nombrojn de apudaj ĉeloj.",
    "tmt_what_p2": "Ĉiu malkovrita nombro diras al vi, kiom da minoj estas kaŝitaj en <strong>difinita regiono</strong>. Regionoj povas etendiĝi tra la tuta tablo, ĉirkaŭvolvi randojn, aŭ formi neregulajn formojn.",
    "tmt_what_p3": "Ĉiu enigmo sur ĉi tiu retejo estas garantiite solvebla per pura logiko — neniu diveno bezonata.",
    "tmt_howto_h2": "Kiel Ludi Tametsi",
    "tmt_howto_li1": "<strong>Maldekstra klako</strong> sur ĉelo malkovras ĝin kaj montras ĝian regionan minokalkulon.",
    "tmt_howto_li2": "<strong>Dekstra klako</strong> sur ĉelo metas flagon (🚩) sur suspektatan minon.",
    "tmt_howto_li3": "Ŝvebu super malkovrita nombro por reliefigi la regionon, kiun ĝi kalkulas.",
    "tmt_howto_li4": "Uzu nombrajn indikojn por dedukti, kiuj ĉeloj estas sekuraj kaj kiuj kaŝas minojn.",
    "tmt_howto_li5": "Venku per ĝuste flagado ĉiuj minoj kaj malkovrante ĉiujn sekurajn ĉelojn.",
    "tmt_vs_ms_h2": "Tametsi kontraŭ Minesweeper",
    "tmt_vs_ms_li1": "<strong>Regionaj indikpunktoj:</strong> Nombroj kalkulas minojn en difinita regiono, ne nur en 8 apudaj ĉeloj.",
    "tmt_vs_ms_li2": "<strong>Neniu diveno:</strong> Ĉiu enigmo estas plene logike solvebla — neniaj 50/50 divenado.",
    "tmt_vs_ms_li3": "<strong>Neregulaj regionoj:</strong> Indikpunktaj regionoj povas esti ajna formo, ne fiksa 3×3 najbaro.",
    "tmt_vs_ms_li4": "<strong>Envolvi tabuloj:</strong> Iuj kradoj havas randojn kiuj konektas, malfermante novajn deduktajn vojojn.",
    "tmt_vs_ms_li5": "<strong>Freŝa ĉiutaga enigmo:</strong> Nova garantiite-solvebla defio ĉiun tagon je noktomezo UTC.",
    "tmt_vs_tz_h2": "Tametsi kontraŭ Tentaizu",
    "tmt_vs_tz_intro": 'Tametsi kaj <a href="/tentaizu">Tentaizu</a> ambaŭ estas regionaj minserĉaj enigmoj, sed diferencas en ŝlosilaj manieroj:',
    "tmt_vs_tz_li1": "<strong>Krada grandeco:</strong> Tametsi uzas pli grandajn plur-vicliniajn kradojn; Tentaizu uzas kompaktan 7×7 kradon.",
    "tmt_vs_tz_li2": "<strong>Minokvanto:</strong> Tametsi havas multajn minojn tra granda tablo; Tentaizu kaŝas ekzakte 10.",
    "tmt_vs_tz_li3": "<strong>Malfacilecaj niveloj:</strong> Tametsi ofertas Komencanto, Meznivelo, kaj Eksperto reĝimojn.",
    "tmt_vs_tz_li4": "<strong>Malkovri kontraŭ cikli:</strong> En Tametsi vi malkovras ĉelojn; en Tentaizu vi ciclas ĉelojn tra statoj.",
    "tmt_strategy_h2": "Konsiloj pri Tametsi-Strategio",
    "tmt_strategy_li1": "<strong>Komencu kun plene limigitaj regionoj.</strong> Se la minokvanto de regiono egalas la nombron de kaŝitaj ĉeloj, flagu ĉiujn.",
    "tmt_strategy_li2": "<strong>Trovu nul-regionojn.</strong> Regiono montranta 0 signifas, ke ĉiu kaŝita ĉelo en ĝi estas sekura — malkovru ĉiujn.",
    "tmt_strategy_li3": "<strong>Subtrahu superkovrantajn regionojn.</strong> La diferenco en kalkuloj inter superkovrantaj regionoj limigas iliajn unikajn ĉelojn.",
    "tmt_strategy_li4": "<strong>Ŝvebu por bildigi.</strong> Ŝvebu super ajna nombro por vidi ĝian regionon kaj trovi superkovradon kun najbaroj.",
    "tmt_strategy_li5": "<strong>Flagu frue.</strong> Konfirmitaj minoj flagitaj baldaŭ malpliigas la nekonataĵojn en ĉiu superkovra regiono.",
    "tmt_strategy_li6": "<strong>Laboru enflue.</strong> Pli malgrandaj randaraj regionoj ofte donas la unuajn certajn deduktojn.",
}

if __name__ == "__main__":
    ok = insert_tmt.insert_lang("eo")
    sys.exit(0 if ok else 1)
