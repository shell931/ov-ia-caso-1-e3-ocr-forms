"""Post-procesamiento express para Parte 4.

Objetivo: Mejorar de 77% a 80%+ corrigiendo TOP 3 campos con más errores:
1. direccion (740 errores)
2. telefono_movil (673 errores) 
3. email (375 errores)

Errores identificados en comparacion-gold.csv:
- direccion: "Cll 73 # 89-13" → "C11+389-13" (58%)
- direccion: "cll 69 D # 72 C 38 Sur" → "cl1 690# 72 038 508" (63%)
- ciudad: "Bogota" → "Bo50.t3" (46%)
- telefono: "3222940" → "3222940576" (números de más)
"""

import re


def corregir_direccion(texto: str) -> str:
    """
    Corrige errores comunes en direcciones colombianas.
    
    Patrones identificados:
    - C11 → Cll (Calle)
    - Cr1 → Cra (Carrera)
    - + → # (signo de número)
    - Números pegados sin espacios
    - Confusión 1/l, 0/O
    """
    if not texto or len(texto.strip()) == 0:
        return texto
    
    resultado = texto.strip()
    
    # 1. Prefijos de vía más comunes (al inicio)
    # IMPORTANTE: hacer case-insensitive match pero reemplazar con formato correcto
    patrones_prefijo = [
        (r'^\s*C1[1l]\b', 'Cll'),      # C11, C1l → Cll
        (r'^\s*C[1l]{2}\b', 'Cll'),    # C11, Cll → Cll
        (r'^\s*Cr1\b', 'Cra'),         # Cr1 → Cra
        (r'^\s*Av1\b', 'Av'),          # Av1 → Av
        (r'^\s*Dg1\b', 'Dg'),          # Dg1 → Dg
        (r'^\s*Tr1\b', 'Tr'),          # Tr1 → Tr
        (r'^\s*C[1l]{1}[1l]\b', 'Cll'), # cl1, c1l, cll → Cll
    ]
    
    for patron, reemplazo in patrones_prefijo:
        resultado = re.sub(patron, reemplazo, resultado, flags=re.IGNORECASE)
    
    # 2. Signo + por # (muy común)
    resultado = re.sub(r'\+(\d)', r'# \1', resultado)
    resultado = re.sub(r'(\d)\+(\d)', r'\1-\2', resultado)  # Si + está entre números
    
    # 3. Separar números pegados a letras (ej: "72C38" → "72 C 38")
    resultado = re.sub(r'(\d)([A-Za-z])', r'\1 \2', resultado)
    resultado = re.sub(r'([A-Za-z])(\d)', r'\1 \2', resultado)
    
    # 4. Normalizar espacios múltiples
    resultado = re.sub(r'\s+', ' ', resultado)
    
    # 5. Validación: Si no tiene formato Cll/Cra/Av, intentar rescatar
    if not re.search(r'(Cll|Cra|Av|Dg|Tr)\s', resultado, re.IGNORECASE):
        # Si empieza con C seguido de números, es probablemente Cll
        if re.match(r'^C\s?\d', resultado, re.IGNORECASE):
            resultado = 'Cll ' + re.sub(r'^C\s?', '', resultado, flags=re.IGNORECASE)
    
    return resultado.strip()


