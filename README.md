# Tipo de cambio Banguat (USD/GTQ, EUR/USD, EUR/GTQ)

Pagina publica que se actualiza sola con el tipo de cambio de referencia del
Banco de Guatemala. Corre gratis en GitHub (Actions + Pages); no necesita servidor
ni Databricks.

- `generar.py`: consulta el Web Service de Banguat, valida y genera `docs/`.
- `plantilla/index.html`: diseno de la pagina.
- `.github/workflows/actualizar.yml`: corre `generar.py` cada 2 horas (6:15 a 20:15 hora GT) y publica.
- `docs/index.html`: la pagina que se publica.
- `estado.txt`: huella de los datos publicados (para no republicar si nada cambio).

## Puesta en marcha (una sola vez)

1. Crear una cuenta en https://github.com/signup.
2. **New repository** -> nombre `tipo-cambio-gt` -> **Public** -> Create.
3. **Add file -> Upload files** y arrastrar el contenido de esta carpeta.
   Si la carpeta `.github` no se sube (algunas computadoras ocultan carpetas que empiezan
   con punto): **Add file -> Create new file**, escribir como nombre
   `.github/workflows/actualizar.yml` y pegar el contenido de ese archivo.
4. **Settings -> Pages -> Build and deployment -> Source: GitHub Actions**.
5. **Actions** -> (habilitar si lo pide) -> **Actualizar tipo de cambio** -> **Run workflow**.
6. Al terminar (1-2 min) la pagina queda en:
   `https://<usuario>.github.io/tipo-cambio-gt/`

Si el paso "Guardar cambios" falla por permisos:
**Settings -> Actions -> General -> Workflow permissions -> Read and write permissions**.

## Como se calcula el EUR/GTQ

EUR/GTQ = promedio(compra, venta) EUR/USD x USD/GTQ del mismo dia.
El EUR solo se publica en dias habiles. La pagina explica el calculo y permite
descargar el historico en CSV.

## Notas

- GitHub puede atrasar unos minutos las corridas programadas.
- Si la validacion falla (datos viejos o fuera de rango) no se publica nada y
  GitHub envia un correo al dueno del repositorio.
- GitHub pausa los workflows programados de repos publicos sin actividad en 60 dias;
  este workflow hace un commit cada vez que Banguat publica datos nuevos, asi que se
  mantiene activo. Si alguna vez se pausa: Actions -> Enable workflow.
