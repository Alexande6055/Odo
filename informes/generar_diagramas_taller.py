# -*- coding: utf-8 -*-
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

# Configurar estilo global
plt.rcParams['font.sans-serif'] = 'DejaVu Sans'
plt.rcParams['font.family'] = 'sans-serif'

def generar_ishikawa():
    fig, ax = plt.subplots(figsize=(14, 8), dpi=300)
    ax.set_facecolor('#F8FAFC')
    fig.patch.set_facecolor('#FFFFFF')
    
    # Eje principal (Espina central)
    ax.annotate('', xy=(13.2, 5), xytext=(0.8, 5),
                arrowprops=dict(arrowstyle="-|>", color='#1E293B', lw=4, mutation_scale=25))
    
    # Caja de Efecto (Cabeza de pescado)
    efecto_box = patches.FancyBboxPatch((13.3, 3.8), 4.2, 2.4, boxstyle="round,pad=0.3",
                                        facecolor='#DC2626', edgecolor='#991B1B', linewidth=2)
    ax.add_patch(efecto_box)
    ax.text(15.4, 5.0, "EFECTO:\nErrores en los Resultados\ndel Módulo de Operaciones\nMatemáticas (Odoo ERP)",
            ha='center', va='center', color='white', weight='bold', fontsize=11, linespacing=1.3)
    
    # Categorías Superiores e Inferiores
    categorias = [
        {"nombre": "SISTEMA / CÓDIGO", "pos": (3.5, 8.5), "xy": (4.5, 5), "color": "#2563EB",
         "subcausas": ["• Fórmulas erróneas (promedio, % sin /100)", "• Falta de validaciones preventivas",
                       "• Excepciones no controladas (ZeroDiv, Overflow)", "• Estructura deficiente _compute_result"]},
        {"nombre": "DATOS / ENTRADAS", "pos": (9.5, 8.5), "xy": (10.5, 5), "color": "#0D9488",
         "subcausas": ["• División por cero sin control", "• Radicando negativo en raíz (< 0)",
                       "• Exponente negativo con base cero", "• Datos no sanitizados"]},
        {"nombre": "PERSONAS / DESARROLLO", "pos": (3.5, 1.5), "xy": (4.5, 5), "color": "#7C3AED",
         "subcausas": ["• Errores de lógica y programación", "• Falta de revisión de código (Code Review)",
                       "• Suposición errónea de entradas ideales", "• Desconocimiento ISO/IEC 25010"]},
        {"nombre": "HERRAMIENTAS / MÉTODOS", "pos": (9.5, 1.5), "xy": (10.5, 5), "color": "#D97706",
         "subcausas": ["• Ausencia inicial de unittest / TransactionCase", "• Sin pruebas automatizadas de regresión",
                       "• Falta de análisis estático (Linter/SonarQube)", "• Sin control continuo de calidad (QA/QC)"]}
    ]
    
    for cat in categorias:
        # Cajas de categorías
        box = patches.FancyBboxPatch((cat["pos"][0]-2.3, cat["pos"][1]-0.4), 4.6, 0.9, boxstyle="round,pad=0.2",
                                     facecolor=cat["color"], edgecolor='#0F172A', linewidth=1.5)
        ax.add_patch(box)
        ax.text(cat["pos"][0], cat["pos"][1], cat["nombre"],
                ha='center', va='center', color='white', weight='bold', fontsize=10)
        
        # Espinas secundarias
        is_top = cat["pos"][1] > 5
        arrow_y = cat["pos"][1] - 0.5 if is_top else cat["pos"][1] + 0.6
        ax.annotate('', xy=cat["xy"], xytext=(cat["pos"][0], arrow_y),
                    arrowprops=dict(arrowstyle="-", color=cat["color"], lw=2.5))
        
        # Subcausas
        y_start = cat["pos"][1] - 0.8 if is_top else cat["pos"][1] + 0.9
        y_step = -0.45 if is_top else 0.45
        for i, sub in enumerate(cat["subcausas"]):
            text_y = y_start + i * y_step
            ax.text(cat["pos"][0] - 1.8, text_y, sub,
                    ha='left', va='center', color='#1E293B', fontsize=8.5, weight='semibold',
                    bbox=dict(boxstyle="square,pad=0.1", fc="#FFFFFF", ec="#CBD5E1", lw=0.8, alpha=0.9))

    ax.set_xlim(0, 18.2)
    ax.set_ylim(0.5, 9.5)
    ax.axis('off')
    plt.title("DIAGRAMA DE CAUSA-EFECTO (ISHIKAWA)\nAnálisis de Defectos en el Módulo de Operaciones Matemáticas de Odoo",
              fontsize=14, weight='bold', pad=20, color='#0F172A')
    plt.tight_layout()
    plt.savefig('imagenes/ishikawa_math_operations.png', bbox_inches='tight', dpi=300)
    plt.close()
    print("Guardado imagenes/ishikawa_math_operations.png")