def corregir_ciudad(texto: str) -> str:
    """
    Corrige errores en nombres de ciudades.
    
    Errores identificados:
    - "Bogota" → "Bo50.t3", "FPANCA·FONTIRON"
    - Caracteres extraños, números
    """
    if not texto or len(texto.strip()) == 0:
        return texto
    
    resultado = texto.strip()
    
    # 1. Remover caracteres especiales raros
    resultado = re.sub(r'[·•\.]', '', resultado)
    resultado = re.sub(r'\d', '', resultado)  # Ciudades no tienen números
    
    # 2. Normalizar espacios
    resultado = re.sub(r'\s+', ' ', resultado)
    
    # 3. Capitalizar correctamente (Title Case)
    resultado = resultado.title()
    
    # 4. Correcciones específicas de ciudades conocidas
    # (En producción, esto vendría de un léxico)
    ciudades_comunes = {
        'bogota': 'Bogotá',
        'cali': 'Cali',
        'medellin': 'Medellín',
        'barranquilla': 'Barranquilla',
        'cartagena': 'Cartagena',
    }
    
    resultado_lower = resultado.lower()
    for ciudad_key, ciudad_correcta in ciudades_comunes.items():
        if ciudad_key in resultado_lower:
            return ciudad_correcta
    
    # 5. Si quedó muy corto o raro, devolver vacío
    if len(resultado) < 3 or not resultado.isalpha():
        return ""
    
    return resultado


def corregir_telefono(texto: str) -> str:
    """
    Corrige errores en teléfonos.
    
    Errores identificados:
    - "3222940" → "3222940576" (números de más al final)
    - Confusión dígitos: 6→5, 8→9
    """
    if not texto or len(texto.strip()) == 0:
        return texto
    
    # Solo dígitos
    resultado = re.sub(r'\D', '', texto)
    
    # Validación básica Colombia:
    # - Móviles: 10 dígitos (empiezan con 3)
    # - Fijos: 7 dígitos
    
    if len(resultado) == 10 and resultado.startswith('3'):
        return resultado  # Móvil OK
    
    if len(resultado) == 7:
        return resultado  # Fijo OK
    
    # Si tiene más de 10 dígitos y empieza con 3, recortar
    if len(resultado) > 10 and resultado.startswith('3'):
        return resultado[:10]
    
    # Si tiene más de 7 pero menos de 10, devolver como está
    # (puede ser error del gold también)
    return resultado if resultado else ""


def corregir_email(texto: str) -> str:
    """
    Corrige errores comunes en emails.
    
    Errores identificados:
    - @ → o, a (confusión)
    - .com → .can, .cam
    - gmail → gimal, gima
    """
    if not texto or len(texto.strip()) == 0:
        return texto
    
    resultado = texto.strip()
    
    # 1. Asegurar que tiene @
    if '@' not in resultado:
        # Intentar detectar 'o' o 'a' que debería ser @
        # Buscar patrón: palabra + o/a + palabra + .com
        resultado = re.sub(r'([a-z0-9])o([a-z]+\.(com|net|co))', r'\1@\2', resultado, flags=re.IGNORECASE)
        resultado = re.sub(r'([a-z0-9])a([a-z]+\.(com|net|co))', r'\1@\2', resultado, flags=re.IGNORECASE)
    
    # 2. Correcciones de dominios comunes
    correcciones_dominio = {
        r'hotmall': 'hotmail',
        r'gimal': 'gmail',
        r'gima': 'gmail',
        r'gmial': 'gmail',
        r'cutlook': 'outlook',
        r'\.can\b': '.com',
        r'\.cam\b': '.com',
        r'\.con\b': '.com',
    }
    
    for patron, reemplazo in correcciones_dominio.items():
        resultado = re.sub(patron, reemplazo, resultado, flags=re.IGNORECASE)
    
    # 3. Remover espacios
    resultado = resultado.replace(' ', '')
    
    # 4. Validación básica: debe tener @ y .
    if '@' in resultado and '.' in resultado:
        return resultado.lower()
    
    return texto  # Si no se pudo corregir, devolver original


def corregir_nombre(texto: str) -> str:
    """
    Corrige errores en nombres (primer_nombre, segundo_nombre, apellidos).
    
    Errores identificados:
    - Números en nombres: "Juan1" → "Juan"
    - Confusión l/1: "Mar1a" → "Maria"
    - Punto al final: "Natalia." → "Natalia"
    """
    if not texto or len(texto.strip()) == 0:
        return texto
    
    resultado = texto.strip()
    
    # 1. Remover dígitos (nombres nunca tienen números)
    resultado = re.sub(r'\d', '', resultado)
    
    # 2. Remover punto al final
    resultado = resultado.rstrip('.')
    
    # 3. Normalizar espacios
    resultado = re.sub(r'\s+', ' ', resultado)
    
    # 4. Capitalizar correctamente
    resultado = resultado.title()
    
    return resultado


