# -*- coding: utf-8 -*-
"""Insert missing game_* stat/UI keys into translations.py.
Anchor: game_view_lb (present in all language sections).
Usage: python scripts/insert_game.py <lang>
"""
import ast, sys, re, os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRANS = os.path.join(REPO, "translations.py")
ANCHOR = "game_view_lb"

def esc(s):
    s = s.replace("\\", "\\\\")
    s = s.replace('"', '\\"')
    return s

def build_block(keys, existing):
    lines = [f'        "{k}": "{esc(v)}",' for k, v in keys.items() if k not in existing]
    return ("\n".join(lines) + "\n") if lines else ""

LANGS = {}

LANGS["eo"] = {
    "game_3bv_tip": "3BV estas la minimuma nombro da klakoj necesaj por plenumi tabelon sen uzi flagojn.",
    "game_3bvs_tip": "3BV je sekundo — rapido de plenumi la ludon. Pli alta estas pli bone.",
    "game_eff_tip": "Efikeco: 3BV dividita per klakoj faritaj. Malpli da klakoj = pli alta efikeco.",
    "game_hash_col": "Haxso",
    "game_ios_banner": "Elshxutu la senpagan Minesweeper-aplikajon",
    "game_ios_for": "por iPhone kaj iPad.",
    "game_session": "Sesio",
    "game_share_link": "🔗 Kunhavigi cxi tiun ludon",
    "game_stat_avg_eff": "Mez. efikeco",
    "game_stat_best": "Plej bona",
    "game_stat_cps": "klakoj/s",
    "game_stat_lost": "perdita",
    "game_stat_won": "venkita",
}
LANGS["de"] = {
    "game_3bv_tip": "3BV ist die Mindestanzahl an Klicks, um ein Feld ohne Flaggen abzuschliessen.",
    "game_3bvs_tip": "3BV pro Sekunde — Geschwindigkeit des Spielabschlusses. Hoher ist besser.",
    "game_eff_tip": "Effizienz: 3BV geteilt durch geleistete Klicks. Weniger Klicks = hohere Effizienz.",
    "game_hash_col": "Hash",
    "game_ios_banner": "Lade die kostenlose Minesweeper-App herunter",
    "game_ios_for": "fur iPhone & iPad.",
    "game_session": "Sitzung",
    "game_share_link": "🔗 Dieses Spiel teilen",
    "game_stat_avg_eff": "Durchschn. Eff.",
    "game_stat_best": "Bestzeit",
    "game_stat_cps": "Klicks/s",
    "game_stat_lost": "verloren",
    "game_stat_won": "gewonnen",
}
LANGS["es"] = {
    "game_3bv_tip": "3BV es el numero minimo de clics necesarios para completar un tablero sin usar banderas.",
    "game_3bvs_tip": "3BV por segundo — velocidad para completar el juego. Mayor es mejor.",
    "game_eff_tip": "Eficiencia: 3BV dividido por los clics realizados. Menos clics = mayor eficiencia.",
    "game_hash_col": "Hash",
    "game_ios_banner": "Descarga la aplicacion gratuita de Minesweeper",
    "game_ios_for": "para iPhone y iPad.",
    "game_session": "Sesion",
    "game_share_link": "🔗 Compartir este juego",
    "game_stat_avg_eff": "Ef. media",
    "game_stat_best": "Mejor",
    "game_stat_cps": "clics/s",
    "game_stat_lost": "perdidos",
    "game_stat_won": "ganados",
}
LANGS["fr"] = {
    "game_3bv_tip": "3BV est le nombre minimum de clics necessaires pour terminer un plateau sans utiliser de drapeaux.",
    "game_3bvs_tip": "3BV par seconde — vitesse de completion du jeu. Plus eleve est mieux.",
    "game_eff_tip": "Efficacite : 3BV divise par les clics effectues. Moins de clics = plus grande efficacite.",
    "game_hash_col": "Hachage",
    "game_ios_banner": "Telecharger l'application Demineur gratuite",
    "game_ios_for": "pour iPhone et iPad.",
    "game_session": "Session",
    "game_share_link": "🔗 Partager ce jeu",
    "game_stat_avg_eff": "Eff. moy.",
    "game_stat_best": "Meilleur",
    "game_stat_cps": "clics/s",
    "game_stat_lost": "perdu",
    "game_stat_won": "gagne",
}
LANGS["uk"] = {
    "game_3bv_tip": "3BV — мінімальна кількість кліків для завершення поля без використання прапорців.",
    "game_3bvs_tip": "3BV на секунду — швидкість завершення гри. Вище — краще.",
    "game_eff_tip": "Ефективність: 3BV поділено на виконані кліки. Менше кліків = вища ефективність.",
    "game_hash_col": "Хеш",
    "game_ios_banner": "Завантажте безкоштовний додаток Сапер",
    "game_ios_for": "для iPhone та iPad.",
    "game_session": "Сесія",
    "game_share_link": "🔗 Поділитися цією грою",
    "game_stat_avg_eff": "Сер. ефект.",
    "game_stat_best": "Найкращий",
    "game_stat_cps": "кліків/с",
    "game_stat_lost": "програно",
    "game_stat_won": "виграно",
}
LANGS["ru"] = {
    "game_3bv_tip": "3BV — минимальное количество кликов для завершения поля без использования флажков.",
    "game_3bvs_tip": "3BV в секунду — скорость завершения игры. Выше — лучше.",
    "game_eff_tip": "Эффективность: 3BV делённое на выполненные клики. Меньше кликов = выше эффективность.",
    "game_hash_col": "Хэш",
    "game_ios_banner": "Скачайте бесплатное приложение Сапёр",
    "game_ios_for": "для iPhone и iPad.",
    "game_session": "Сессия",
    "game_share_link": "🔗 Поделиться этой игрой",
    "game_stat_avg_eff": "Ср. эффект.",
    "game_stat_best": "Лучший",
    "game_stat_cps": "кликов/с",
    "game_stat_lost": "проиграно",
    "game_stat_won": "выиграно",
}
LANGS["pt"] = {
    "game_3bv_tip": "3BV e o numero minimo de cliques necessarios para completar um campo sem usar bandeiras.",
    "game_3bvs_tip": "3BV por segundo — velocidade de conclusao do jogo. Mais alto e melhor.",
    "game_eff_tip": "Eficiencia: 3BV dividido pelos cliques realizados. Menos cliques = maior eficiencia.",
    "game_hash_col": "Hash",
    "game_ios_banner": "Descarregue a aplicacao gratuita Campo Minado",
    "game_ios_for": "para iPhone e iPad.",
    "game_session": "Sessao",
    "game_share_link": "🔗 Partilhar este jogo",
    "game_stat_avg_eff": "Ef. media",
    "game_stat_best": "Melhor",
    "game_stat_cps": "cliques/s",
    "game_stat_lost": "perdido",
    "game_stat_won": "ganho",
}
LANGS["it"] = {
    "game_3bv_tip": "3BV e il numero minimo di clic necessari per completare un campo senza usare bandiere.",
    "game_3bvs_tip": "3BV al secondo — velocita di completamento del gioco. Piu alto e meglio.",
    "game_eff_tip": "Efficienza: 3BV diviso per i clic effettuati. Meno clic = maggiore efficienza.",
    "game_hash_col": "Hash",
    "game_ios_banner": "Scarica l'app gratuita Puntaspilli",
    "game_ios_for": "per iPhone e iPad.",
    "game_session": "Sessione",
    "game_share_link": "🔗 Condividi questo gioco",
    "game_stat_avg_eff": "Ef. media",
    "game_stat_best": "Migliore",
    "game_stat_cps": "clic/s",
    "game_stat_lost": "perso",
    "game_stat_won": "vinto",
}
LANGS["ko"] = {
    "game_3bv_tip": "3BV는 깃발 없이 보드를 완료하는 데 필요한 최소 클릭 수입니다.",
    "game_3bvs_tip": "초당 3BV — 게임 완료 속도. 높을수록 좋습니다.",
    "game_eff_tip": "효율성: 3BV를 수행한 클릭 수로 나눈 값. 클릭 수가 적을수록 = 효율성이 높습니다.",
    "game_hash_col": "해시",
    "game_ios_banner": "무료 지뢰찾기 앱 다운로드",
    "game_ios_for": "iPhone 및 iPad용.",
    "game_session": "세션",
    "game_share_link": "🔗 이 게임 공유",
    "game_stat_avg_eff": "평균 효율",
    "game_stat_best": "최고",
    "game_stat_cps": "클릭/초",
    "game_stat_lost": "패배",
    "game_stat_won": "승리",
}
LANGS["ja"] = {
    "game_3bv_tip": "3BVはフラグを使わずにボードを完了するために必要な最小クリック数です。",
    "game_3bvs_tip": "1秒あたりの3BV — ゲーム完了速度。高いほど良い。",
    "game_eff_tip": "効率：3BVを行ったクリック数で割った値。クリック数が少ない = 効率が高い。",
    "game_hash_col": "ハッシュ",
    "game_ios_banner": "無料のマインスイーパーアプリをダウンロード",
    "game_ios_for": "iPhone・iPad用。",
    "game_session": "セッション",
    "game_share_link": "🔗 このゲームをシェア",
    "game_stat_avg_eff": "平均効率",
    "game_stat_best": "ベスト",
    "game_stat_cps": "クリック/秒",
    "game_stat_lost": "敗北",
    "game_stat_won": "勝利",
}
LANGS["zh"] = {
    "game_3bv_tip": "3BV 是不使用旗帜完成棋盘所需的最少点击次数。",
    "game_3bvs_tip": "每秒 3BV — 游戏完成速度。越高越好。",
    "game_eff_tip": "效率：3BV 除以点击次数。点击越少 = 效率越高。",
    "game_hash_col": "哈希",
    "game_ios_banner": "下载免费的扫雷应用",
    "game_ios_for": "适用于 iPhone 和 iPad。",
    "game_session": "本局统计",
    "game_share_link": "🔗 分享此游戏",
    "game_stat_avg_eff": "平均效率",
    "game_stat_best": "最佳",
    "game_stat_cps": "次/秒",
    "game_stat_lost": "输",
    "game_stat_won": "赢",
}
LANGS["zh-hant"] = {
    "game_3bv_tip": "3BV 是不使用旗幟完成棋盤所需的最少點擊次數。",
    "game_3bvs_tip": "每秒 3BV — 遊戲完成速度。越高越好。",
    "game_eff_tip": "效率：3BV 除以點擊次數。點擊越少 = 效率越高。",
    "game_hash_col": "雜湊",
    "game_ios_banner": "下載免費的踩地雷應用程式",
    "game_ios_for": "適用於 iPhone 和 iPad。",
    "game_session": "本局統計",
    "game_share_link": "🔗 分享此遊戲",
    "game_stat_avg_eff": "平均效率",
    "game_stat_best": "最佳",
    "game_stat_cps": "次/秒",
    "game_stat_lost": "輸",
    "game_stat_won": "贏",
}
LANGS["pl"] = {
    "game_3bv_tip": "3BV to minimalna liczba klikniec potrzebna do ukonczenia planszy bez uzycia flag.",
    "game_3bvs_tip": "3BV na sekunde — szybkosc ukonczenia gry. Wyzszy jest lepszy.",
    "game_eff_tip": "Wydajnosc: 3BV podzielone przez wykonane klikniecia. Mniej klikniec = wieksza wydajnosc.",
    "game_hash_col": "Hash",
    "game_ios_banner": "Pobierz darmowa aplikacje Saper",
    "game_ios_for": "na iPhone i iPad.",
    "game_session": "Sesja",
    "game_share_link": "🔗 Udostepnij te gre",
    "game_stat_avg_eff": "Sr. wydajn.",
    "game_stat_best": "Najlepszy",
    "game_stat_cps": "klikniec/s",
    "game_stat_lost": "przegrane",
    "game_stat_won": "wygrane",
}
LANGS["tl"] = {
    "game_3bv_tip": "Ang 3BV ay ang minimum na bilang ng mga pag-click na kailangan upang makumpleto ang isang board nang walang paggamit ng mga bandila.",
    "game_3bvs_tip": "3BV bawat segundo — bilis ng pagkumpleto ng laro. Mas mataas ay mas magaling.",
    "game_eff_tip": "Kahusayan: 3BV na hinati sa mga pag-click na ginawa. Mas kaunting pag-click = mas mataas na kahusayan.",
    "game_hash_col": "Hash",
    "game_ios_banner": "I-download ang libreng Minesweeper app",
    "game_ios_for": "para sa iPhone at iPad.",
    "game_session": "Sesyon",
    "game_share_link": "🔗 Ibahagi ang larong ito",
    "game_stat_avg_eff": "Avg kahusayan",
    "game_stat_best": "Pinakamahusay",
    "game_stat_cps": "pag-click/s",
    "game_stat_lost": "natalo",
    "game_stat_won": "nanalo",
}
LANGS["pgl"] = {
    "game_3bv_tip": "3BV isway ethay inimummay umbernay ofway icksclay equiredray otay ompleteay away oardbay ithoutway usingway agsflay.",
    "game_3bvs_tip": "3BV erpay econdsay — eedspay ofway ompletingcay ethay amegay. Igherhay isway etterbay.",
    "game_eff_tip": "Iciencyeffay: 3BV ividedday ybay icksclay erformedpay. Ewerfay icksclay = igherhay iciencyeffay.",
    "game_hash_col": "Ashhay",
    "game_ios_banner": "Ownloadday ethay eefray Inesweepermay appway",
    "game_ios_for": "orfay iPhone andway iPad.",
    "game_session": "Essionsay",
    "game_share_link": "🔗 Areshay isthay amegay",
    "game_stat_avg_eff": "Avgway effway",
    "game_stat_best": "Estbay",
    "game_stat_cps": "icksclay/sway",
    "game_stat_lost": "ostlay",
    "game_stat_won": "onway",
}
LANGS["nl"] = {
    "game_3bv_tip": "3BV is het minimale aantal klikken dat nodig is om een veld te voltooien zonder vlaggen te gebruiken.",
    "game_3bvs_tip": "3BV per seconde — snelheid van het voltooien van het spel. Hoger is beter.",
    "game_eff_tip": "Efficiëntie: 3BV gedeeld door uitgevoerde klikken. Minder klikken = hogere efficiëntie.",
    "game_hash_col": "Hash",
    "game_ios_banner": "Download de gratis Mijnenveger-app",
    "game_ios_for": "voor iPhone en iPad.",
    "game_session": "Sessie",
    "game_share_link": "🔗 Dit spel delen",
    "game_stat_avg_eff": "Gem. eff.",
    "game_stat_best": "Beste",
    "game_stat_cps": "klikken/s",
    "game_stat_lost": "verloren",
    "game_stat_won": "gewonnen",
}

