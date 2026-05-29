"""Add Portuguese tmt_* keys"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import insert_tmt

insert_tmt.LANGS["pt"] = {
    "tmt_bridge": "Um puzzle lógico diário — escolha uma dificuldade e deixe os números guiá-lo.",
    "tmt_my_history": "Meu Histórico",
    "tmt_stat_mines": "Minas restantes",
    "tmt_stat_time": "Tempo decorrido",
    "tmt_overlay_solved": "🎉 Puzzle Resolvido!",
    "tmt_retry": "🔄 Tentar Novamente",
    "tmt_new_random": "🎲 Novo Aleatório",
    "tmt_start_hint": "Clique em qualquer célula para começar &middot; <strong>Clique esquerdo</strong> revelar &middot; <strong>Clique direito</strong> bandeira",
    "tmt_play_hint": "Passe o rato sobre um número para destacar a sua região &middot; cada número conta as minas na sua <strong>região destacada</strong>",
    "tmt_lb_today": "🏆 Tabela de Hoje",
    "tmt_about_h2": "Sobre o Tametsi",
    "tmt_what_h2": "O Que É o Tametsi?",
    "tmt_what_p1": "O Tametsi é um puzzle de lógica numérica onde deve localizar todas as minas ocultas numa grelha usando pistas numéricas regionais — não apenas contagens de células adjacentes.",
    "tmt_what_p2": "Cada número revelado indica quantas minas estão ocultas numa <strong>região definida</strong>. As regiões podem abranger todo o tabuleiro, envolver as bordas ou formar formas irregulares.",
    "tmt_what_p3": "Todos os puzzles neste site são garantidamente resolvíveis por lógica pura — sem necessidade de adivinhar.",
    "tmt_howto_h2": "Como Jogar Tametsi",
    "tmt_howto_li1": "<strong>Clique esquerdo</strong> numa célula para a revelar e ver a contagem de minas da sua região.",
    "tmt_howto_li2": "<strong>Clique direito</strong> numa célula para colocar uma bandeira (🚩) numa mina suspeita.",
    "tmt_howto_li3": "Passe o rato sobre qualquer número revelado para destacar a região que conta.",
    "tmt_howto_li4": "Use as pistas numéricas para deduzir quais células são seguras e quais escondem minas.",
    "tmt_howto_li5": "Ganhe marcando corretamente todas as minas e revelando todas as células seguras.",
    "tmt_vs_ms_h2": "Tametsi vs. Campo Minado",
    "tmt_vs_ms_li1": "<strong>Pistas regionais:</strong> Os números contam minas numa região definida, não apenas nas 8 células adjacentes.",
    "tmt_vs_ms_li2": "<strong>Sem adivinhar:</strong> Cada puzzle é completamente resolvível por lógica — sem escolhas 50/50.",
    "tmt_vs_ms_li3": "<strong>Regiões irregulares:</strong> As regiões de pistas podem ter qualquer forma, não apenas uma vizinhança fixa de 3×3.",
    "tmt_vs_ms_li4": "<strong>Tabuleiros envolventes:</strong> Algumas grelhas têm bordas que se conectam, abrindo novos caminhos de dedução.",
    "tmt_vs_ms_li5": "<strong>Puzzle diário novo:</strong> Um novo desafio garantidamente resolvível todos os dias à meia-noite UTC.",
    "tmt_vs_tz_h2": "Tametsi vs. Tentaizu",
    "tmt_vs_tz_intro": 'Tanto o Tametsi como o <a href="/tentaizu">Tentaizu</a> são puzzles regionais de busca de minas, mas diferem em aspetos fundamentais:',
    "tmt_vs_tz_li1": "<strong>Tamanho da grelha:</strong> O Tametsi usa grelhas maiores com múltiplas linhas; o Tentaizu usa uma grelha compacta de 7×7.",
    "tmt_vs_tz_li2": "<strong>Contagem de minas:</strong> O Tametsi tem muitas minas num tabuleiro grande; o Tentaizu esconde exatamente 10.",
    "tmt_vs_tz_li3": "<strong>Níveis de dificuldade:</strong> O Tametsi oferece os modos Iniciante, Intermédio e Especialista.",
    "tmt_vs_tz_li4": "<strong>Revelar vs. ciclar:</strong> No Tametsi revela células; no Tentaizu cicla células por estados.",
    "tmt_strategy_h2": "Dicas de Estratégia para o Tametsi",
    "tmt_strategy_li1": "<strong>Comece com regiões totalmente restringidas.</strong> Se a contagem de minas de uma região for igual ao número de células ocultas, marque-as todas.",
    "tmt_strategy_li2": "<strong>Detecte regiões zero.</strong> Uma região a mostrar 0 significa que todas as células ocultas nela são seguras — revele-as todas.",
    "tmt_strategy_li3": "<strong>Subtraia regiões sobrepostas.</strong> A diferença nas contagens entre regiões sobrepostas restringe as suas células únicas.",
    "tmt_strategy_li4": "<strong>Passe o rato para visualizar.</strong> Passe o rato sobre qualquer número para ver a sua região e encontrar sobreposições com vizinhos.",
    "tmt_strategy_li5": "<strong>Marque cedo.</strong> Minas confirmadas marcadas prontamente reduzem as incógnitas em cada região sobreposta.",
    "tmt_strategy_li6": "<strong>Trabalhe para dentro.</strong> Regiões de borda menores frequentemente fornecem as primeiras deduções certas.",
}

if __name__ == "__main__":
    ok = insert_tmt.insert_lang("pt")
    sys.exit(0 if ok else 1)
