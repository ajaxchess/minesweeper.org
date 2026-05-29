"""Add Italian tmt_* keys"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import insert_tmt

insert_tmt.LANGS["it"] = {
    "tmt_bridge": "Un puzzle logico quotidiano — scegli una difficoltà e lascia che i numeri ti guidino.",
    "tmt_my_history": "La Mia Cronologia",
    "tmt_stat_mines": "Mine rimanenti",
    "tmt_stat_time": "Tempo trascorso",
    "tmt_overlay_solved": "🎉 Puzzle Risolto!",
    "tmt_retry": "🔄 Riprova",
    "tmt_new_random": "🎲 Nuovo Casuale",
    "tmt_start_hint": "Clicca su qualsiasi cella per iniziare &middot; <strong>Click sinistro</strong> scopri &middot; <strong>Click destro</strong> bandiera",
    "tmt_play_hint": "Passa il mouse su un numero per evidenziare la sua regione &middot; ogni numero conta le mine nella sua <strong>regione evidenziata</strong>",
    "tmt_lb_today": "🏆 Classifica di Oggi",
    "tmt_about_h2": "Informazioni su Tametsi",
    "tmt_what_h2": "Cos'è Tametsi?",
    "tmt_what_p1": "Tametsi è un puzzle di logica numerica in cui devi individuare tutte le mine nascoste su una griglia usando indizi numerici regionali — non solo i conteggi delle celle adiacenti.",
    "tmt_what_p2": "Ogni numero rivelato ti indica quante mine sono nascoste in una <strong>regione definita</strong>. Le regioni possono estendersi sull'intera plancia, avvolgersi ai bordi o formare forme irregolari.",
    "tmt_what_p3": "Ogni puzzle su questo sito è garantito risolvibile con pura logica — nessuna ipotesi necessaria.",
    "tmt_howto_h2": "Come Giocare a Tametsi",
    "tmt_howto_li1": "<strong>Click sinistro</strong> su una cella per rivelarla e vedere il conteggio delle mine nella sua regione.",
    "tmt_howto_li2": "<strong>Click destro</strong> su una cella per piazzare una bandiera (🚩) su una mina sospetta.",
    "tmt_howto_li3": "Passa il mouse su qualsiasi numero rivelato per evidenziare la regione che conta.",
    "tmt_howto_li4": "Usa gli indizi numerici per dedurre quali celle sono sicure e quali nascondono mine.",
    "tmt_howto_li5": "Vinci segnalando correttamente tutte le mine e rivelando tutte le celle sicure.",
    "tmt_vs_ms_h2": "Tametsi vs. Campo Minato",
    "tmt_vs_ms_li1": "<strong>Indizi regionali:</strong> I numeri contano le mine in una regione definita, non solo nelle 8 celle adiacenti.",
    "tmt_vs_ms_li2": "<strong>Nessuna ipotesi:</strong> Ogni puzzle è completamente risolvibile logicamente — nessuna scelta 50/50.",
    "tmt_vs_ms_li3": "<strong>Regioni irregolari:</strong> Le regioni degli indizi possono avere qualsiasi forma, non solo un vicinato fisso di 3×3.",
    "tmt_vs_ms_li4": "<strong>Plancie avvolgenti:</strong> Alcune griglie hanno bordi che si collegano, aprendo nuovi percorsi di deduzione.",
    "tmt_vs_ms_li5": "<strong>Nuovo puzzle quotidiano:</strong> Una nuova sfida garantita risolvibile ogni giorno a mezzanotte UTC.",
    "tmt_vs_tz_h2": "Tametsi vs. Tentaizu",
    "tmt_vs_tz_intro": 'Sia Tametsi che <a href="/tentaizu">Tentaizu</a> sono puzzle regionali di ricerca mine, ma differiscono in aspetti fondamentali:',
    "tmt_vs_tz_li1": "<strong>Dimensione della griglia:</strong> Tametsi usa griglie più grandi con più righe; Tentaizu usa una griglia compatta di 7×7.",
    "tmt_vs_tz_li2": "<strong>Conteggio delle mine:</strong> Tametsi ha molte mine su una grande plancia; Tentaizu ne nasconde esattamente 10.",
    "tmt_vs_tz_li3": "<strong>Livelli di difficoltà:</strong> Tametsi offre le modalità Principiante, Intermedio ed Esperto.",
    "tmt_vs_tz_li4": "<strong>Rivelare vs. ciclare:</strong> In Tametsi riveli le celle; in Tentaizu cicli le celle attraverso gli stati.",
    "tmt_strategy_h2": "Consigli Strategici per Tametsi",
    "tmt_strategy_li1": "<strong>Inizia con le regioni completamente vincolate.</strong> Se il conteggio delle mine di una regione è uguale al numero di celle nascoste, segna tutte.",
    "tmt_strategy_li2": "<strong>Individua le regioni zero.</strong> Una regione che mostra 0 significa che ogni cella nascosta in essa è sicura — rivela tutte.",
    "tmt_strategy_li3": "<strong>Sottrai le regioni sovrapposte.</strong> La differenza nei conteggi tra regioni sovrapposte vincola le loro celle uniche.",
    "tmt_strategy_li4": "<strong>Passa il mouse per visualizzare.</strong> Passa il mouse su qualsiasi numero per vedere la sua regione e trovare sovrapposizioni con i vicini.",
    "tmt_strategy_li5": "<strong>Segna presto.</strong> Le mine confermate segnate prontamente riducono le incognite in ogni regione sovrapposta.",
    "tmt_strategy_li6": "<strong>Lavora verso l'interno.</strong> Le regioni di bordo più piccole spesso forniscono le prime deduzioni certe.",
}

if __name__ == "__main__":
    ok = insert_tmt.insert_lang("it")
    sys.exit(0 if ok else 1)