def postprocesar_campos_express(campos: list) -> list:
    """
    Aplica correcciones post-procesamiento a campos extraídos.
    
    Solo toca los campos que tienen más errores según el análisis:
    - direccion (740 errores)
    - telefono_movil (673 errores)
    - email (375 errores)
    - ciudad (311 errores)
    - primer_nombre, segundo_nombre, apellidos (234-174 errores)
    
    Returns:
        Lista de campos con correcciones aplicadas
    """
    campos_corregidos = []
    
    for campo in campos:
        etiqueta = campo.get('etiqueta', '')
        valor_original = campo.get('valor', '')
        
        # Skip si está vacío
        if not valor_original or str(valor_original).strip() == '':
            campos_corregidos.append(campo)
            continue
        
        valor_corregido = None
        
        # Aplicar corrección según el campo
        if etiqueta == 'direccion':
            valor_corregido = corregir_direccion(valor_original)
            
        elif etiqueta == 'ciudad':
            valor_corregido = corregir_ciudad(valor_original)
            
        elif etiqueta in ['telefono_movil', 'telefono_fijo']:
            valor_corregido = corregir_telefono(valor_original)
            
        elif etiqueta == 'email':
            valor_corregido = corregir_email(valor_original)
            
        elif etiqueta in ['primer_nombre', 'segundo_nombre', 
                          'primer_apellido', 'segundo_apellido']:
            valor_corregido = corregir_nombre(valor_original)
        
        else:
            # No tocar otros campos
            campos_corregidos.append(campo)
            continue
        
        # Si se aplicó corrección
        if valor_corregido and valor_corregido != valor_original:
            campo_nuevo = campo.copy()
            campo_nuevo['valor'] = valor_corregido
            campo_nuevo['valor_original'] = valor_original
            campo_nuevo['postprocesado'] = True
            
            # Bajar un poco la confianza (fue corregido automáticamente)
            conf_actual = campo.get('confianza', 0)
            campo_nuevo['confianza'] = max(conf_actual - 5, 70)
            
            campos_corregidos.append(campo_nuevo)
        else:
            # No cambió, mantener original
            campos_corregidos.append(campo)
    
    return campos_corregidos


if __name__ == '__main__':
    # Pruebas con casos reales del CSV
    print("=== PRUEBAS DE POST-PROCESAMIENTO ===\n")
    
    casos_prueba = [
        ('direccion', "C11+389-13", "Cll 73 # 89-13"),
        ('direccion', "cl1 690# 72 038 508", "Cll 69 D # 72 C 38 Sur"),
        ('ciudad', "Bo50.t3", "Bogota"),
        ('ciudad', "FPANCA·FONTIRON", "Bogota (zona franca fontibon)"),
        ('telefono_movil', "3222940576", "3222940"),
        ('email', "tatianaivr64@cutlook.can", "tatianavr64@outlook.com"),
        ('primer_nombre', "Juan1", "Juan"),
        ('segundo_apellido', "Natalia.", "Natalia"),
    ]
    
    for etiqueta, valor_malo, valor_esperado in casos_prueba:
        if etiqueta == 'direccion':
            corregido = corregir_direccion(valor_malo)
        elif etiqueta == 'ciudad':
            corregido = corregir_ciudad(valor_malo)
        elif etiqueta.startswith('telefono'):
            corregido = corregir_telefono(valor_malo)
        elif etiqueta == 'email':
            corregido = corregir_email(valor_malo)
        else:
            corregido = corregir_nombre(valor_malo)
        
        print(f"{etiqueta:20s} | Malo: {valor_malo:30s} | Corregido: {corregido:30s}")
        print(f"{'':20s} | Esperado: {valor_esperado}")
        print()