def generar_pareto():
    fig, ax1 = plt.subplots(figsize=(10, 6), dpi=300)
    fig.patch.set_facecolor('#FFFFFF')
    ax1.set_facecolor('#F8FAFC')
    
    operaciones = ['Potencia\n(pow)', 'Raíz Cuad.\n(sqrt)', 'Porcentaje\n(percent)', 'Promedio\n(avg)', 'División\n(division)']
    defectos = [1, 1, 1, 1, 1]  # Según tabla Slide 43
    porcentajes = [20.0, 20.0, 20.0, 20.0, 20.0]
    acumulado = [20.0, 40.0, 60.0, 80.0, 100.0]
    colores_barras = ['#EF4444', '#DC2626', '#F59E0B', '#FBBF24', '#3B82F6']
    
    x = np.arange(len(operaciones))
    bars = ax1.bar(x, defectos, color=colores_barras, width=0.55, edgecolor='#1E293B', linewidth=1.2, zorder=3)
    ax1.set_ylabel('Frecuencia de Defectos Detectados', color='#1E293B', fontsize=11, weight='bold')
    ax1.set_ylim(0, 2.0)
    ax1.set_yticks([0, 0.5, 1.0, 1.5, 2.0])
    ax1.grid(axis='y', linestyle='--', alpha=0.5, zorder=0)
    
    # Eje secundario para porcentaje acumulado
    ax2 = ax1.twinx()
    line = ax2.plot(x, acumulado, color='#1E3A8A', marker='o', linewidth=2.5, markersize=8, zorder=4)
    ax2.set_ylabel('Porcentaje Acumulado (%)', color='#1E3A8A', fontsize=11, weight='bold')
    ax2.set_ylim(0, 110)
    
    # Línea del 80% (Principio de Pareto)
    ax2.axhline(80, color='#B91C1C', linestyle='--', linewidth=1.8, label='Umbral 80% (Pareto)')
    
    # Anotaciones en barras y puntos
    for i, bar in enumerate(bars):
        yval = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2.0, yval + 0.05, f"{yval} def.", ha='center', va='bottom', fontsize=9, weight='bold')
        ax2.annotate(f"{acumulado[i]:.0f}%", (x[i], acumulado[i]), textcoords="offset points", xytext=(0, 10),
                     ha='center', fontsize=9, weight='bold', color='#1E3A8A')
        
    ax1.set_xticks(x)
    ax1.set_xticklabels(operaciones, fontsize=9.5, weight='bold')
    
    # Leyenda explicativa de criticidad (según Slide 43 del PDF)
    texto_info = (
        "Clasificación de Criticidad (Slide 43):\n"
        "• pow & sqrt: Errores de Código (CRÍTICOS - Parada/Crash)\n"
        "• percent & avg: Errores Lógicos (Fórmulas defectuosas)\n"
        "• division: Error de Validación (Retorna 0 silencioso)"
    )
    plt.gcf().text(0.15, 0.02, texto_info, fontsize=8.5,
                   bbox=dict(boxstyle="round,pad=0.5", facecolor="#FEF3C7", edgecolor="#D97706", lw=1))
    
    plt.title("DIAGRAMA DE PARETO: PRIORIZACIÓN DE DEFECTOS EN MÓDULO MATEMÁTICO\nDistribución uniforme de fallos críticos vs. lógicos",
              fontsize=12, weight='bold', pad=15, color='#0F172A')
    plt.subplots_adjust(bottom=0.22)
    plt.savefig('imagenes/pareto_math_operations.png', bbox_inches='tight', dpi=300)
    plt.close()
    print("Guardado imagenes/pareto_math_operations.png")

