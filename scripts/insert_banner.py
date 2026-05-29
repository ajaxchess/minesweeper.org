# -*- coding: utf-8 -*-
"""Seasonal banner (banner_*) translations — all 16 non-nl languages.
Inserts 5 keys after the anchor key 'game_new_game' in each language section.
"""
import sys, io, re, ast, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRANS_FILE = os.path.join(REPO, 'translations.py')
ANCHOR = "game_new_game"


def esc(s):
    s = s.replace("\\", "\\\\")
    s = s.replace('"', '\\"')
    return s


def build_block(keys, existing):
    lines = [f'        "{k}": "{esc(v)}",' for k, v in keys.items() if k not in existing]
    return ("\n".join(lines) + "\n") if lines else ""


LANGS = {
    "eo": {
        "banner_diana_birthday": "Feliĉan naskiĝtagon, Diana, Princino de Kimrio!",
        "banner_equinox": "Por festi la Ekvinokson, bonvolu ĝui la Tentaizu-temon",
        "banner_mexico_cinco": "¡Feliz Cinco de Mayo! 🇲🇽",
        "banner_mexico_independence": "¡Viva México! 🇲🇽 Feliĉan Tagon de Sendependeco de Meksiko!",
        "banner_solstice": "La Tentaizu-temo estas por festi la solsticon!",
    },
    "de": {
        "banner_diana_birthday": "Alles Gute zum Geburtstag, Diana, Prinzessin von Wales!",
        "banner_equinox": "Zu Ehren der Tagundnachtgleiche – genieße das Tentaizu-Theme",
        "banner_mexico_cinco": "¡Feliz Cinco de Mayo! 🇲🇽",
        "banner_mexico_independence": "¡Viva México! 🇲🇽 Frohes mexikanisches Unabhängigkeitsfest!",
        "banner_solstice": "Das Tentaizu-Theme feiert die Sonnenwende!",
    },
    "es": {
        "banner_diana_birthday": "¡Feliz cumpleaños, Diana, Princesa de Gales!",
        "banner_equinox": "En celebración del Equinoccio, disfruta del tema Tentaizu",
        "banner_mexico_cinco": "¡Feliz Cinco de Mayo! 🇲🇽",
        "banner_mexico_independence": "¡Viva México! 🇲🇽 ¡Feliz Día de la Independencia de México!",
        "banner_solstice": "¡El tema Tentaizu celebra el solsticio!",
    },
    "fr": {
        "banner_diana_birthday": "Joyeux anniversaire, Diana, Princesse de Galles !",
        "banner_equinox": "En célébration de l'Équinoxe, profitez du thème Tentaizu",
        "banner_mexico_cinco": "¡Feliz Cinco de Mayo! 🇲🇽",
        "banner_mexico_independence": "¡Viva México! 🇲🇽 Bonne fête de l'Indépendance du Mexique !",
        "banner_solstice": "Le thème Tentaizu est en célébration du solstice !",
    },
    "uk": {
        "banner_diana_birthday": "З днем народження, Діана, Принцеса Уельська!",
        "banner_equinox": "На честь рівнодення, насолоджуйтесь темою Tentaizu",
        "banner_mexico_cinco": "¡Feliz Cinco de Mayo! 🇲🇽",
        "banner_mexico_independence": "¡Viva México! 🇲🇽 З Днем незалежності Мексики!",
        "banner_solstice": "Тема Tentaizu — на честь сонцестояння!",
    },
    "ru": {
        "banner_diana_birthday": "С днём рождения, Диана, Принцесса Уэльская!",
        "banner_equinox": "В честь равноденствия, насладитесь темой Tentaizu",
        "banner_mexico_cinco": "¡Feliz Cinco de Mayo! 🇲🇽",
        "banner_mexico_independence": "¡Viva México! 🇲🇽 С Днём независимости Мексики!",
        "banner_solstice": "Тема Tentaizu в честь солнцестояния!",
    },
    "pt": {
        "banner_diana_birthday": "Feliz aniversário, Diana, Princesa de Gales!",
        "banner_equinox": "Em celebração do Equinócio, aproveite o tema Tentaizu",
        "banner_mexico_cinco": "¡Feliz Cinco de Mayo! 🇲🇽",
        "banner_mexico_independence": "¡Viva México! 🇲🇽 Feliz Dia da Independência do México!",
        "banner_solstice": "O tema Tentaizu está em celebração do solstício!",
    },
    "it": {
        "banner_diana_birthday": "Buon compleanno, Diana, Principessa del Galles!",
        "banner_equinox": "In celebrazione dell'Equinozio, goditi il tema Tentaizu",
        "banner_mexico_cinco": "¡Feliz Cinco de Mayo! 🇲🇽",
        "banner_mexico_independence": "¡Viva México! 🇲🇽 Buona Festa dell'Indipendenza del Messico!",
        "banner_solstice": "Il tema Tentaizu festeggia il solstizio!",
    },
    "ko": {
        "banner_diana_birthday": "생일 축하해요, 웨일스의 공주 다이애나!",
        "banner_equinox": "춘분·추분을 기념하여 Tentaizu 테마를 즐겨보세요",
        "banner_mexico_cinco": "¡Feliz Cinco de Mayo! 🇲🇽",
        "banner_mexico_independence": "¡Viva México! 🇲🇽 멕시코 독립기념일 축하해요!",
        "banner_solstice": "Tentaizu 테마는 하지·동지를 기념합니다!",
    },
    "ja": {
        "banner_diana_birthday": "お誕生日おめでとうございます、ウェールズ公妃ダイアナ！",
        "banner_equinox": "春分・秋分のお祝いとして、Tentaizuテーマをお楽しみください",
        "banner_mexico_cinco": "¡Feliz Cinco de Mayo! 🇲🇽",
        "banner_mexico_independence": "¡Viva México! 🇲🇽 メキシコ独立記念日おめでとうございます！",
        "banner_solstice": "Tentaizuテーマは夏至・冬至のお祝いです！",
    },
    "zh": {
        "banner_diana_birthday": "生日快乐，戴安娜，威尔士王妃！",
        "banner_equinox": "为庆祝春分/秋分，请欣赏天体主题",
        "banner_mexico_cinco": "¡Feliz Cinco de Mayo! 🇲🇽",
        "banner_mexico_independence": "¡Viva México! 🇲🇽 墨西哥独立日快乐！",
        "banner_solstice": "天体主题是庆祝夏至/冬至的！",
    },
    "zh-hant": {
        "banner_diana_birthday": "生日快樂，黛安娜，威爾斯王妃！",
        "banner_equinox": "為慶祝春分/秋分，請欣賞天體主題",
        "banner_mexico_cinco": "¡Feliz Cinco de Mayo! 🇲🇽",
        "banner_mexico_independence": "¡Viva México! 🇲🇽 墨西哥獨立日快樂！",
        "banner_solstice": "天體主題是慶祝夏至/冬至的！",
    },
    "pl": {
        "banner_diana_birthday": "Wszystkiego najlepszego z okazji urodzin, Diana, Księżniczko Walii!",
        "banner_equinox": "Świętując Równonoc, ciesz się motywem Tentaizu",
        "banner_mexico_cinco": "¡Feliz Cinco de Mayo! 🇲🇽",
        "banner_mexico_independence": "¡Viva México! 🇲🇽 Szczęśliwego Dnia Niepodległości Meksyku!",
        "banner_solstice": "Motyw Tentaizu jest z okazji przesilenia!",
    },
    "tl": {
        "banner_diana_birthday": "Maligayang kaarawan, Diana, Prinsesa ng Wales!",
        "banner_equinox": "Bilang pagdiriwang ng Ekwinoks, i-enjoy ang Tentaizu theme",
        "banner_mexico_cinco": "¡Feliz Cinco de Mayo! 🇲🇽",
        "banner_mexico_independence": "¡Viva México! 🇲🇽 Maligayang Araw ng Kalayaan ng Mexico!",
        "banner_solstice": "Ang Tentaizu theme ay para sa pagdiriwang ng solstice!",
    },
    "th": {
        "banner_diana_birthday": "สุขสันต์วันเกิด ไดอาน่า เจ้าหญิงแห่งเวลส์!",
        "banner_equinox": "เพื่อเฉลิมฉลองวิษุวัต โปรดเพลิดเพลินกับธีม Tentaizu",
        "banner_mexico_cinco": "¡Feliz Cinco de Mayo! 🇲🇽",
        "banner_mexico_independence": "¡Viva México! 🇲🇽 สุขสันต์วันประกาศอิสรภาพของเม็กซิโก!",
        "banner_solstice": "ธีม Tentaizu เป็นการเฉลิมฉลองครีษมายัน/เหมายัน!",
    },
    "pgl": {
        "banner_diana_birthday": "Arrr, happy birthday to ye, Diana, Princess o' Wales!",
        "banner_equinox": "In celebration o' the Equinox, please enjoy the Tentaizu theme, matey!",
        "banner_mexico_cinco": "¡Feliz Cinco de Mayo!, ye scallywags! 🇲🇽",
        "banner_mexico_independence": "¡Viva México! 🇲🇽 Happy Mexican Independence Day, ye pirates!",
        "banner_solstice": "The Tentaizu theme be in celebration o' the solstice, arr!",
    },
}


