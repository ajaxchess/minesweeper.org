"""Add French tmt_* keys"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import insert_tmt

insert_tmt.LANGS["fr"] = {
    "tmt_bridge": "Un puzzle logique quotidien — choisissez une difficulté et laissez les chiffres vous guider.",
    "tmt_my_history": "Mon Historique",
    "tmt_stat_mines": "Mines restantes",
    "tmt_stat_time": "Temps écoulé",
    "tmt_overlay_solved": "🎉 Puzzle résolu !",
    "tmt_retry": "🔄 Réessayer",
    "tmt_new_random": "🎲 Nouveau aléatoire",
    "tmt_start_hint": "Cliquez sur une cellule pour commencer &middot; <strong>Clic gauche</strong> révéler &middot; <strong>Clic droit</strong> drapeau",
    "tmt_play_hint": "Survolez un chiffre pour surligner sa région &middot; chaque chiffre compte les mines dans sa <strong>région surlignée</strong>",
    "tmt_lb_today": "🏆 Classement du jour",
    "tmt_about_h2": "À propos de Tametsi",
    "tmt_what_h2": "Qu'est-ce que Tametsi ?",
    "tmt_what_p1": "Tametsi est un puzzle logique numérique où vous devez localiser toutes les mines cachées sur une grille en utilisant des indices numériques régionaux, pas seulement les comptages de cellules adjacentes.",
    "tmt_what_p2": "Chaque chiffre révélé vous indique combien de mines sont cachées dans une <strong>région définie</strong>. Les régions peuvent s'étendre sur tout le plateau, se replier sur les bords ou former des formes irrégulières.",
    "tmt_what_p3": "Chaque puzzle sur ce site est garanti résolvable par pure logique — aucune supposition requise.",
    "tmt_howto_h2": "Comment jouer à Tametsi",
    "tmt_howto_li1": "<strong>Clic gauche</strong> sur une cellule pour la révéler et voir son compte de mines régional.",
    "tmt_howto_li2": "<strong>Clic droit</strong> sur une cellule pour placer un drapeau (🚩) sur une mine suspectée.",
    "tmt_howto_li3": "Survolez n'importe quel chiffre révélé pour surligner la région qu'il compte.",
    "tmt_howto_li4": "Utilisez les indices numériques pour déduire quelles cellules sont sûres et lesquelles cachent des mines.",
    "tmt_howto_li5": "Gagnez en marquant correctement toutes les mines et en révélant toutes les cellules sûres.",
    "tmt_vs_ms_h2": "Tametsi vs. Démineur",
    "tmt_vs_ms_li1": "<strong>Indices régionaux :</strong> Les chiffres comptent les mines dans une région définie, pas seulement dans les 8 cellules adjacentes.",
    "tmt_vs_ms_li2": "<strong>Pas de supposition :</strong> Chaque puzzle est entièrement résolvable par la logique — pas de choix 50/50.",
    "tmt_vs_ms_li3": "<strong>Régions irrégulières :</strong> Les régions d'indices peuvent avoir n'importe quelle forme, pas un voisinage fixe de 3×3.",
    "tmt_vs_ms_li4": "<strong>Plateaux enveloppants :</strong> Certaines grilles ont des bords qui se connectent, ouvrant de nouveaux chemins de déduction.",
    "tmt_vs_ms_li5": "<strong>Nouveau puzzle quotidien :</strong> Un nouveau défi garanti résolvable chaque jour à minuit UTC.",
    "tmt_vs_tz_h2": "Tametsi vs. Tentaizu",
    "tmt_vs_tz_intro": 'Tametsi et <a href="/tentaizu">Tentaizu</a> sont tous deux des puzzles régionaux de recherche de mines, mais diffèrent sur des points clés :',
    "tmt_vs_tz_li1": "<strong>Taille de la grille :</strong> Tametsi utilise des grilles multi-rangées plus grandes ; Tentaizu utilise une grille compacte de 7×7.",
    "tmt_vs_tz_li2": "<strong>Nombre de mines :</strong> Tametsi a de nombreuses mines sur un grand plateau ; Tentaizu en cache exactement 10.",
    "tmt_vs_tz_li3": "<strong>Niveaux de difficulté :</strong> Tametsi propose les modes Débutant, Intermédiaire et Expert.",
    "tmt_vs_tz_li4": "<strong>Révéler vs. cycler :</strong> Dans Tametsi vous révélez des cellules ; dans Tentaizu vous faites cycler les cellules entre les états.",
    "tmt_strategy_h2": "Conseils de stratégie Tametsi",
    "tmt_strategy_li1": "<strong>Commencez par les régions entièrement contraintes.</strong> Si le nombre de mines d'une région est égal à son nombre de cellules cachées, marquez-les toutes.",
    "tmt_strategy_li2": "<strong>Repérez les régions nulles.</strong> Une région affichant 0 signifie que chaque cellule cachée dans cette région est sûre — révélez-les toutes.",
    "tmt_strategy_li3": "<strong>Soustrayez les régions superposées.</strong> La différence dans les comptes entre les régions superposées contraint leurs cellules uniques.",
    "tmt_strategy_li4": "<strong>Survolez pour visualiser.</strong> Survolez n'importe quel chiffre pour voir sa région et trouver des chevauchements avec les voisins.",
    "tmt_strategy_li5": "<strong>Marquez tôt.</strong> Les mines confirmées marquées rapidement réduisent les inconnues dans chaque région superposée.",
    "tmt_strategy_li6": "<strong>Travaillez de l'extérieur vers l'intérieur.</strong> Les petites régions de bord fournissent souvent les premières déductions sûres.",
}

if __name__ == "__main__":
    ok = insert_tmt.insert_lang("fr")
    sys.exit(0 if ok else 1)