def generar_pdca():
    fig, ax = plt.subplots(figsize=(9, 7), dpi=300)
    fig.patch.set_facecolor('#FFFFFF')
    ax.set_facecolor('#F8FAFC')
    
    pasos = [
        {"titulo": "1. PLAN (Planificar)", "desc": "• Identificar fallas en operaciones (div/0, %, avg, pow, sqrt)\n• Detectar retorno silencioso de 0 en división\n• Planificar refactorización y cobertura de tests",
         "box": (0.05, 0.52, 0.42, 0.42), "color": "#3B82F6"},
        {"titulo": "2. DO (Hacer)", "desc": "• Refactorizar math_operations.py en Odoo\n• Implementar excepciones ValidationError\n• Agregar validaciones @api.constrains y defensivas",
         "box": (0.53, 0.52, 0.42, 0.42), "color": "#10B981"},
        {"titulo": "3. CHECK (Verificar)", "desc": "• Ejecutar 11 pruebas unitarias TransactionCase\n• Correr 100 pruebas de integración API REST\n• Verificar tiempo de respuesta < 1s y 0% errores",
         "box": (0.53, 0.04, 0.42, 0.42), "color": "#F59E0B"},
        {"titulo": "4. ACT (Actuar)", "desc": "• Estandarizar catálogo de operaciones (alias multilingüe)\n• Asegurar persistencia y blindaje en API JSON-RPC\n• Integrar aseguramiento continuo de calidad (QA)",
         "box": (0.05, 0.04, 0.42, 0.42), "color": "#8B5CF6"},
    ]
    
    for p in pasos:
        rect = patches.FancyBboxPatch((p["box"][0], p["box"][1]), p["box"][2], p["box"][3],
                                      boxstyle="round,pad=0.03", facecolor=p["color"], edgecolor='#1E293B', lw=1.5, alpha=0.95)
        ax.add_patch(rect)
        ax.text(p["box"][0]+0.02, p["box"][1]+p["box"][3]-0.06, p["titulo"],
                color='white', weight='bold', fontsize=11)
        ax.text(p["box"][0]+0.02, p["box"][1]+p["box"][3]-0.15, p["desc"],
                color='white', fontsize=8.5, linespacing=1.4)
        
    # Flechas de ciclo
    ax.annotate('', xy=(0.51, 0.73), xytext=(0.48, 0.73), arrowprops=dict(arrowstyle="->", lw=3, color='#1E293B'))
    ax.annotate('', xy=(0.74, 0.49), xytext=(0.74, 0.47), arrowprops=dict(arrowstyle="->", lw=3, color='#1E293B'))
    ax.annotate('', xy=(0.48, 0.25), xytext=(0.51, 0.25), arrowprops=dict(arrowstyle="->", lw=3, color='#1E293B'))
    ax.annotate('', xy=(0.26, 0.47), xytext=(0.26, 0.49), arrowprops=dict(arrowstyle="->", lw=3, color='#1E293B'))
    
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')
    plt.title("CICLO PDCA (PLAN - DO - CHECK - ACT)\nMejora Continua del Módulo math_operations en Odoo ERP",
              fontsize=13, weight='bold', pad=15, color='#0F172A')
    plt.tight_layout()
    plt.savefig('imagenes/pdca_math_operations.png', bbox_inches='tight', dpi=300)
    plt.close()
    print("Guardado imagenes/pdca_math_operations.png")

def generar_dmaic():
    fig, ax = plt.subplots(figsize=(12, 4.5), dpi=300)
    fig.patch.set_facecolor('#FFFFFF')
    ax.set_facecolor('#F8FAFC')
    
    fases = [
        {"sigla": "DEFINE", "sub": "Definir", "color": "#1E40AF",
         "items": ["• Inconsistencia en cálculos", "• Error div/0 silencioso", "• Meta: 0% defectos"]},
        {"sigla": "MEASURE", "sub": "Medir", "color": "#047857",
         "items": ["• 100 pruebas ejecutadas", "• Tasa error previa: 40-78%", "• Tiempo inicial: 0.017s"]},
        {"sigla": "ANALYZE", "sub": "Analizar", "color": "#B45309",
         "items": ["• Ishikawa (Causa raíz)", "• Pareto (Criticidad)", "• Ausencia validaciones"]},
        {"sigla": "IMPROVE", "sub": "Mejorar", "color": "#6D28D9",
         "items": ["• Refactorización modelo", "• ValidationError estricto", "• Catálogo operaciones"]},
        {"sigla": "CONTROL", "sub": "Controlar", "color": "#BE123C",
         "items": ["• 11 unittests Odoo (0 fallos)", "• 100 tests API (100% éxito)", "• Tiempo prom: 0.021s < 1s"]}
    ]
    
    x_positions = np.linspace(0.04, 0.82, 5)
    width = 0.16
    
    for i, f in enumerate(fases):
        xp = x_positions[i]
        rect = patches.FancyBboxPatch((xp, 0.1), width, 0.8, boxstyle="round,pad=0.02",
                                      facecolor=f["color"], edgecolor='#0F172A', lw=1.5)
        ax.add_patch(rect)
        ax.text(xp + width/2.0, 0.81, f["sigla"], color='white', weight='bold', fontsize=11, ha='center')
        ax.text(xp + width/2.0, 0.73, f"({f['sub']})", color='#E2E8F0', fontsize=9, ha='center', style='italic')
        
        y_text = 0.61
        for item in f["items"]:
            ax.text(xp + 0.012, y_text, item, color='white', fontsize=7.5, ha='left', weight='medium')
            y_text -= 0.13
            
        if i < 4:
            ax.annotate('', xy=(xp + width + 0.035, 0.5), xytext=(xp + width, 0.5),
                        arrowprops=dict(arrowstyle="-|>", lw=2.5, color='#334155', mutation_scale=15))
            
    ax.set_xlim(0, 1.02)
    ax.set_ylim(0, 1)
    ax.axis('off')
    plt.title("METODOLOGÍA SIX SIGMA (DMAIC) APLICADA AL MÓDULO MATEMÁTICO\nOptimización Basada en Datos Reales de Pruebas",
              fontsize=12, weight='bold', pad=15, color='#0F172A')
    plt.tight_layout()
    plt.savefig('imagenes/six_sigma_dmaic_math.png', bbox_inches='tight', dpi=300)
    plt.close()
    print("Guardado imagenes/six_sigma_dmaic_math.png")

if __name__ == '__main__':
    generar_ishikawa()
    generar_pareto()
    generar_pdca()
    generar_dmaic()
