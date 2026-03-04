from argon2 import PasswordHasher

ph = PasswordHasher()

def hashear_carnet(idclient):
    """
    Genera un hash de Argon2 y lo devuelve en formato hexadecimal.
    """
    # Generar hash original (formato PHC)
    res_phc = ph.hash(str(idclient))
    # Convertir a Hexadecimal (Opción A)
    res_hex = res_phc.encode('utf-8').hex()
    return res_hex

def hash_contra(contra):
    return ph.hash(contra)
