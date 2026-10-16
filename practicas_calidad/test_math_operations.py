import time
import random
import math
import requests

URL = 'http://localhost:8069/api/operations/create'

OPERACIONES = ['suma', 'resta', 'multiplicacion', 'division', 'potencia', 'raiz_cuadrada']

def ejecutar_prueba(numero_prueba):
    operacion = random.choice(OPERACIONES)
    
    numero1 = random.randint(1, 100)
    numero2 = random.randint(1, 10) if operacion == 'potencia' else random.randint(1, 100)


    if operacion == 'suma':
        resultado_esperado = float(numero1 + numero2)
    elif operacion == 'resta':
        resultado_esperado = float(numero1 - numero2)
    elif operacion == 'multiplicacion':
        resultado_esperado = float(numero1 * numero2)
    elif operacion == 'division':
        resultado_esperado = float(numero1 / numero2)
    elif operacion == 'potencia':
        resultado_esperado = float(numero1 ** numero2)
    elif operacion == 'raiz_cuadrada':
        numero2 = 0  
        resultado_esperado = math.sqrt(numero1)

    data= {
         "operand_1": numero1,
        "operand_2": numero2,
        "operation_type": operacion,
        "notes": f"Prueba automatizada #{numero_prueba}"
       
       
    }

    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": data,
        "id": numero_prueba
    }

    inicio = time.time()
    response = requests.post(URL, json=payload, timeout=10)
    fin = time.time()

    tiempo = fin - inicio
    respuesta = response.json()
    
    assert response.status_code == 200
    assert "result" in respuesta

    resultado = respuesta["result"]
    api_success = resultado.get("success", False)
    
    resultado_odoo = resultado.get("data", {}).get("result")
     
    if api_success and resultado_odoo is not None:
        correcto = math.isclose(resultado_esperado, resultado_odoo, rel_tol=1e-5)
    else:
        correcto = False
 
    print(f"\n===========================")
    print(f"Prueba #{numero_prueba}:")
    print(f"Operacion: {operacion}")
    print(f"OPERANDO1: {numero1}")
    print(f"OPERANDO2: {numero2}")
    print(f"Resultado Esperado: {resultado_esperado:.4f}")
    print(f"Resultado Odoo:     {resultado_odoo if resultado_odoo is not None else 'N/A'}")
    print(f"Tiempo de respuesta: {tiempo:.4f}s")
    print(f"===========================")
    if correcto:
        print("Estado: Correcta")
    else:
        print("Estado: Fallida")
        print("Mensaje Odoo:", resultado.get("message"))
    print(f"===========================")
    return operacion, tiempo, correcto
        
def test_operaciones():
    tiempos = []
    estadisticas = {
        "suma": {"bien": 0, "mal": 0},
        "resta": {"bien": 0, "mal": 0},
        "multiplicacion": {"bien": 0, "mal": 0},
        "division": {"bien": 0, "mal": 0},
        "potencia": {"bien": 0, "mal": 0},
        "raiz_cuadrada": {"bien": 0, "mal": 0}
    }

    for i in range(1, 101):
        operacion, tiempo_respuesta, correcto = ejecutar_prueba(i)
        tiempos.append(tiempo_respuesta)
        
        if correcto:
            estadisticas[operacion]["bien"] += 1  
        else:
            estadisticas[operacion]["mal"] += 1

    promedio = sum(tiempos) / len(tiempos) if tiempos else 0

    print("\n=============== ESTADISTICAS FINALES =================")
    
    for op, datos in estadisticas.items():
        total = datos["bien"] + datos["mal"]

        print(f"Operacion: {op:15}")
        print(f"  Total: {total:3}")
        print(f"  Bien: {datos['bien']:3}")
        print(f"  Mal: {datos['mal']:3}")
        
    print("======================================================")
    print(f"Tiempo Promedio: {promedio:.4f} segundos")
    print(f"Tiempo Minimo:   {min(tiempos):.4f} segundos")
    print(f"Tiempo Maximo:   {max(tiempos):.4f} segundos")
    
    assert max(tiempos) < 1