# ── insertion logic ───────────────────────────────────────────────────────────
def insert_lang(lang):
    with open(TRANS, encoding="utf-8") as f:
        lines = f.readlines()
    section_starts = {}
    for i, line in enumerate(lines):
        m = re.match(r'\s*"([a-z\-]+)"\s*:\s*\{', line)
        if m: section_starts[m.group(1)] = i
    if lang not in section_starts:
        print(f"ERROR: language '{lang}' not found"); return False
    langs_list = list(section_starts.keys())
    lang_idx = langs_list.index(lang)
    section_start = section_starts[lang]
    section_end = section_starts[langs_list[lang_idx+1]] if lang_idx+1 < len(langs_list) else len(lines)
    existing = set()
    for i in range(section_start, section_end):
        m = re.match(r'\s*"([^"]+)"\s*:', lines[i])
        if m: existing.add(m.group(1))
    insert_after = None
    for i in range(section_start, section_end):
        if f'"{ANCHOR}"' in lines[i]:
            insert_after = i; break
    if insert_after is None:
        print(f"ERROR: anchor '{ANCHOR}' not found in '{lang}'"); return False
    block = build_block(LANGS[lang], existing)
    if not block.strip():
        print(f"SKIP: all keys already present in '{lang}'"); return True
    new_lines = lines[:insert_after+1] + [block] + lines[insert_after+1:]
    new_src = "".join(new_lines)
    try:
        ast.parse(new_src)
    except SyntaxError as e:
        print(f"SYNTAX ERROR in '{lang}': {e}"); return False
    with open(TRANS, "w", encoding="utf-8") as f:
        f.write(new_src)
    added = len([k for k in LANGS[lang] if k not in existing])
    print(f"OK: {added} keys inserted for '{lang}' after line {insert_after+1}")
    return True

if __name__ == "__main__":
    if len(sys.argv) > 1:
        sys.exit(0 if insert_lang(sys.argv[1]) else 1)
    else:
        # Run all
        for lang in LANGS:
            insert_lang(lang)
