"""
Genera la pagina publica de tipo de cambio (Banguat) para GitHub Pages.

Salida: docs/index.html, la pagina con los datos incrustados
(la descarga de CSV la hace la misma pagina en el navegador).

Si los datos no cambiaron desde la ultima corrida, no reescribe nada
(asi solo hay un commit cuando Banguat publica algo nuevo).
Si las validaciones fallan, termina con error y NO publica.
"""
import hashlib
import json
import os
import sys
import time
import datetime as dt
import xml.etree.ElementTree as ET

import requests

URL = "https://www.banguat.gob.gt/variables/ws/TipoCambio.asmx"
NS = "http://www.banguat.gob.gt/variables/ws/"
USD, EUR = 2, 24
ANIOS_HIST = int(os.environ.get("TC_ANIOS_HIST", "3"))
TZ_GT = dt.timezone(dt.timedelta(hours=-6))
RAIZ = os.path.dirname(os.path.abspath(__file__))
PLANTILLA = os.path.join(RAIZ, "plantilla", "index.html")
SALIDA = os.path.join(RAIZ, "docs")
ESTADO = os.path.join(RAIZ, "estado.txt")  # huella de los datos publicados

_ses = requests.Session()


def _local(tag):
    return tag.split("}", 1)[-1]


def _soap(op, params, intentos=4):
    cuerpo = "".join(f"<{k}>{v}</{k}>" for k, v in params.items())
    env = (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">'
        f'<soap:Body><{op} xmlns="{NS}">{cuerpo}</{op}></soap:Body></soap:Envelope>'
    )
    hdr = {"Content-Type": "text/xml; charset=utf-8", "SOAPAction": f'"{NS}{op}"'}
    for i in range(intentos):
        try:
            r = _ses.post(URL, data=env.encode(), headers=hdr, timeout=60)
            r.raise_for_status()
            return ET.fromstring(r.content)
        except Exception:
            if i == intentos - 1:
                raise
            time.sleep(2 ** i)


def rango(moneda, ini, fin):
    """{fecha: (compra, venta)} en bloques anuales."""
    out = {}
    a = ini
    while a <= fin:
        b = min(dt.date(a.year, 12, 31), fin)
        root = _soap("TipoCambioRangoMoneda", {
            "fechainit": a.strftime("%d/%m/%Y"),
            "fechafin": b.strftime("%d/%m/%Y"),
            "moneda": moneda,
        })
        for el in root.iter():
            if _local(el.tag) != "Var":
                continue
            d = {_local(h.tag): (h.text or "").strip() for h in el}
            try:
                f = dt.datetime.strptime(d["fecha"], "%d/%m/%Y").date()
                out[f] = (float(d["compra"]), float(d["venta"]))
            except (KeyError, ValueError):
                continue
        a = b + dt.timedelta(days=1)
        time.sleep(0.3)
    return dict(sorted(out.items()))


def main():
    ahora = dt.datetime.now(TZ_GT)
    hoy = ahora.date()
    ini = dt.date(hoy.year - ANIOS_HIST, 1, 1)
    usd = rango(USD, ini, hoy)
    eur = rango(EUR, ini, hoy)
    print(f"USD: {len(usd)} dias, ultimo {max(usd)} | EUR: {len(eur)} dias, ultimo {max(eur)}")

    # --- cruce EUR -> USD -> GTQ
    fechas_usd = list(usd)

    def usd_al(f):
        if f in usd:
            return usd[f][1]
        prev = [x for x in fechas_usd if x <= f]
        return usd[prev[-1]][1] if prev else None

    eur_rows = []
    for f, (c, v) in eur.items():
        u = usd_al(f)
        if u is not None:
            eur_rows.append([f.isoformat(), round((c + v) / 2 * u, 5), c, v, u])
    usd_rows = [[f.isoformat(), v[1]] for f, v in usd.items()]

    # --- validaciones: si algo esta mal, no se publica
    errores = []
    ult_usd_f = max(usd)
    if len(usd) < 300:
        errores.append(f"muy pocos datos USD ({len(usd)})")
    if (hoy - ult_usd_f).days > 3:
        errores.append(f"USD desactualizado (ultimo {ult_usd_f})")
    if (hoy - max(eur)).days > 6:
        errores.append(f"EUR desactualizado (ultimo {max(eur)})")
    if not 6.0 <= usd[ult_usd_f][1] <= 10.0:
        errores.append(f"USD/GTQ fuera de rango ({usd[ult_usd_f][1]})")
    if not 4.0 <= eur_rows[-1][1] <= 14.0:
        errores.append(f"EUR/GTQ fuera de rango ({eur_rows[-1][1]})")
    if errores:
        sys.exit("No se publica: " + "; ".join(errores))

    # --- sin cambios en los datos -> no reescribir
    huella = hashlib.sha256(json.dumps([usd_rows, eur_rows]).encode()).hexdigest()
    if os.path.exists(ESTADO) and open(ESTADO).read().strip() == huella:
        print("Sin cambios en los datos; no se reescribe nada.")
        return

    payload = {
        "actualizado": ahora.isoformat(timespec="seconds"),
        "desactualizado": False,
        "error": None,
        "fuente": "Banco de Guatemala - Web Service TipoCambio",
        "usd": usd_rows,
        "eur": eur_rows,
    }
    os.makedirs(SALIDA, exist_ok=True)

    # index.html
    with open(PLANTILLA, encoding="utf-8") as fh:
        plantilla = fh.read()
    marca = "<script>\n(() => {"
    if plantilla.count(marca) != 1:
        sys.exit("La plantilla no tiene el punto de insercion esperado")
    datos = json.dumps(payload, separators=(",", ":")).replace("</", "<\\/")
    html = plantilla.replace(
        marca, f"<script>window.TC_STATIC = {datos};</script>\n{marca}", 1)
    with open(os.path.join(SALIDA, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(html)

    # GitHub Pages: servir los archivos tal cual
    open(os.path.join(SALIDA, ".nojekyll"), "w").close()
    with open(ESTADO, "w") as fh:
        fh.write(huella + "\n")
    print(f"Publicado: USD/GTQ {usd_rows[-1][1]} ({usd_rows[-1][0]}) | EUR/GTQ {eur_rows[-1][1]} ({eur_rows[-1][0]})")


if __name__ == "__main__":
    main()
