"""Add Polish tmt_* keys"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import insert_tmt

insert_tmt.LANGS["pl"] = {
    "tmt_bridge": "Codzienna logiczna zagadka — wybierz poziom trudnosci i pozwol, by liczby cie prowadziły.",
    "tmt_my_history": "Moja Historia",
    "tmt_stat_mines": "Pozostale miny",
    "tmt_stat_time": "Uplynal czas",
    "tmt_overlay_solved": "🎉 Zagadka Rozwiazana!",
    "tmt_retry": "🔄 Sprobuj ponownie",
    "tmt_new_random": "🎲 Nowa Losowa",
    "tmt_start_hint": "Kliknij dowolna komorke, aby rozpoczac &middot; <strong>Lewy przycisk</strong> odkryj &middot; <strong>Prawy przycisk</strong> flaga",
    "tmt_play_hint": "Najedz na liczbe, aby podswietlic jej region &middot; kazda liczba liczy miny w swoim <strong>podswietlonym regionie</strong>",
    "tmt_lb_today": "🏆 Dzisiejsza Tabela Wynikow",
    "tmt_about_h2": "O Tametsi",
    "tmt_what_h2": "Czym jest Tametsi?",
    "tmt_what_p1": "Tametsi to logiczna zagadka liczbowa, w ktorej musisz zlokalizowac wszystkie ukryte miny na siatce, uzywajac regionalnych wskazowek liczbowych — nie tylko liczby sasiadujacych pol.",
    "tmt_what_p2": "Kazda odkryta liczba mowi ci, ile min jest ukrytych w <strong>okreslonym regionie</strong>. Regiony moga obejmowac cala plansze, zawijac sie na krawedziach lub tworzyc nieregularne ksztalty.",
    "tmt_what_p3": "Kazda zagadka na tej stronie jest gwarantowanie rozwiazywalna przez czesta logike — nie jest wymagane zgadywanie.",
    "tmt_howto_h2": "Jak Grac w Tametsi",
    "tmt_howto_li1": "<strong>Lewy przycisk myszy</strong> na komorce odkrywa ja i pokazuje liczbe min w jej regionie.",
    "tmt_howto_li2": "<strong>Prawy przycisk myszy</strong> na komorce umieszcza flage (🚩) na podejrzanej minie.",
    "tmt_howto_li3": "Najedz na odkryta liczbe, aby podswietlic region, ktory liczy.",
    "tmt_howto_li4": "Uzywaj wskazowek liczbowych, aby wywnioskac, ktore komorki sa bezpieczne, a ktore kryja miny.",
    "tmt_howto_li5": "Wygraj, prawidlowo oznaczajac wszystkie miny i odkrywajac wszystkie bezpieczne komorki.",
    "tmt_vs_ms_h2": "Tametsi kontra Saper",
    "tmt_vs_ms_li1": "<strong>Regionalne wskazowki:</strong> Liczby licza miny w okreslonym regionie, nie tylko w 8 sasiadujacych komorkach.",
    "tmt_vs_ms_li2": "<strong>Bez zgadywania:</strong> Kazda zagadka jest w pelni rozwiazywalna logicznie — bez wyboru 50/50.",
    "tmt_vs_ms_li3": "<strong>Nieregularne regiony:</strong> Regiony wskazowek moga miec dowolny ksztalt, a nie stalego 3x3 sasiedztwa.",
    "tmt_vs_ms_li4": "<strong>Zawijajace plansze:</strong> Niektorych siatki maja polaczone krawedzie, otwierajac nowe sciezki dedukcji.",
    "tmt_vs_ms_li5": "<strong>Swiezy codzienny puzel:</strong> Nowe gwarantowanie rozwiazywalne wyzwanie kazdego dnia o polnocy UTC.",
    "tmt_vs_tz_h2": "Tametsi kontra Tentaizu",
    "tmt_vs_tz_intro": 'Zarowno Tametsi, jak i <a href="/tentaizu">Tentaizu</a> sa regionalnymi zagadkami poszukiwania min, ale roznia sie w kluczowych kwestiach:',
    "tmt_vs_tz_li1": "<strong>Rozmiar siatki:</strong> Tametsi uzywa wiekszych wielorzedowych siatek; Tentaizu uzywa kompaktowej siatki 7x7.",
    "tmt_vs_tz_li2": "<strong>Liczba min:</strong> Tametsi ma wiele min na duzej planszy; Tentaizu ukrywa dokladnie 10.",
    "tmt_vs_tz_li3": "<strong>Poziomy trudnosci:</strong> Tametsi oferuje tryby Poczatkujacy, Sredniozaawansowany i Ekspert.",
    "tmt_vs_tz_li4": "<strong>Odkryc kontra cyklic:</strong> W Tametsi odkrywasz komorki; w Tentaizu cyklujesz komorki przez stany.",
    "tmt_strategy_h2": "Porady Strategiczne Tametsi",
    "tmt_strategy_li1": "<strong>Zacznij od w pelni ograniczonych regionow.</strong> Jesli liczba min regionu rowna sie liczbie ukrytych komorek, oznacz je wszystkie.",
    "tmt_strategy_li2": "<strong>Wykrywaj zerowe regiony.</strong> Region pokazujacy 0 oznacza, ze kazda ukryta komorka w nim jest bezpieczna — odkryj je wszystkie.",
    "tmt_strategy_li3": "<strong>Odejmuj nakladajace sie regiony.</strong> Roznica w liczbach miedzy nakladajacymi sie regionami ogranicza ich unikalne komorki.",
    "tmt_strategy_li4": "<strong>Najedz, aby zwizualizowac.</strong> Najedz na dowolna liczbe, aby zobaczyc jej region i znalezc nakladanie sie z sasiadami.",
    "tmt_strategy_li5": "<strong>Oznaczaj wczesnie.</strong> Potwierdzone miny oznaczone niezwlocznie zmniejszaja nieznane w kazdym nakladajacym sie regionie.",
    "tmt_strategy_li6": "<strong>Pracuj do wewnatrz.</strong> Mniejsze regiony krawedzi czesto dostarczaja pierwszych pewnych dedukcji.",
}

if __name__ == "__main__":
    ok = insert_tmt.insert_lang("pl")
    sys.exit(0 if ok else 1)
