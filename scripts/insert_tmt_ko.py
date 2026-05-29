"""Add Korean tmt_* keys"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import insert_tmt

insert_tmt.LANGS["ko"] = {
    "tmt_bridge": "매일 제공되는 논리 퍼즐 — 난이도를 선택하고 숫자가 안내하는 대로 따라가세요.",
    "tmt_my_history": "내 기록",
    "tmt_stat_mines": "남은 지뢰",
    "tmt_stat_time": "경과 시간",
    "tmt_overlay_solved": "🎉 퍼즐 완료!",
    "tmt_retry": "🔄 다시 시도",
    "tmt_new_random": "🎲 새 랜덤",
    "tmt_start_hint": "시작하려면 아무 셀이나 클릭하세요 &middot; <strong>왼쪽 클릭</strong> 열기 &middot; <strong>오른쪽 클릭</strong> 깃발",
    "tmt_play_hint": "숫자 위에 마우스를 올리면 해당 영역이 강조됩니다 &middot; 각 숫자는 <strong>강조된 영역</strong>의 지뢰 수를 나타냅니다",
    "tmt_lb_today": "🏆 오늘의 리더보드",
    "tmt_about_h2": "Tametsi 소개",
    "tmt_what_h2": "Tametsi란 무엇인가요?",
    "tmt_what_p1": "Tametsi는 인접 셀 수가 아닌 지역별 숫자 단서를 사용하여 격자의 모든 숨겨진 지뢰를 찾아야 하는 숫자 논리 퍼즐입니다.",
    "tmt_what_p2": "공개된 각 숫자는 <strong>정의된 영역</strong>에 숨겨진 지뢰의 수를 알려줍니다. 영역은 보드 전체에 걸쳐 있거나 가장자리를 둘러싸거나 불규칙한 모양을 형성할 수 있습니다.",
    "tmt_what_p3": "이 사이트의 모든 퍼즐은 순수한 논리로 풀 수 있도록 보장됩니다 — 추측이 필요하지 않습니다.",
    "tmt_howto_h2": "Tametsi 플레이 방법",
    "tmt_howto_li1": "셀을 <strong>왼쪽 클릭</strong>하면 공개되고 해당 지역의 지뢰 수가 표시됩니다.",
    "tmt_howto_li2": "셀을 <strong>오른쪽 클릭</strong>하면 의심되는 지뢰에 깃발(🚩)을 꽂을 수 있습니다.",
    "tmt_howto_li3": "공개된 숫자 위에 마우스를 올리면 해당 숫자가 계산하는 영역이 강조됩니다.",
    "tmt_howto_li4": "숫자 단서를 사용하여 어떤 셀이 안전하고 어떤 셀에 지뢰가 있는지 추론하세요.",
    "tmt_howto_li5": "모든 지뢰에 올바르게 깃발을 꽂고 모든 안전한 셀을 공개하면 승리합니다.",
    "tmt_vs_ms_h2": "Tametsi vs. 지뢰찾기",
    "tmt_vs_ms_li1": "<strong>지역별 단서:</strong> 숫자는 인접한 8개 셀뿐만 아니라 정의된 영역의 지뢰를 셉니다.",
    "tmt_vs_ms_li2": "<strong>추측 없음:</strong> 모든 퍼즐은 논리로 완전히 풀 수 있습니다 — 50/50 추측 없음.",
    "tmt_vs_ms_li3": "<strong>불규칙한 영역:</strong> 단서 영역은 고정된 3×3 이웃이 아닌 어떤 모양도 될 수 있습니다.",
    "tmt_vs_ms_li4": "<strong>래핑 보드:</strong> 일부 격자는 연결된 가장자리가 있어 새로운 추론 경로를 열어줍니다.",
    "tmt_vs_ms_li5": "<strong>새로운 일일 퍼즐:</strong> 매일 자정 UTC에 새로운 보장된 풀이 가능한 도전이 제공됩니다.",
    "tmt_vs_tz_h2": "Tametsi vs. Tentaizu",
    "tmt_vs_tz_intro": 'Tametsi와 <a href="/tentaizu">Tentaizu</a>는 모두 지역별 지뢰 찾기 퍼즐이지만 핵심 차이점이 있습니다:',
    "tmt_vs_tz_li1": "<strong>격자 크기:</strong> Tametsi는 더 큰 다중 행 격자를 사용합니다. Tentaizu는 컴팩트한 7×7 격자를 사용합니다.",
    "tmt_vs_tz_li2": "<strong>지뢰 수:</strong> Tametsi는 큰 보드에 많은 지뢰가 있습니다. Tentaizu는 정확히 10개를 숨깁니다.",
    "tmt_vs_tz_li3": "<strong>난이도 등급:</strong> Tametsi는 초급, 중급, 전문가 모드를 제공합니다.",
    "tmt_vs_tz_li4": "<strong>공개 vs. 순환:</strong> Tametsi에서는 셀을 공개합니다. Tentaizu에서는 셀을 상태별로 순환합니다.",
    "tmt_strategy_h2": "Tametsi 전략 팁",
    "tmt_strategy_li1": "<strong>완전히 제한된 영역부터 시작하세요.</strong> 영역의 지뢰 수가 숨겨진 셀 수와 같으면 모두 표시하세요.",
    "tmt_strategy_li2": "<strong>제로 영역을 찾으세요.</strong> 0을 표시하는 영역은 그 안의 모든 숨겨진 셀이 안전하다는 의미입니다 — 모두 공개하세요.",
    "tmt_strategy_li3": "<strong>겹치는 영역을 빼세요.</strong> 겹치는 영역 간의 수 차이가 고유한 셀을 제한합니다.",
    "tmt_strategy_li4": "<strong>마우스를 올려 시각화하세요.</strong> 숫자 위에 마우스를 올려 영역을 보고 이웃과의 겹침을 찾으세요.",
    "tmt_strategy_li5": "<strong>일찍 표시하세요.</strong> 초기에 확인된 지뢰를 표시하면 겹치는 모든 영역의 미지수가 줄어듭니다.",
    "tmt_strategy_li6": "<strong>안쪽으로 작업하세요.</strong> 더 작은 가장자리 영역이 종종 첫 번째 확실한 추론을 제공합니다.",
}

if __name__ == "__main__":
    ok = insert_tmt.insert_lang("ko")
    sys.exit(0 if ok else 1)
