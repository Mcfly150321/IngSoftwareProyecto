import secrets

def generar_codigo_verificacion() -> str:
    """
    Genera un código de verificación de 6 dígitos de forma criptográficamente segura.
    Al usar un bucle y unir caracteres, permite que el código pueda empezar con '0' 
    (por ejemplo: '013485'), manteniendo siempre la longitud exacta de 6.
    """
    # Genera 6 dígitos individuales del 0 al 9 y los une en un solo string
    codigo_completo = "".join(str(secrets.randbelow(10)) for _ in range(6))
    return codigo_completo

# Ejecución principal para retornar el código en la consola
if __name__ == "__main__":
    codigo_seguro = generar_codigo_verificacion()
    
    print("====================================")
    print(f"CÓDIGO DE VERIFICACIÓN: {codigo_seguro}")
    print("====================================")