def insert_lang(lang):
    keys = LANGS.get(lang)
    if not keys:
        print(f"[{lang}] no translations defined — skip")
        return True

    src = open(TRANS_FILE, encoding='utf-8').read()
    lines = src.splitlines(keepends=True)

    section_start = None
    for i, line in enumerate(lines):
        m = re.match(r'\s*"([a-z\-]+)"\s*:\s*\{', line)
        if m and m.group(1) == lang:
            section_start = i
            break

    if section_start is None:
        print(f"[{lang}] section not found!")
        return False

    existing = set()
    brace_depth = 0
    anchor_line = None
    for i in range(section_start, len(lines)):
        line = lines[i]
        brace_depth += line.count('{') - line.count('}')
        m = re.match(r'\s*"([^"]+)"\s*:', line)
        if m:
            k = m.group(1)
            existing.add(k)
            if k == ANCHOR and anchor_line is None:
                anchor_line = i
        if brace_depth <= 0 and i > section_start:
            break

    if anchor_line is None:
        print(f"[{lang}] anchor '{ANCHOR}' not found — cannot insert!")
        return False

    block = build_block(keys, existing)
    if not block:
        print(f"[{lang}] all keys already present — skipped")
        return True

    # Insert after the anchor line
    new_lines = lines[:anchor_line + 1] + [block] + lines[anchor_line + 1:]
    new_src = "".join(new_lines)

    try:
        ast.parse(new_src)
    except SyntaxError as e:
        print(f"[{lang}] SYNTAX ERROR after insertion: {e}")
        return False

    with open(TRANS_FILE, 'w', encoding='utf-8') as f:
        f.write(new_src)

    added = len([k for k in keys if k not in existing])
    print(f"[{lang}] inserted {added} keys OK")
    return True


if __name__ == "__main__":
    order = ["eo", "de", "es", "fr", "uk", "ru", "pt", "it",
             "ko", "ja", "zh", "zh-hant", "pl", "tl", "th", "pgl"]
    ok = 0
    fail = 0
    for lang in order:
        if insert_lang(lang):
            ok += 1
        else:
            fail += 1
    print(f"\nDone: {ok} OK, {fail} failed")
