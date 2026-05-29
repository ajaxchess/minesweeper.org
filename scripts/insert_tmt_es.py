"""Add Spanish tmt_* keys"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import insert_tmt

insert_tmt.LANGS["es"] = {
    "tmt_bridge": "Un rompecabezas lógico diario — elige una dificultad y deja que los números te guíen.",
    "tmt_my_history": "Mi Historial",
    "tmt_stat_mines": "Minas restantes",
    "tmt_stat_time": "Tiempo transcurrido",
    "tmt_overlay_solved": "🎉 ¡Puzzle Resuelto!",
    "tmt_retry": "🔄 Reintentar",
    "tmt_new_random": "🎲 Nuevo Aleatorio",
    "tmt_start_hint": "Haz clic en cualquier celda para comenzar &middot; <strong>Clic izquierdo</strong> revelar &middot; <strong>Clic derecho</strong> marcar",
    "tmt_play_hint": "Pasa el cursor sobre un número para resaltar su región &middot; cada número cuenta las minas en su <strong>región resaltada</strong>",
    "tmt_lb_today": "🏆 Tabla de Hoy",
    "tmt_about_h2": "Sobre Tametsi",
    "tmt_what_h2": "¿Qué Es Tametsi?",
    "tmt_what_p1": "Tametsi es un rompecabezas de lógica numérica donde debes localizar todas las minas ocultas en una cuadrícula usando pistas numéricas regionales, no solo conteos de celdas adyacentes.",
    "tmt_what_p2": "Cada número revelado te indica cuántas minas están ocultas en una <strong>región definida</strong>. Las regiones pueden abarcar todo el tablero, envolverse en los bordes o formar formas irregulares.",
    "tmt_what_p3": "Cada rompecabezas en este sitio está garantizado como resoluble mediante lógica pura — no se requiere adivinar.",
    "tmt_howto_h2": "Cómo Jugar Tametsi",
    "tmt_howto_li1": "<strong>Clic izquierdo</strong> en una celda para revelarla y ver el conteo de minas de su región.",
    "tmt_howto_li2": "<strong>Clic derecho</strong> en una celda para plantar una bandera (🚩) en una mina sospechosa.",
    "tmt_howto_li3": "Pasa el cursor sobre cualquier número revelado para resaltar la región que cuenta.",
    "tmt_howto_li4": "Usa las pistas numéricas para deducir qué celdas son seguras y cuáles ocultan minas.",
    "tmt_howto_li5": "Gana marcando correctamente todas las minas y revelando todas las celdas seguras.",
    "tmt_vs_ms_h2": "Tametsi vs. Buscaminas",
    "tmt_vs_ms_li1": "<strong>Pistas regionales:</strong> Los números cuentan minas en una región definida, no solo en las 8 celdas adyacentes.",
    "tmt_vs_ms_li2": "<strong>Sin adivinar:</strong> Cada puzzle es completamente resoluble por lógica — sin elecciones 50/50.",
    "tmt_vs_ms_li3": "<strong>Regiones irregulares:</strong> Las regiones de pistas pueden tener cualquier forma, no solo un vecindario fijo de 3×3.",
    "tmt_vs_ms_li4": "<strong>Tableros envolventes:</strong> Algunas cuadrículas tienen bordes que se conectan, abriendo nuevas rutas de deducción.",
    "tmt_vs_ms_li5": "<strong>Puzzle diario fresco:</strong> Un nuevo desafío garantizado resoluble cada día a medianoche UTC.",
    "tmt_vs_tz_h2": "Tametsi vs. Tentaizu",
    "tmt_vs_tz_intro": 'Tanto Tametsi como <a href="/tentaizu">Tentaizu</a> son puzzles regionales de búsqueda de minas, pero difieren en aspectos clave:',
    "tmt_vs_tz_li1": "<strong>Tamaño de cuadrícula:</strong> Tametsi usa cuadrículas más grandes de múltiples filas; Tentaizu usa una cuadrícula compacta de 7×7.",
    "tmt_vs_tz_li2": "<strong>Conteo de minas:</strong> Tametsi tiene muchas minas en un tablero grande; Tentaizu esconde exactamente 10.",
    "tmt_vs_tz_li3": "<strong>Niveles de dificultad:</strong> Tametsi ofrece modos Principiante, Intermedio y Experto.",
    "tmt_vs_tz_li4": "<strong>Revelar vs. ciclar:</strong> En Tametsi revelas celdas; en Tentaizu ciclas celdas por estados.",
    "tmt_strategy_h2": "Consejos de Estrategia para Tametsi",
    "tmt_strategy_li1": "<strong>Empieza con regiones totalmente restringidas.</strong> Si el conteo de minas de una región es igual al de celdas ocultas, márcalas todas.",
    "tmt_strategy_li2": "<strong>Detecta regiones cero.</strong> Una región que muestra 0 significa que cada celda oculta en ella es segura — revélalas todas.",
    "tmt_strategy_li3": "<strong>Resta regiones superpuestas.</strong> La diferencia en los conteos entre regiones superpuestas restringe sus celdas únicas.",
    "tmt_strategy_li4": "<strong>Pasa el cursor para visualizar.</strong> Pasa el cursor sobre cualquier número para ver su región y encontrar superposiciones con vecinos.",
    "tmt_strategy_li5": "<strong>Marca pronto.</strong> Las minas confirmadas marcadas a tiempo reducen las incógnitas en cada región superpuesta.",
    "tmt_strategy_li6": "<strong>Trabaja hacia adentro.</strong> Las regiones de borde más pequeñas a menudo proporcionan las primeras deducciones seguras.",
}

if __name__ == "__main__":
    ok = insert_tmt.insert_lang("es")
    sys.exit(0 if ok else 1)
