"""Add Pig Latin tmt_* keys"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import insert_tmt

insert_tmt.LANGS["pgl"] = {
    "tmt_bridge": "Away ailyday ogiclay uzzlepay — oosechay away ifficultyDay andway etlay ethay umbersnay uidegay ouyay.",
    "tmt_my_history": "Ymay Istoryhay",
    "tmt_stat_mines": "Inesmay emainingray",
    "tmt_stat_time": "Imetay elapsedway",
    "tmt_overlay_solved": "🎉 Uzzlepay Olvedsay!",
    "tmt_retry": "🔄 Etryray",
    "tmt_new_random": "🎲 Ewnay Andomray",
    "tmt_start_hint": "Icklay anyway ellcay otay artstay &middot; <strong>Eftlay-icklay</strong> evealray &middot; <strong>Ightray-icklay</strong> agflay",
    "tmt_play_hint": "Overhay away umbernay otay ighlighthay itsway egionray &middot; eachway umbernay ountscay inesmay inway itsway <strong>ighlightedhay egionray</strong>",
    "tmt_lb_today": "🏆 Odaytay's Eaderboardlay",
    "tmt_about_h2": "Aboutway Ametsitay",
    "tmt_what_h2": "Hatway Isway Ametsitay?",
    "tmt_what_p1": "Ametsitay isway away umber-logicnay uzzlepay erewhay ouyay ustmay ocatelay allway iddenhay inesmay onway away idgray usingway egionalray umber-clue nay — otnay ustjay adjacentway-ellcay ountscay.",
    "tmt_what_p2": "Everyway evealedray umbernay ellstay ouyay owhay anymay inesmay arehay iddenhay inway away <strong>efinedday egionray</strong>. Egionsray ancay panway ethay entireway oardbay, rapway aroundway edgesway, orway ormfay irregularway apesshay.",
    "tmt_what_p3": "Everyway uzzlepay onway isway itesay isway uaranteedgay olvablesay ybay urepay ogiclay — onay uessing-gay equiredray.",
    "tmt_howto_h2": "Owhay otay Ayplay Ametsitay",
    "tmt_howto_li1": "<strong>Eftlay-icklay</strong> away ellcay otay evealray itway andway eesay itsway egionalray inemay ountcay.",
    "tmt_howto_li2": "<strong>Ightray-icklay</strong> away ellcay otay antplay away agflay (🚩) onway away uspectedsay inemay.",
    "tmt_howto_li3": "Overhay overway anyway evealedray umbernay otay ighlighthay ethay egionray itway ountscay.",
    "tmt_howto_li4": "Useway umbernay uesclays otay educeday ichwhay ellscay arehay afesay andway ichwhay idehay inesmay.",
    "tmt_howto_li5": "Inway ybay orrectlycay aggingflay everyway inemay andway evealingray everyway afesay ellcay.",
    "tmt_vs_ms_h2": "Ametsitay vsway. Inesmay-weepersway",
    "tmt_vs_ms_li1": "<strong>Egionalray uesclays:</strong> Umbersnay ountcay inesmay inway away efinedday egionray, otnay ustjay ethay 8 adjacentway ellscay.",
    "tmt_vs_ms_li2": "<strong>Onay uessing-gay:</strong> Everyway uzzlepay isway ullyFay ogic-solvablelay — onay 50/50 uessesGay.",
    "tmt_vs_ms_li3": "<strong>Irregularway egionsray:</strong> Ueclway egionsray ancay ebay anyway apeshay, otnay away ixedfay 3×3 eighbourhoodnay.",
    "tmt_vs_ms_li4": "<strong>Rappingway oardsDay:</strong> Omesay idsgray avehay edgesway atthay onnectcay, openingway ewnay eductiondway athspay.",
    "tmt_vs_ms_li5": "<strong>Eshfray ailyday uzzlepay:</strong> Away ewnay uaranteed-solvablegay allengehcay everyway ayday atway idnightmay UTC.",
    "tmt_vs_tz_h2": "Ametsitay vsway. Entaizutay",
    "tmt_vs_tz_intro": 'Othbay Ametsitay andway <a href="/tentaizu">Entaizutay</a> arehay egionalray inemay-indingfay uzzlespay, utbay ifferday inway eykay aysway:',
    "tmt_vs_tz_li1": "<strong>Idgray izesay:</strong> Ametsitay usesway argerlAy ulti-rowmay idsgray; Entaizutay usesway away ompactcay 7×7 idgray.",
    "tmt_vs_tz_li2": "<strong>Inemay ountcay:</strong> Ametsitay ashay anymay inesmay acrossway away argelay oardbay; Entaizutay ideshay exactlyway 10.",
    "tmt_vs_tz_li3": "<strong>Ifficultyday iersTay:</strong> Ametsitay offersway Eginnerbay, Intermediateway, andway Expertway odesmay.",
    "tmt_vs_tz_li4": "<strong>Evealray vsway. yclecay:</strong> Inway Ametsitay ouyay evealray ellscay; inway Entaizutay ouyay yclecay ellscay oughthray atestay.",
    "tmt_strategy_h2": "Ametsitay Ategystray Ipstay",
    "tmt_strategy_li1": "<strong>Artstay ithway ullyfay onstrained-cay egionsray.</strong> Ifway away egionray's inemay ountcay equalsway itsway iddenhay-ellcay ountcay, agflay emthay allway.",
    "tmt_strategy_li2": "<strong>Otspay erozay egionsray.</strong> Away egionray owingshay 0 eansmay everyway iddenhay ellcay inway itway isway afesay — evealray emthay allway.",
    "tmt_strategy_li3": "<strong>Ubtractsay overlappingway egionsray.</strong> Ethay ifferenceday inway ountscay etweenbay overlappingway egionsray onstrainscay eirthay uniqueway ellscay.",
    "tmt_strategy_li4": "<strong>Overhay otay isualiseVay.</strong> Overhay anyway umbernay otay eesay itsway egionray andway indfay overlapsway ithway eighboursnay.",
    "tmt_strategy_li5": "<strong>Agflay earlyway.</strong> Onfirmedcay inesmay aggedflay omptlypray rinkshay ethay unknownsway inway everyway overlappingway egionray.",
    "tmt_strategy_li6": "<strong>Orkway inwardway.</strong> Mallersay edgeway egionsray oftenway ieldyay ethay irstfay uresay eductiondway.",
}

if __name__ == "__main__":
    ok = insert_tmt.insert_lang("pgl")
    sys.exit(0 if ok else 1)
