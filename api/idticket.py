from datetime import datetime
from sqlalchemy.orm import Session
from . import models

def generate_idticket(db: Session):
    now = datetime.now()
    year = now.year
    month = now.month
    day = now.day
    # Suffix for the search (YYYYMMDD) - we want to match tickets from TODAY
    date_str = f"{year}{month:02d}{day:02d}"

    # Busca el idclient más alto que empiece con la fecha de hoy
    max_idticket = db.query(models.Client.idclient).filter(
        models.Client.idclient.like(f"{date_str}%")
    ).order_by(models.Client.idclient.desc()).first()
    
    if max_idticket:
        try:
            # El formato será YYYYMMDDNNNNN (13 caracteres)
            # Extraemos los últimos 5 dígitos (secuencia)
            last_seq = int(max_idticket[0][-5:])
            new_seq = last_seq + 1
        except (ValueError, IndexError):
            new_seq = 1
    else:
        new_seq = 1
        
    return f"{date_str}{new_seq:05d}"