"""Add Traditional Chinese tmt_* keys"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import insert_tmt

insert_tmt.LANGS["zh-hant"] = {
    "tmt_bridge": "每日邏輯謎題 — 選擇難度，讓數字引導你。",
    "tmt_my_history": "我的記錄",
    "tmt_stat_mines": "剩餘地雷",
    "tmt_stat_time": "已用時間",
    "tmt_overlay_solved": "🎉 謎題已解決！",
    "tmt_retry": "🔄 重試",
    "tmt_new_random": "🎲 新隨機",
    "tmt_start_hint": "點擊任意格子開始 &middot; <strong>左鍵</strong>揭開 &middot; <strong>右鍵</strong>插旗",
    "tmt_play_hint": "將滑鼠懸停在數字上可高亮其區域 &middot; 每個數字代表其<strong>高亮區域</strong>內的地雷數",
    "tmt_lb_today": "🏆 今日排行榜",
    "tmt_about_h2": "關於 Tametsi",
    "tmt_what_h2": "什麼是 Tametsi？",
    "tmt_what_p1": "Tametsi 是一款數字邏輯謎題，你需要使用區域數字提示找到網格上所有隱藏的地雷，而非僅僅相鄰格子的計數。",
    "tmt_what_p2": "每個揭開的數字告訴你<strong>特定區域</strong>內隱藏了多少顆地雷。區域可以跨越整個棋盤、繞過邊緣，或形成不規則形狀。",
    "tmt_what_p3": "本網站的每道謎題都保證可透過純邏輯推理解決，無需猜測。",
    "tmt_howto_h2": "如何遊玩 Tametsi",
    "tmt_howto_li1": "<strong>左鍵點擊</strong>格子以揭開它，並查看該區域的地雷數。",
    "tmt_howto_li2": "<strong>右鍵點擊</strong>格子，在疑似地雷處插上旗幟（🚩）。",
    "tmt_howto_li3": "將滑鼠懸停在任意已揭開的數字上，可高亮顯示它所計算的區域。",
    "tmt_howto_li4": "利用數字提示推斷哪些格子是安全的，哪些格子藏有地雷。",
    "tmt_howto_li5": "正確標記所有地雷並揭開所有安全格子即可獲勝。",
    "tmt_vs_ms_h2": "Tametsi 與踩地雷的區別",
    "tmt_vs_ms_li1": "<strong>區域提示：</strong>數字統計的是特定區域內的地雷，而非僅相鄰的8個格子。",
    "tmt_vs_ms_li2": "<strong>無需猜測：</strong>每道謎題都可完全透過邏輯解決，沒有50/50的猜測。",
    "tmt_vs_ms_li3": "<strong>不規則區域：</strong>提示區域可以是任意形狀，不僅僅是固定的3×3鄰域。",
    "tmt_vs_ms_li4": "<strong>循環棋盤：</strong>部分網格的邊緣相互連接，開闢了新的推理路徑。",
    "tmt_vs_ms_li5": "<strong>每日新謎題：</strong>每天UTC午夜提供一道全新的保證可解挑戰。",
    "tmt_vs_tz_h2": "Tametsi 與 Tentaizu 的區別",
    "tmt_vs_tz_intro": 'Tametsi 和 <a href="/tentaizu">Tentaizu</a> 都是區域性找地雷謎題，但在關鍵方面有所不同：',
    "tmt_vs_tz_li1": "<strong>網格大小：</strong>Tametsi 使用更大的多行網格；Tentaizu 使用緊湊的 7×7 網格。",
    "tmt_vs_tz_li2": "<strong>地雷數量：</strong>Tametsi 在大棋盤上有很多地雷；Tentaizu 恰好隱藏 10 顆。",
    "tmt_vs_tz_li3": "<strong>難度等級：</strong>Tametsi 提供初級、中級和專家模式。",
    "tmt_vs_tz_li4": "<strong>揭開與循環：</strong>在 Tametsi 中你揭開格子；在 Tentaizu 中你循環切換格子狀態。",
    "tmt_strategy_h2": "Tametsi 策略技巧",
    "tmt_strategy_li1": "<strong>從完全受限的區域開始。</strong>如果某區域的地雷數等於隱藏格子數，則全部標記為地雷。",
    "tmt_strategy_li2": "<strong>尋找零區域。</strong>顯示 0 的區域意味著其中每個隱藏格子都是安全的，全部揭開。",
    "tmt_strategy_li3": "<strong>減去重疊區域。</strong>重疊區域之間計數的差值可約束其獨有格子的範圍。",
    "tmt_strategy_li4": "<strong>懸停以視覺化。</strong>懸停任意數字可查看其區域，並找到與相鄰區域的重疊。",
    "tmt_strategy_li5": "<strong>盡早插旗。</strong>盡早確認並標記地雷，可減少每個重疊區域的未知數。",
    "tmt_strategy_li6": "<strong>由外向內推進。</strong>較小的邊緣區域通常能最先給出確定性推斷。",
}

if __name__ == "__main__":
    ok = insert_tmt.insert_lang("zh-hant")
    sys.exit(0 if ok else 1)
