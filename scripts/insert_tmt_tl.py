"""Add Tagalog tmt_* keys"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import insert_tmt

insert_tmt.LANGS["tl"] = {
    "tmt_bridge": "Isang araw-araw na lohikal na palaisipan — pumili ng kahirapan at hayaan ang mga numero na gabayan ka.",
    "tmt_my_history": "Ang Aking Kasaysayan",
    "tmt_stat_mines": "Natitirang mina",
    "tmt_stat_time": "Lumipas na oras",
    "tmt_overlay_solved": "🎉 Nalutas ang Palaisipan!",
    "tmt_retry": "🔄 Subukang Muli",
    "tmt_new_random": "🎲 Bagong Random",
    "tmt_start_hint": "I-click ang anumang cell upang magsimula &middot; <strong>Kaliwang-click</strong> para ihayag &middot; <strong>Kanang-click</strong> para maglagay ng bandila",
    "tmt_play_hint": "I-hover ang isang numero upang i-highlight ang rehiyon nito &middot; ang bawat numero ay binibilang ang mga mina sa <strong>naka-highlight na rehiyon</strong>",
    "tmt_lb_today": "🏆 Leaderboard Ngayon",
    "tmt_about_h2": "Tungkol sa Tametsi",
    "tmt_what_h2": "Ano ang Tametsi?",
    "tmt_what_p1": "Ang Tametsi ay isang numero-lohikal na palaisipan kung saan dapat mong hanapin ang lahat ng nakatagong mina sa isang grid gamit ang mga rehiyonal na pahiwatig ng numero — hindi lamang mga bilang ng katabing cell.",
    "tmt_what_p2": "Ang bawat nahayag na numero ay nagsasabi sa iyo kung ilang mina ang nakatago sa isang <strong>tinukoy na rehiyon</strong>. Ang mga rehiyon ay maaaring sumasaklaw sa buong board, mag-wrap sa paligid ng mga gilid, o bumuo ng mga hindi regular na hugis.",
    "tmt_what_p3": "Ang bawat palaisipan sa site na ito ay garantisadong malulutas sa pamamagitan ng purong lohika — hindi kailangan ang paghula.",
    "tmt_howto_h2": "Paano Maglaro ng Tametsi",
    "tmt_howto_li1": "<strong>Kaliwang-click</strong> sa isang cell upang ihayag ito at makita ang bilang ng mina sa rehiyon nito.",
    "tmt_howto_li2": "<strong>Kanang-click</strong> sa isang cell upang maglagay ng bandila (🚩) sa isang pinaghihinalaang mina.",
    "tmt_howto_li3": "I-hover ang anumang nahayag na numero upang i-highlight ang rehiyong binibilang nito.",
    "tmt_howto_li4": "Gamitin ang mga pahiwatig ng numero upang malaman kung aling mga cell ang ligtas at alin ang may nakatagong mina.",
    "tmt_howto_li5": "Manalo sa pamamagitan ng tamang paglalagay ng bandila sa lahat ng mina at paghahayag ng lahat ng ligtas na cell.",
    "tmt_vs_ms_h2": "Tametsi laban sa Minesweeper",
    "tmt_vs_ms_li1": "<strong>Mga rehiyonal na pahiwatig:</strong> Ang mga numero ay binibilang ang mga mina sa isang tinukoy na rehiyon, hindi lamang sa 8 katabing cell.",
    "tmt_vs_ms_li2": "<strong>Walang paghula:</strong> Ang bawat palaisipan ay ganap na malulutas sa lohika — walang 50/50 na paghula.",
    "tmt_vs_ms_li3": "<strong>Mga hindi regular na rehiyon:</strong> Ang mga rehiyon ng pahiwatig ay maaaring maging anumang hugis, hindi isang nakapirming 3x3 na kapitbahayan.",
    "tmt_vs_ms_li4": "<strong>Mga lumalagpas na board:</strong> Ang ilang mga grid ay may mga konektadong gilid, nagbubukas ng mga bagong landas ng deduksyon.",
    "tmt_vs_ms_li5": "<strong>Sariwang araw-araw na palaisipan:</strong> Isang bagong garantisadong malulutas na hamon araw-araw sa hatinggabi UTC.",
    "tmt_vs_tz_h2": "Tametsi laban sa Tentaizu",
    "tmt_vs_tz_intro": 'Ang parehong Tametsi at <a href="/tentaizu">Tentaizu</a> ay mga rehiyonal na palaisipan sa paghahanap ng mina, ngunit naiiba sa mga pangunahing paraan:',
    "tmt_vs_tz_li1": "<strong>Laki ng grid:</strong> Ang Tametsi ay gumagamit ng mas malalaking multi-row na grid; ang Tentaizu ay gumagamit ng compact na 7x7 na grid.",
    "tmt_vs_tz_li2": "<strong>Bilang ng mina:</strong> Ang Tametsi ay may maraming mina sa isang malaking board; ang Tentaizu ay nagtatago ng eksaktong 10.",
    "tmt_vs_tz_li3": "<strong>Mga antas ng kahirapan:</strong> Ang Tametsi ay nag-aalok ng mga mode na Nagsisimula, Intermediate, at Expert.",
    "tmt_vs_tz_li4": "<strong>Ihayag laban sa mag-cycle:</strong> Sa Tametsi ay ihinahayag mo ang mga cell; sa Tentaizu ay ino-cycle mo ang mga cell sa pamamagitan ng mga estado.",
    "tmt_strategy_h2": "Mga Tips sa Estratehiya ng Tametsi",
    "tmt_strategy_li1": "<strong>Magsimula sa ganap na limitadong mga rehiyon.</strong> Kung ang bilang ng mina ng isang rehiyon ay katumbas ng bilang ng nakatagong cell nito, i-flag silang lahat.",
    "tmt_strategy_li2": "<strong>Hanapin ang mga zero na rehiyon.</strong> Ang isang rehiyon na nagpapakita ng 0 ay nangangahulugan na ang bawat nakatagong cell dito ay ligtas — ihayag silang lahat.",
    "tmt_strategy_li3": "<strong>Ibawas ang mga nagsasapawan na rehiyon.</strong> Ang pagkakaiba sa mga bilang sa pagitan ng mga nagsasapawang rehiyon ay naglilimita sa kanilang natatanging mga cell.",
    "tmt_strategy_li4": "<strong>I-hover para mag-visualise.</strong> I-hover ang anumang numero upang makita ang rehiyon nito at mahanap ang mga overlap sa mga kapitbahay.",
    "tmt_strategy_li5": "<strong>Mag-flag nang maaga.</strong> Ang mga kumpirmadong mina na na-flag agad ay nagpapababa ng mga hindi kilala sa bawat nagsasapawang rehiyon.",
    "tmt_strategy_li6": "<strong>Magtrabaho patungo sa loob.</strong> Ang mas maliliit na rehiyon ng gilid ay kadalasang nagbibigay ng unang tiyak na mga deduksyon.",
}

if __name__ == "__main__":
    ok = insert_tmt.insert_lang("tl")
    sys.exit(0 if ok else 1)
