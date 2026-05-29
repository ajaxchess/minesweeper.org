"""Add Simplified Chinese tmt_* keys"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import insert_tmt

insert_tmt.LANGS["zh"] = {
    "tmt_bridge": "每日逻辑谜题 — 选择难度，让数字引导你。",
    "tmt_my_history": "我的记录",
    "tmt_stat_mines": "剩余地雷",
    "tmt_stat_time": "已用时间",
    "tmt_overlay_solved": "🎉 谜题已解决！",
    "tmt_retry": "🔄 重试",
    "tmt_new_random": "🎲 新随机",
    "tmt_start_hint": "点击任意格子开始 &middot; <strong>左键</strong>揭开 &middot; <strong>右键</strong>插旗",
    "tmt_play_hint": "将鼠标悬停在数字上可高亮其区域 &middot; 每个数字代表其<strong>高亮区域</strong>内的地雷数",
    "tmt_lb_today": "🏆 今日排行榜",
    "tmt_about_h2": "关于 Tametsi",
    "tmt_what_h2": "什么是 Tametsi？",
    "tmt_what_p1": "Tametsi 是一款数字逻辑谜题，你需要使用区域数字提示找到网格上所有隐藏的地雷，而不仅仅是相邻格子的计数。",
    "tmt_what_p2": "每个揭开的数字告诉你<strong>特定区域</strong>内隐藏了多少颗地雷。区域可以跨越整个棋盘、绕过边缘，或形成不规则形状。",
    "tmt_what_p3": "本网站的每道谜题都保证可通过纯逻辑推理解决，无需猜测。",
    "tmt_howto_h2": "如何游玩 Tametsi",
    "tmt_howto_li1": "<strong>左键点击</strong>格子以揭开它，并查看该区域的地雷数。",
    "tmt_howto_li2": "<strong>右键点击</strong>格子，在疑似地雷处插上旗帜（🚩）。",
    "tmt_howto_li3": "将鼠标悬停在任意已揭开的数字上，可高亮显示它所计算的区域。",
    "tmt_howto_li4": "利用数字提示推断哪些格子是安全的，哪些格子藏有地雷。",
    "tmt_howto_li5": "正确标记所有地雷并揭开所有安全格子即可获胜。",
    "tmt_vs_ms_h2": "Tametsi 与扫雷的区别",
    "tmt_vs_ms_li1": "<strong>区域提示：</strong>数字统计的是特定区域内的地雷，而非仅相邻的8个格子。",
    "tmt_vs_ms_li2": "<strong>无需猜测：</strong>每道谜题都可完全通过逻辑解决，没有50/50的猜测。",
    "tmt_vs_ms_li3": "<strong>不规则区域：</strong>提示区域可以是任意形状，不仅仅是固定的3×3邻域。",
    "tmt_vs_ms_li4": "<strong>循环棋盘：</strong>部分网格的边缘相互连接，开辟了新的推理路径。",
    "tmt_vs_ms_li5": "<strong>每日新谜题：</strong>每天UTC午夜提供一道全新的保证可解挑战。",
    "tmt_vs_tz_h2": "Tametsi 与 Tentaizu 的区别",
    "tmt_vs_tz_intro": 'Tametsi 和 <a href="/tentaizu">Tentaizu</a> 都是区域性找地雷谜题，但在关键方面有所不同：',
    "tmt_vs_tz_li1": "<strong>网格大小：</strong>Tametsi 使用更大的多行网格；Tentaizu 使用紧凑的 7×7 网格。",
    "tmt_vs_tz_li2": "<strong>地雷数量：</strong>Tametsi 在大棋盘上有很多地雷；Tentaizu 恰好隐藏 10 颗。",
    "tmt_vs_tz_li3": "<strong>难度等级：</strong>Tametsi 提供初级、中级和专家模式。",
    "tmt_vs_tz_li4": "<strong>揭开与循环：</strong>在 Tametsi 中你揭开格子；在 Tentaizu 中你循环切换格子状态。",
    "tmt_strategy_h2": "Tametsi 策略技巧",
    "tmt_strategy_li1": "<strong>从完全受限的区域开始。</strong>如果某区域的地雷数等于隐藏格子数，则全部标记为地雷。",
    "tmt_strategy_li2": "<strong>寻找零区域。</strong>显示 0 的区域意味着其中每个隐藏格子都是安全的，全部揭开。",
    "tmt_strategy_li3": "<strong>减去重叠区域。</strong>重叠区域之间计数的差值可约束其独有格子的范围。",
    "tmt_strategy_li4": "<strong>悬停以可视化。</strong>悬停任意数字可查看其区域，并找到与相邻区域的重叠。",
    "tmt_strategy_li5": "<strong>尽早插旗。</strong>尽早确认并标记地雷，可减少每个重叠区域的未知数。",
    "tmt_strategy_li6": "<strong>由外向内推进。</strong>较小的边缘区域通常能最先给出确定性推断。",
}

if __name__ == "__main__":
    ok = insert_tmt.insert_lang("zh")
    sys.exit(0 if ok else 1)
