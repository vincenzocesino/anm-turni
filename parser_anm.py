import re
import pdfplumber

SPECIAL_TYPES = [
    'CONGEDO ORDINARIO', 'NON PRESTAZIONE',
    'DISP. MATTINALE', 'DISP. SERALE',
    'PRE-LAVORATO', 'RIPOSO', 'FERIE'
]

def parse_turni_pdf(filepath):
    """Legge un PDF quindicinale ANM (SIPNRR01).
    Ritorna (info_dict, lista_record) oppure (None, []) se non riconosciuto.
    """
    try:
        with pdfplumber.open(filepath) as pdf:
            text = '\n'.join(page.extract_text() or '' for page in pdf.pages)
    except Exception:
        return None, []

    if 'TURNI DI SERVIZIO' not in text:
        return None, []

    m_sig = re.search(r'Sig\.\s+(.+?)\s+matr\.\s+(\d+)', text)
    if not m_sig:
        return None, []
    nome = m_sig.group(1).strip()
    matricola = m_sig.group(2).strip()

    m_per = re.search(r'DAL\s+(\d{2}/\d{2}/\d{4})\s+AL\s+(\d{2}/\d{2}/\d{4})', text)
    dal = m_per.group(1) if m_per else ''
    al = m_per.group(2) if m_per else ''

    records = []
    for line in text.split('\n'):
        line = line.strip()
        dm = re.match(r'^(Lun|Mar|Mer|Gio|Ven|Sab|Dom)\s+(\d{2}/\d{2}/\d{4})\s+(.*)', line)
        if not dm:
            continue

        giorno, data, rest = dm.group(1), dm.group(2), dm.group(3).strip()
        rec = {
            'matricola': matricola,
            'nome': nome,
            'giorno': giorno,
            'data': data,
            'tipo': 'TURNO',
            'monto': '',
            'turno_macchina': '',
            'localita': '',
            'durata': '',
            'fine_servizio': '',
            'cadenza': '',
        }

        special = next((s for s in SPECIAL_TYPES if rest.startswith(s)), None)
        if special:
            rec['tipo'] = special
        else:
            # Formato: HH:MM TURNO/N LUOGO HH:MM Norm 70 HH:MM MM' (Dep|Linea) N
            t = re.match(
                r'(\d{2}:\d{2})\s+([\w/]+)\s+(\w+)\s+\d{2}:\d{2}\s+Norm\s+\d+\s+(\d{2}:\d{2})\s+\d+\'\s+(Dep|Linea)',
                rest
            )
            if t:
                rec['monto'] = t.group(1)
                rec['turno_macchina'] = t.group(2)
                rec['localita'] = t.group(3)
                rec['durata'] = t.group(4)
                rec['fine_servizio'] = t.group(5)
                # Calcola orario fine stimato
                rec['cadenza'] = _calc_fine(t.group(1), t.group(4))
            else:
                # Parse parziale
                t2 = re.match(r'(\d{2}:\d{2})\s+([\w/]+)\s+(\w+)', rest)
                if t2:
                    rec['monto'] = t2.group(1)
                    rec['turno_macchina'] = t2.group(2)
                    rec['localita'] = t2.group(3)

        records.append(rec)

    info = {'nome': nome, 'matricola': matricola, 'dal': dal, 'al': al}
    return info, records


def _calc_fine(monto_str, durata_str):
    """Calcola orario di fine stimato da monto + durata (HH:MM)."""
    try:
        mh, mm = map(int, monto_str.split(':'))
        dh, dm = map(int, durata_str.split(':'))
        total_min = (mh * 60 + mm) + (dh * 60 + dm)
        total_min = total_min % (24 * 60)
        return f"{total_min // 60:02d}:{total_min % 60:02d}"
    except Exception:
        return ''


def parse_matricole_pdf(filepath):
    """Legge matrAUTISTI.pdf e ritorna dict {matricola: nome}."""
    try:
        with pdfplumber.open(filepath) as pdf:
            text = '\n'.join(page.extract_text() or '' for page in pdf.pages)
    except Exception:
        return {}

    autisti = {}
    # Pattern: 5 cifre + nome in CAPS (con spazi, punti, apostrofi)
    for m in re.finditer(r'\b(\d{5})\s+([A-Z][A-Z\s\.\'\-]{1,28}?)(?=\s{2,}|\s*\d{5}|\s*\d\s|\s*\n|\s*$)', text):
        matr = m.group(1)
        nome = m.group(2).strip().rstrip('. ')
        if nome and len(nome) > 1:
            autisti[matr] = nome
    return autisti
