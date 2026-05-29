"""Add Japanese tmt_* keys"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import insert_tmt

insert_tmt.LANGS["ja"] = {
    "tmt_bridge": "毎日の論理パズル — 難易度を選んで、数字に導かれてみましょう。",
    "tmt_my_history": "マイ履歴",
    "tmt_stat_mines": "残りの地雷",
    "tmt_stat_time": "経過時間",
    "tmt_overlay_solved": "🎉 パズル完了！",
    "tmt_retry": "🔄 リトライ",
    "tmt_new_random": "🎲 新しいランダム",
    "tmt_start_hint": "任意のセルをクリックして開始 &middot; <strong>左クリック</strong>で開く &middot; <strong>右クリック</strong>でフラグ",
    "tmt_play_hint": "数字の上にマウスを置くと、その領域がハイライトされます &middot; 各数字は<strong>ハイライトされた領域</strong>内の地雷数を示します",
    "tmt_lb_today": "🏆 本日のリーダーボード",
    "tmt_about_h2": "Tametsiについて",
    "tmt_what_h2": "Tametsiとは？",
    "tmt_what_p1": "Tametsiは、隣接セルのカウントではなく、地域的な数字のヒントを使用してグリッド上のすべての隠れた地雷を見つけなければならない数字論理パズルです。",
    "tmt_what_p2": "公開された各数字は、<strong>定義された領域</strong>に隠れている地雷の数を教えてくれます。領域はボード全体に及んだり、端を回り込んだり、不規則な形を形成したりすることができます。",
    "tmt_what_p3": "このサイトのすべてのパズルは純粋な論理で解けることが保証されています — 推測は不要です。",
    "tmt_howto_h2": "Tametsiの遊び方",
    "tmt_howto_li1": "セルを<strong>左クリック</strong>すると開いて、そのエリアの地雷数が表示されます。",
    "tmt_howto_li2": "セルを<strong>右クリック</strong>すると、疑わしい地雷にフラグ(🚩)を立てられます。",
    "tmt_howto_li3": "公開された数字の上にマウスを置くと、その数字がカウントする領域がハイライトされます。",
    "tmt_howto_li4": "数字のヒントを使って、どのセルが安全でどのセルに地雷があるかを推論します。",
    "tmt_howto_li5": "すべての地雷に正しくフラグを立て、すべての安全なセルを開くと勝利です。",
    "tmt_vs_ms_h2": "Tametsiとマインスイーパーの違い",
    "tmt_vs_ms_li1": "<strong>地域的なヒント：</strong>数字は隣接する8つのセルだけでなく、定義された領域内の地雷をカウントします。",
    "tmt_vs_ms_li2": "<strong>推測不要：</strong>すべてのパズルは論理で完全に解けます — 50/50の推測はありません。",
    "tmt_vs_ms_li3": "<strong>不規則な領域：</strong>ヒントの領域は固定の3×3の近傍ではなく、あらゆる形を持つことができます。",
    "tmt_vs_ms_li4": "<strong>ラッピングボード：</strong>一部のグリッドには端が繋がっていて、新しい推論経路が開けます。",
    "tmt_vs_ms_li5": "<strong>毎日新しいパズル：</strong>毎日UTC深夜に保証された解けるチャレンジが提供されます。",
    "tmt_vs_tz_h2": "TametsiとTentaizuの違い",
    "tmt_vs_tz_intro": 'TametsiとTentaizuはどちらも地域的な地雷探しパズルですが、重要な点で異なります：(<a href="/tentaizu">Tentaizu</a>を参照)',
    "tmt_vs_tz_li1": "<strong>グリッドサイズ：</strong>Tametsiはより大きな複数行グリッドを使用します。Tentaizuはコンパクトな7×7グリッドを使用します。",
    "tmt_vs_tz_li2": "<strong>地雷数：</strong>Tametsiは大きなボードに多くの地雷があります。Tentaizuはちょうど10個を隠します。",
    "tmt_vs_tz_li3": "<strong>難易度：</strong>Tametsiは初心者、中級者、エキスパートモードを提供します。",
    "tmt_vs_tz_li4": "<strong>開くvsサイクル：</strong>Tametsiではセルを開きます。Tentaizuではセルの状態をサイクルします。",
    "tmt_strategy_h2": "Tametsi戦略のヒント",
    "tmt_strategy_li1": "<strong>完全に制約された領域から始めましょう。</strong>領域の地雷数が隠れたセルの数と等しければ、すべてにフラグを立てます。",
    "tmt_strategy_li2": "<strong>ゼロ領域を見つけましょう。</strong>0を示す領域は、その中のすべての隠れたセルが安全であることを意味します — すべて開きましょう。",
    "tmt_strategy_li3": "<strong>重なる領域を引き算しましょう。</strong>重なる領域間のカウントの差が、固有のセルを制約します。",
    "tmt_strategy_li4": "<strong>マウスを置いて視覚化しましょう。</strong>数字の上にマウスを置くと、その領域が見えて、隣接領域との重なりが分かります。",
    "tmt_strategy_li5": "<strong>早めにフラグを立てましょう。</strong>確認された地雷を早めにフラグすると、重なる各領域の未知数が減ります。",
    "tmt_strategy_li6": "<strong>内側に向かって作業しましょう。</strong>小さな端の領域が最初の確実な推論を提供することが多いです。",
}

if __name__ == "__main__":
    ok = insert_tmt.insert_lang("ja")
    sys.exit(0 if ok else 1)
