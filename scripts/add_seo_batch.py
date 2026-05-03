#!/usr/bin/env python3
"""Insert seo_* keys for all remaining locales into translations.py"""

LOCALES = {
    "fr": {
        "anchor": '        "guest_banner_post": "sinon vos scores disparaîtront à minuit UTC.",',
        "keys": {
            "seo_beg_h2": "Jouer au Démineur en Ligne — Gratuit",
            "seo_beg_p1": 'Voici le plateau Débutant : une <strong>grille 9×9 avec 10 mines cachées</strong>. C\'est le point de départ classique — assez petit pour terminer en moins d\'une minute quand on connaît les règles, assez grand pour enseigner toutes les techniques fondamentales. Clic gauche pour révéler une case. Clic droit pour placer un drapeau sur une mine suspecte. Quand toutes les mines sont marquées et toutes les cases sûres ouvertes, vous gagnez.',
            "seo_beg_p2": 'Chaque chiffre sur le plateau indique combien de mines se cachent dans les huit cases qui l\'entourent. Un <em>1</em> près d\'une case d\'angle avec seulement deux voisins non révélés ? L\'une de ces deux est une mine. Un <em>0</em> ? Aucune mine à proximité — le plateau se développe automatiquement à travers toutes les cases vides adjacentes. Tout le jeu repose sur la lecture de ces chiffres et la déduction de l\'emplacement des mines.',
            "seo_about_h2": "À Propos de ce Site",
            "seo_about_p1": 'minesweeper.org — surnommé <strong>Les Mines de Lady Di</strong> — est une plateforme de Démineur gratuite dans le navigateur. Pas de téléchargement, pas d\'installation, pas de compte requis. Développé par une petite équipe souhaitant une implémentation rapide et propre respectant les règles classiques tout en ajoutant des commodités modernes : classements quotidiens, mode sans devinette, scores chronométrés avec statistiques 3BV et une collection croissante de variantes.',
            "seo_about_p2": 'Le lien avec Diana est une blague interne devenue marque : <em>Les Mines de Lady Di</em>. Quelque part entre un hommage et un terrible jeu de mots. Nous l\'assumons.',
            "seo_diff_h2": "Niveaux de Difficulté",
            "seo_diff_li1": '<strong>Débutant (cette page) —</strong> Grille 9×9, 10 mines. ~12,3 % de densité. Apprenez les règles, développez la mémoire musculaire, visez des temps en dessous de 10 secondes.',
            "seo_diff_li2": '<strong><a href="/intermediate">Intermédiaire</a> —</strong> Grille 16×16, 40 mines. ~15,6 % de densité. Chaînes plus longues, déductions plus complexes, là où la plupart des joueurs se bloquent.',
            "seo_diff_li3": '<strong><a href="/expert">Expert</a> —</strong> Grille 30×16, 99 mines. ~20,6 % de densité. La référence. Les records mondiaux y vivent. Dangereux à chaque coup.',
            "seo_diff_li4": '<strong><a href="/custom">Personnalisé</a> —</strong> Définissez vos propres dimensions de plateau et nombre de mines pour un défi sur mesure.',
            "seo_tips_h2": "Conseils pour Démarrer",
            "seo_tips_li1": '<strong>Cliquez d\'abord près du centre.</strong> Le premier clic est toujours sûr et ouvre généralement une plus grande cascade depuis une position centrale.',
            "seo_tips_li2": '<strong>Trouvez les zéros.</strong> Une région vide qui s\'étend automatiquement vous donne des informations gratuites et révèle de nombreux bords numérotés à exploiter.',
            "seo_tips_li3": '<strong>Drapeau ou juste mémoriser ?</strong> Vous n\'êtes pas obligé de marquer chaque mine — les drapeaux ne sont que des repères. Beaucoup de joueurs rapides évitent les drapeaux et utilisent leur mémoire pour maintenir un faible nombre de clics.',
            "seo_tips_li4": '<strong>Utilisez le mode sans devinette</strong> si vous détestez perdre à cause de situations 50/50. Il génère des plateaux toujours résolubles par la logique.',
            "seo_tips_li5": '<strong>Le chord pour aller plus vite.</strong> Double-cliquer sur un chiffre révélé révèle automatiquement tous ses voisins si le bon nombre de drapeaux est posé. C\'est le moyen le plus rapide de nettoyer un plateau une fois confiant.',
            "seo_beyond_h2": "Au-delà du Plateau Classique",
            "seo_beyond_p": "Une fois le débutant facile, il y a encore beaucoup à explorer ici :",
            "seo_beyond_li1": '<strong><a href="/tentaizu">Tentaizu</a> —</strong> Un puzzle japonais de carte étoilée. Tous les indices sont prédisposés, pas de clic pour révéler — logique pure dès le premier coup. Un nouveau puzzle chaque jour.',
            "seo_beyond_li2": '<strong><a href="/rush">Rush</a> —</strong> Démineur compétitif de 60 secondes. Nettoyez autant de plateaux que possible avant la fin du temps.',
            "seo_beyond_li3": '<strong><a href="/cylinder">Cylindre</a> —</strong> Le plateau classique mais les bords gauche et droit se rejoignent, créant un terrain en boucle continue.',
            "seo_beyond_li4": '<strong><a href="/hexsweeper">Hexsweeper</a> —</strong> Démineur sur une grille hexagonale. Chaque case a six voisins au lieu de huit.',
            "seo_beyond_li5": '<strong><a href="/mosaic">Mosaïque</a> —</strong> Une variante style nonogramme où les indices comptent une zone 3×3 plutôt que l\'adjacence directe.',
            "seo_int_h2": "Démineur Intermédiaire — 16×16, 40 Mines",
            "seo_int_p1": 'L\'intermédiaire est là où le Démineur cesse d\'être un tutoriel pour devenir un jeu. Le plateau passe à <strong>16×16 avec 40 mines</strong> — plus de quatre fois la superficie du débutant, avec une densité de mines d\'environ 15,6 %. Les chaînes de déduction s\'étendent sur plusieurs rangées. Les motifs qui fonctionnaient isolément sur une grille 9×9 se chevauchent maintenant et interagissent. Le bond de difficulté est réel, et c\'est là que la plupart des joueurs stagnent.',
            "seo_int_changes_h2": "Ce qui Change en Intermédiaire",
            "seo_int_changes_li1": '<strong>Chaînes de déduction plus longues.</strong> Une contrainte à un bord du plateau peut se propager sur cinq ou six cases avant de se résoudre. Vous devez maintenir plus d\'états en tête simultanément.',
            "seo_int_changes_li2": '<strong>Murs de chiffres plus denses.</strong> Avec plus de mines par zone, vous verrez plus de 2, 3 et 4 regroupés. Lire les indices qui se chevauchent — déterminer quelles mines sont partagées entre deux contraintes — est la compétence clé ici.',
            "seo_int_changes_li3": '<strong>Les situations 50/50 apparaissent plus souvent.</strong> À densité plus élevée, des ambiguïtés isolées de deux cases surgissent plus fréquemment. Le mode sans devinette les élimine pour un défi de logique pure.',
            "seo_int_changes_li4": '<strong>Les cascades d\'ouverture sont plus petites.</strong> La densité de mines plus élevée signifie que la région ouverte sûre est plus petite en moyenne. Vous passerez plus de temps sur une déduction contrainte plutôt que sur une exploration libre.',
            "seo_int_strat_h2": "Stratégie pour l'Intermédiaire",
            "seo_int_strat_li1": '<strong>Maîtrisez le motif 1-2.</strong> Un <em>1</em> adjacent à un <em>2</em> partageant un voisin inconnu signifie que l\'autre voisin unique du <em>2</em> est une mine. Ce motif apparaît constamment à densité intermédiaire.',
            "seo_int_strat_li2": '<strong>Travaillez les bords en premier.</strong> Les cases de bord ont moins de voisins, rendant leurs contraintes plus serrées et plus faciles à résoudre. Nettoyer les bordures ouvre d\'abord un territoire intérieur sûr.',
            "seo_int_strat_li3": '<strong>Suivez les comptes de mines globalement.</strong> Quarante mines à suivre, mais si vous en avez marqué 35, il n\'en reste que 5. Cette contrainte globale peut résoudre des clusters ambigus que le raisonnement local ne peut pas déchiffrer.',
            "seo_int_strat_li4": '<strong>Utilisez les clics chord agressivement.</strong> La vitesse compte. Une fois qu\'un chiffre est satisfait, double-cliquez pour révéler automatiquement les voisins plutôt que de cliquer manuellement sur chacun.',
            "seo_int_strat_li5": '<strong>Ne sur-marquez pas.</strong> Chaque drapeau est un clic droit et potentiellement un clic gauche gaspillé. Les joueurs rapides à ce niveau marquent seulement quand ils ont besoin du repère visuel pour compléter une chaîne de déduction.',
            "seo_int_compare_h2": "Débutant vs. Intermédiaire vs. Expert",
            "seo_int_compare_li1": '<strong><a href="/">Débutant</a> —</strong> 9×9, 10 mines (~12,3 % densité). Apprenez les bases, visez des records personnels en dessous de 10 secondes.',
            "seo_int_compare_li2": '<strong>Intermédiaire (cette page) —</strong> 16×16, 40 mines (~15,6 %). Le point de contrôle de compétence standard. Sub-60 s est respectable ; sub-30 s est fort.',
            "seo_int_compare_li3": '<strong><a href="/expert">Expert</a> —</strong> 30×16, 99 mines (~20,6 %). La référence définitive. Le territoire des records mondiaux est en dessous de 40 secondes.',
            "seo_int_related_h2": "Modes Associés",
            "seo_int_related_li1": '<strong><a href="/cylinder/intermediate">Cylindre Intermédiaire</a> —</strong> 16×16, 40 mines, mais les bords gauche et droit se connectent. Même densité, topologie différente.',
            "seo_int_related_li2": '<strong><a href="/toroid/intermediate">Toroïde Intermédiaire</a> —</strong> Les quatre bords se connectent. Aucune bordure du tout.',
            "seo_int_related_li3": '<strong><a href="/hexsweeper/intermediate">Hexsweeper Intermédiaire</a> —</strong> Le plateau intermédiaire sur une grille hexagonale.',
            "seo_int_related_li4": '<strong><a href="/tentaizu">Tentaizu</a> —</strong> Un puzzle de déduction japonais avec tous les indices prédisposés. Sans devinette, jamais. Nouveau puzzle quotidien.',
            "seo_exp_h2": "Démineur Expert — 30×16, 99 Mines",
            "seo_exp_p1": 'Expert est la référence définitive du Démineur. Le plateau a <strong>30×16 avec 99 mines</strong> — une densité d\'environ 20,6 %, presque le double du débutant. Pas de cascades d\'ouverture faciles, pas de régions vides généreuses à explorer. Chaque zone du plateau est contrainte, chaque chiffre est un indice nécessitant une attention immédiate. C\'est là que le jeu devient sérieux.',
            "seo_exp_p2": 'Les joueurs de classe mondiale terminent Expert en moins de 40 secondes. Sub-100 secondes est un jalon intermédiaire courant. Si vous êtes nouveau en Expert, attendez-vous à ce que vos premières victoires prennent plusieurs minutes — et attendez-vous à perdre souvent. Apprendre à lire le plateau à densité expert prend du temps, mais la reconnaissance des motifs qui se développe est ce qui sépare les joueurs occasionnels des joueurs sérieux.',
            "seo_exp_hard_h2": "Ce qui Rend l'Expert Difficile",
            "seo_exp_hard_li1": '<strong>Haute densité de mines partout.</strong> À 20,6 %, il y a peu de cases zéro. Presque chaque révélation produit un chiffre. Le plateau ne s\'ouvre jamais comme aux difficultés inférieures.',
            "seo_exp_hard_li2": '<strong>Résolution simultanée de contraintes.</strong> Les plateaux expert présentent régulièrement des configurations où trois, quatre ou cinq cases numérotées partagent des voisins inconnus. Lire ces motifs rapidement — et correctement — est la compétence centrale.',
            "seo_exp_hard_li3": '<strong>Pression de vitesse.</strong> Expert récompense les schémas de clics efficaces. Les joueurs qui passent sous les 60 secondes ont tellement intégré les motifs communs qu\'ils les traitent en fractions de seconde.',
            "seo_exp_hard_li4": '<strong>Devinettes plus fréquentes.</strong> Même sur les plateaux sans devinette, les configurations à densité expert produisent des chaînes plus contraintes. Sans mode sans devinette, certains plateaux contiennent des 50/50 inévitables.',
            "seo_exp_strat_h2": "Stratégie Expert",
            "seo_exp_strat_li1": '<strong>Commencez par n\'importe quelle ouverture.</strong> Votre premier clic est sûr n\'importe où. Beaucoup de joueurs Expert cliquent dans un coin — petite cascade initiale, mais immédiatement en territoire contraint où vous pouvez commencer à lire.',
            "seo_exp_strat_li2": '<strong>Reconnaissez les motifs instantanément.</strong> Le motif 1-2, 1-2-1, 1-2-2-1, les coins isolés, les contraintes satisfaites — à vitesse Expert, la reconnaissance des motifs doit être automatique. Étudiez-les explicitement.',
            "seo_exp_strat_li3": '<strong>Minimisez les drapeaux, maximisez les chords.</strong> Les meilleurs joueurs Expert utilisent souvent une approche "flag au fur et à mesure" voire "sans drapeau", chordant à travers les contraintes révélées sans s\'arrêter pour cliquer droit sur chaque mine.',
            "seo_exp_strat_li4": '<strong>Scannez, ne lisez pas.</strong> N\'analysez pas une case à la fois. Entraînez vos yeux à scanner une région pour les contraintes satisfaites afin de chorter plusieurs cases en un seul balayage.',
            "seo_exp_strat_li5": '<strong>Acceptez les devinettes.</strong> Sur les plateaux non sans-devinette, les 50/50 inévitables font partie d\'Expert. Un bon temps avec une mauvaise devinette n\'est pas un échec — c\'est de la variance. Visez une déduction cohérente sur tout le plateau.',
            "seo_exp_stats_h2": "Statistiques 3BV Expert",
            "seo_exp_stats_p1": 'Les plateaux Expert ont typiquement un 3BV (nombre minimal de clics) entre 100 et 200. Votre 3BV/s (3BV par seconde) et votre efficacité (3BV divisé par les clics réels) apparaissent dans le classement — ils mesurent la qualité de votre jeu au-delà du temps brut. Un temps rapide avec une faible efficacité signifie beaucoup de clics gaspillés. Une haute efficacité avec un temps lent signifie une technique propre, pas encore à la vitesse maximale.',
            "seo_exp_stats_p2": 'Le classement ci-dessus montre les meilleurs scores Expert du jour. Les scores incluent les modes standard et sans devinette — vérifiez le bouton au-dessus du plateau pour changer.',
            "seo_exp_stats_p3": '<a href="/info/3bv">En savoir plus sur le 3BV →</a>',
            "seo_exp_variants_h2": "Variantes Expert",
            "seo_exp_variants_li1": '<strong><a href="/cylinder/expert">Cylindre Expert</a> —</strong> 30×16, 99 mines, avec les bords gauche et droit connectés. La boucle crée des chaînes de déduction sur toute la largeur du plateau.',
            "seo_exp_variants_li2": '<strong><a href="/toroid/expert">Toroïde Expert</a> —</strong> Les quatre bords se connectent. Pas de coins, pas de bords — chaque case a exactement huit voisins.',
            "seo_exp_variants_li3": '<strong><a href="/hexsweeper/expert">Hexsweeper Expert</a> —</strong> Jeu à densité expert sur une grille hexagonale. Six voisins par case au lieu de huit change fondamentalement les calculs.',
            "seo_exp_variants_li4": '<strong><a href="/worldsweeper/expert">Worldsweeper Expert</a> —</strong> Démineur sur un globe 3D. Densité expert répartie sur la surface d\'une sphère.',
        },
    },
    "ko": {
        "anchor": '        "guest_banner_post": "\\uadf8\\ub807\\uc9c0 \\uc54a\\uc73c\\uba74 \\uc810\\uc218\\uac00 \\uc790\\uc815 UTC\\uc5d0 \\uc0ac\\ub77c\\uc9d1\\ub2c8\\ub2e4.",',
        "keys": {
            "seo_beg_h2": "지뢰찾기 온라인 플레이 — 무료",
            "seo_beg_p1": '이것은 초급 보드입니다: <strong>10개의 숨겨진 지뢰가 있는 9×9 격자</strong>. 규칙을 알면 1분 안에 완료할 수 있을 만큼 작고, 게임의 모든 핵심 기술을 가르칠 만큼 큰 클래식 출발점입니다. 왼쪽 클릭으로 셀을 공개합니다. 오른쪽 클릭으로 의심스러운 지뢰에 깃발을 꽂습니다. 모든 지뢰에 깃발이 꽂히고 안전한 셀이 모두 열리면 승리합니다.',
            "seo_beg_p2": '보드의 모든 숫자는 주변 8개 셀에 몇 개의 지뢰가 숨어있는지 알려줍니다. 공개되지 않은 이웃이 두 개뿐인 모서리 셀 옆의 <em>1</em>? 그 두 개 중 하나가 지뢰입니다. <em>0</em>? 근처에 지뢰가 전혀 없음 — 보드가 인접한 빈 셀 전체로 자동 확장됩니다. 게임 전체는 그 숫자를 읽고 지뢰가 어디에 있어야 하는지 좁혀나가는 것입니다.',
            "seo_about_h2": "이 사이트 소개",
            "seo_about_p1": 'minesweeper.org — <strong>Lady Di\'s Mines</strong>라는 별명을 가진 — 는 무료 브라우저 기반 지뢰찾기 플랫폼입니다. 다운로드, 설치, 계정 없이 플레이할 수 있습니다. 클래식 규칙을 존중하면서 현대적 편의를 추가하는 빠르고 깔끔한 구현을 원한 소규모 개발자 팀이 만들었습니다: 일일 리더보드, 추측 없는 모드, 3BV 통계가 포함된 시간 기록, 증가하는 변형 모음.',
            "seo_about_p2": '다이애나와의 연결은 오랫동안 이어온 내부 농담이 브랜드가 된 것입니다: <em>Lady Di\'s Mines</em>. 헌사와 끔찍한 말장난 사이 어딘가. 우리는 그것을 받아들입니다.',
            "seo_diff_h2": "난이도 수준",
            "seo_diff_li1": '<strong>초급 (이 페이지) —</strong> 9×9 격자, 지뢰 10개. ~12.3% 지뢰 밀도. 규칙을 배우고, 근육 기억을 쌓고, 10초 미만 기록을 추구하세요.',
            "seo_diff_li2": '<strong><a href="/intermediate">중급</a> —</strong> 16×16 격자, 지뢰 40개. ~15.6% 지뢰 밀도. 더 긴 체인, 더 복잡한 추론, 대부분의 플레이어가 막히는 곳.',
            "seo_diff_li3": '<strong><a href="/expert">고급</a> —</strong> 30×16 격자, 지뢰 99개. ~20.6% 밀도. 기준점. 세계 기록이 여기에 있습니다. 매 순간 위험합니다.',
            "seo_diff_li4": '<strong><a href="/custom">사용자 정의</a> —</strong> 개인화된 도전을 위해 자신만의 보드 크기와 지뢰 수를 설정하세요.',
            "seo_tips_h2": "빠른 시작 팁",
            "seo_tips_li1": '<strong>먼저 중앙 근처를 클릭하세요.</strong> 첫 번째 클릭은 항상 안전하며 중앙 시작 위치에서 더 큰 연쇄 반응을 일으키는 경향이 있습니다.',
            "seo_tips_li2": '<strong>0을 찾으세요.</strong> 자동으로 확장되는 빈 영역은 무료 정보를 제공하고 작업할 수 있는 번호가 매겨진 많은 가장자리를 드러냅니다.',
            "seo_tips_li3": '<strong>깃발을 꽂을까요, 기억만 할까요?</strong> 모든 지뢰에 깃발을 꽂을 필요가 없습니다 — 깃발은 그저 표시자입니다. 많은 빠른 플레이어는 깃발 꽂기를 건너뛰고 클릭 수를 낮게 유지하기 위해 기억을 사용합니다.',
            "seo_tips_li4": '<strong>추측 없는 모드를 사용하세요</strong> 50/50 상황에서 지는 것이 싫다면. 항상 논리적으로 해결 가능한 보드를 생성합니다.',
            "seo_tips_li5": '<strong>더 빨리 가려면 코드를 사용하세요.</strong> 공개된 숫자를 더블 클릭하면 올바른 수의 깃발이 배치된 경우 모든 이웃이 자동으로 공개됩니다. 자신감이 생겼을 때 보드를 정리하는 가장 빠른 방법입니다.',
            "seo_beyond_h2": "클래식 보드를 넘어서",
            "seo_beyond_p": "초급이 쉬워지면 여기에 더 많은 것이 있습니다:",
            "seo_beyond_li1": '<strong><a href="/tentaizu">Tentaizu</a> —</strong> 일본 별자리 퍼즐. 모든 단서가 미리 배치되어 있어 공개를 위해 클릭할 필요 없이 첫 번째 수부터 순수한 논리입니다. 매일 새로운 퍼즐.',
            "seo_beyond_li2": '<strong><a href="/rush">Rush</a> —</strong> 60초 경쟁 지뢰찾기. 시간이 다 되기 전에 가능한 한 많은 보드를 클리어하세요.',
            "seo_beyond_li3": '<strong><a href="/cylinder">Cylinder</a> —</strong> 클래식 보드지만 왼쪽과 오른쪽 가장자리가 연결되어 매끄러운 감싸기 필드를 만듭니다.',
            "seo_beyond_li4": '<strong><a href="/hexsweeper">Hexsweeper</a> —</strong> 육각형 격자의 지뢰찾기. 각 셀에는 8개 대신 6개의 이웃이 있습니다.',
            "seo_beyond_li5": '<strong><a href="/mosaic">Mosaic</a> —</strong> 단서가 직접 인접성이 아닌 3×3 영역을 세는 노노그램 스타일 변형.',
            "seo_int_h2": "중급 지뢰찾기 — 16×16, 지뢰 40개",
            "seo_int_p1": '중급은 지뢰찾기가 튜토리얼에서 진짜 게임이 되는 곳입니다. 보드가 <strong>16×16에 지뢰 40개</strong>로 커집니다 — 초급의 4배 이상 면적에 지뢰 밀도가 약 15.6%까지 올라갑니다. 추론 체인이 여러 행에 걸쳐 뻗어나갑니다. 9×9 격자에서 고립되어 작동하던 패턴이 이제 겹치고 상호작용합니다. 난이도 차이는 실제이며, 대부분의 플레이어가 여기서 정체됩니다.',
            "seo_int_changes_h2": "중급에서 달라지는 것",
            "seo_int_changes_li1": '<strong>더 긴 추론 체인.</strong> 보드 한쪽 끝의 제약이 해결되기 전에 5~6개 셀을 거쳐 전파될 수 있습니다. 동시에 더 많은 상태를 머릿속에 유지해야 합니다.',
            "seo_int_changes_li2": '<strong>더 조밀한 숫자 벽.</strong> 면적당 지뢰가 많아지면 2, 3, 4가 모여있는 것을 더 많이 보게 됩니다. 겹치는 단서 읽기 — 두 제약 사이에서 어떤 지뢰가 공유되는지 파악하기 — 가 여기서의 핵심 기술입니다.',
            "seo_int_changes_li3": '<strong>50/50 상황이 더 자주 발생합니다.</strong> 밀도가 높을수록 고립된 두 셀 모호성이 더 자주 발생합니다. 순수한 논리 도전을 원하면 추측 없는 모드가 이를 제거합니다.',
            "seo_int_changes_li4": '<strong>오프닝 연쇄 반응이 더 작습니다.</strong> 더 높은 지뢰 밀도는 평균적으로 안전한 열린 영역이 더 작음을 의미합니다. 자유로운 탐험보다 제약된 추론에 더 많은 시간을 보내게 됩니다.',
            "seo_int_strat_h2": "중급 전략",
            "seo_int_strat_li1": '<strong>1-2 패턴을 마스터하세요.</strong> 미지의 이웃을 공유하는 <em>2</em>에 인접한 <em>1</em>은 <em>2</em>의 다른 고유한 이웃이 지뢰임을 의미합니다. 이 패턴은 중간 밀도에서 지속적으로 나타납니다.',
            "seo_int_strat_li2": '<strong>먼저 가장자리를 작업하세요.</strong> 가장자리 셀은 이웃이 더 적어 제약이 더 촘촘하고 해결하기 쉽습니다. 먼저 경계를 정리하면 안전한 내부 영역이 열립니다.',
            "seo_int_strat_li3": '<strong>지뢰 수를 전역적으로 추적하세요.</strong> 40개의 지뢰를 추적하는 것은 많지만, 35개에 깃발을 꽂았다면 5개만 남습니다. 그 전역 제약이 로컬 추론으로는 풀 수 없는 모호한 클러스터를 해결할 수 있습니다.',
            "seo_int_strat_li4": '<strong>코드 클릭을 적극적으로 사용하세요.</strong> 속도가 중요합니다. 숫자가 충족되면 각각 수동으로 클릭하는 대신 더블 클릭으로 이웃을 자동 공개하세요.',
            "seo_int_strat_li5": '<strong>과도하게 깃발을 꽂지 마세요.</strong> 모든 깃발은 오른쪽 클릭이고 잠재적으로 낭비된 왼쪽 클릭입니다. 이 레벨의 빠른 플레이어는 추론 체인을 완성하기 위한 시각적 마커가 필요할 때만 깃발을 꽂습니다.',
            "seo_int_compare_h2": "초급 vs. 중급 vs. 고급",
            "seo_int_compare_li1": '<strong><a href="/">초급</a> —</strong> 9×9, 지뢰 10개 (~12.3% 밀도). 기본기를 배우고 10초 미만의 개인 최고 기록을 추구하세요.',
            "seo_int_compare_li2": '<strong>중급 (이 페이지) —</strong> 16×16, 지뢰 40개 (~15.6%). 표준 기술 확인점. 60초 미만은 괜찮음; 30초 미만은 강함.',
            "seo_int_compare_li3": '<strong><a href="/expert">고급</a> —</strong> 30×16, 지뢰 99개 (~20.6%). 최종 기준점. 세계 기록 영역은 40초 미만.',
            "seo_int_related_h2": "관련 모드",
            "seo_int_related_li1": '<strong><a href="/cylinder/intermediate">Cylinder 중급</a> —</strong> 16×16, 지뢰 40개, 왼쪽과 오른쪽 가장자리가 연결됩니다. 같은 밀도, 다른 위상.',
            "seo_int_related_li2": '<strong><a href="/toroid/intermediate">Toroid 중급</a> —</strong> 네 가장자리 모두 연결됩니다. 경계 없음.',
            "seo_int_related_li3": '<strong><a href="/hexsweeper/intermediate">Hexsweeper 중급</a> —</strong> 육각형 격자의 중급 보드.',
            "seo_int_related_li4": '<strong><a href="/tentaizu">Tentaizu</a> —</strong> 모든 단서가 미리 배치된 일본 추론 퍼즐. 절대 추측 없음. 매일 새로운 퍼즐.',
            "seo_exp_h2": "고급 지뢰찾기 — 30×16, 지뢰 99개",
            "seo_exp_p1": '고급은 지뢰찾기의 최종 기준점입니다. 보드는 <strong>30×16에 지뢰 99개</strong> — 지뢰 밀도 약 20.6%로 초급의 거의 두 배입니다. 쉬운 오프닝 연쇄 반응도, 탐험할 너그러운 빈 영역도 없습니다. 보드의 모든 영역이 제약되어 있고, 모든 숫자는 즉각적인 주의가 필요한 단서입니다. 여기서 게임이 진지해집니다.',
            "seo_exp_p2": '세계 수준의 플레이어는 고급을 40초 미만에 완료합니다. 100초 미만은 일반적인 중간 마일스톤입니다. 고급이 처음이라면 첫 번째 클리어가 몇 분이 걸릴 것을 예상하세요 — 그리고 자주 질 것을 예상하세요. 고급 밀도에서 보드를 읽는 것을 배우는 데는 시간이 걸리지만, 발전하는 패턴 인식이 캐주얼 플레이어와 진지한 플레이어를 구분하는 것입니다.',
            "seo_exp_hard_h2": "고급을 어렵게 만드는 것",
            "seo_exp_hard_li1": '<strong>어디서나 높은 지뢰 밀도.</strong> 20.6%에서 제로 셀이 거의 없습니다. 거의 모든 공개가 숫자를 생성합니다. 낮은 난이도에서처럼 보드가 열리지 않습니다.',
            "seo_exp_hard_li2": '<strong>동시 제약 해결.</strong> 고급 보드는 세 개, 네 개 또는 다섯 개의 번호가 매겨진 셀이 미지의 이웃을 공유하는 구성을 정기적으로 제시합니다. 이런 패턴을 빠르게 — 그리고 올바르게 — 읽는 것이 핵심 기술입니다.',
            "seo_exp_hard_li3": '<strong>속도 압박.</strong> 고급은 효율적인 클릭 패턴에 보상을 줍니다. 60초 미만을 기록하는 플레이어는 일반적인 패턴을 너무 철저히 내면화하여 초 단위로 처리합니다.',
            "seo_exp_hard_li4": '<strong>더 잦은 추측.</strong> 추측 없는 보드에서도 고급 밀도 배치는 더 제약된 체인을 만듭니다. 추측 없는 모드 없이는 일부 보드에 피할 수 없는 50/50이 포함됩니다.',
            "seo_exp_strat_h2": "고급 전략",
            "seo_exp_strat_li1": '<strong>어떤 오프닝으로도 시작하세요.</strong> 첫 번째 클릭은 어디서나 안전합니다. 많은 고급 플레이어는 모서리를 클릭합니다 — 초기 연쇄 반응은 작지만 즉시 제약된 영역에 들어가 읽기 시작할 수 있습니다.',
            "seo_exp_strat_li2": '<strong>패턴을 즉시 인식하세요.</strong> 1-2 패턴, 1-2-1, 1-2-2-1, 고립된 모서리, 완료된 제약 — 고급 속도에서 패턴 인식은 자동적이어야 합니다. 명시적으로 공부하세요.',
            "seo_exp_strat_li3": '<strong>깃발을 최소화하고 코드를 극대화하세요.</strong> 최고의 고급 플레이어는 종종 "진행하면서 깃발" 또는 "깃발 없음" 접근 방식을 사용하여 각 지뢰에 오른쪽 클릭하지 않고 공개된 제약을 통해 코딩합니다.',
            "seo_exp_strat_li4": '<strong>스캔하세요, 읽지 마세요.</strong> 한 번에 한 셀을 분석하지 마세요. 완료된 제약을 위해 영역을 스캔하도록 눈을 훈련시켜 한 번의 스윕으로 여러 셀을 코딩할 수 있게 하세요.',
            "seo_exp_strat_li5": '<strong>추측을 받아들이세요.</strong> 추측 없는 보드가 아닌 경우 피할 수 없는 50/50은 고급의 일부입니다. 나쁜 추측으로 좋은 시간을 내는 것은 실패가 아닙니다 — 변동성입니다. 보드 전체에서 일관된 추론을 추구하고 확률이 시간이 지남에 따라 작동하도록 하세요.',
            "seo_exp_stats_h2": "고급 3BV 통계",
            "seo_exp_stats_p1": '고급 보드는 일반적으로 3BV(최소 클릭 수)가 100~200 사이입니다. 3BV/s(초당 3BV)와 효율(실제 클릭으로 나눈 3BV)은 리더보드에 나타납니다 — 원시 시간을 넘어 플레이 품질을 측정합니다. 낮은 효율의 빠른 시간은 많은 낭비 클릭을 의미합니다. 느린 시간의 높은 효율은 깔끔한 기술을 의미하며 아직 최고 속도에 도달하지 못했음을 나타냅니다.',
            "seo_exp_stats_p2": '위의 리더보드는 오늘의 최고 고급 점수를 보여줍니다. 점수에는 표준 및 추측 없는 모드 모두 포함됩니다 — 보드 위의 토글을 확인하여 전환하세요.',
            "seo_exp_stats_p3": '<a href="/info/3bv">3BV에 대해 더 알아보기 →</a>',
            "seo_exp_variants_h2": "고급 변형",
            "seo_exp_variants_li1": '<strong><a href="/cylinder/expert">Cylinder 고급</a> —</strong> 30×16, 지뢰 99개, 왼쪽과 오른쪽 가장자리가 연결됩니다. 감싸기는 보드의 전체 너비에 걸친 추론 체인을 만듭니다.',
            "seo_exp_variants_li2": '<strong><a href="/toroid/expert">Toroid 고급</a> —</strong> 네 가장자리 모두 연결됩니다. 모서리도 가장자리도 없음 — 모든 셀에 정확히 8개의 이웃이 있습니다.',
            "seo_exp_variants_li3": '<strong><a href="/hexsweeper/expert">Hexsweeper 고급</a> —</strong> 육각형 격자의 고급 밀도 게임. 셀당 8개 대신 6개의 이웃은 수학을 근본적으로 변화시킵니다.',
            "seo_exp_variants_li4": '<strong><a href="/worldsweeper/expert">Worldsweeper 고급</a> —</strong> 3D 지구본의 지뢰찾기. 구 표면에 분산된 고급 밀도.',
        },
    },
}


def apply_locale(content, locale_code, anchor, keys):
    if anchor not in content:
        print(f"ERROR: anchor not found for {locale_code}")
        print(f"  Looking for: {repr(anchor[:80])}")
        return content, False
    insert = '\n'
    for k, v in keys.items():
        safe = v.replace('\\', '\\\\').replace('"', '\\"')
        insert += f'        "{k}": "{safe}",\n'
    new = content.replace(anchor, anchor + insert, 1)
    print(f"OK: {locale_code} — inserted {len(keys)} keys")
    return new, True


with open('/Users/cross/git/minesweeper.org/translations.py', 'r', encoding='utf-8') as f:
    content = f.read()

for locale_code, data in LOCALES.items():
    content, ok = apply_locale(content, locale_code, data["anchor"], data["keys"])

with open('/Users/cross/git/minesweeper.org/translations.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Done.")
