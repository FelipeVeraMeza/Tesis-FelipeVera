"""
Servidor de correo local para demostración (RF7).

Recibe los correos que emite el sistema y los guarda en disco, permitiendo
verificar el envío de las notificaciones sin depender de un servidor
institucional ni enviar mensajes reales.

Uso:
    python backend/servidor_correo_prueba.py

Luego, en el archivo .env:
    SMTP_HOST=localhost
    SMTP_PUERTO=1025
    SMTP_TLS=False

Los mensajes recibidos quedan en backend/correos_recibidos/.
"""
import asyncio
import email
import sys
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
DESTINO = RAIZ.parent / "correos_recibidos"

PUERTO = 1025


class Buzon(asyncio.Protocol):
    """Implementación mínima de SMTP: recibe el mensaje y lo guarda."""

    def connection_made(self, transporte):
        self.transporte = transporte
        self.buffer = b""
        self.en_datos = False
        self.transporte.write(b"220 localhost Servidor de prueba\r\n")

    def data_received(self, datos):
        if self.en_datos:
            self.buffer += datos
            if b"\r\n.\r\n" in self.buffer:
                self._guardar(self.buffer.split(b"\r\n.\r\n")[0])
                self.buffer = b""
                self.en_datos = False
                self.transporte.write(b"250 Mensaje aceptado\r\n")
            return

        for linea in datos.split(b"\r\n"):
            if not linea:
                continue
            orden = linea.upper()

            if orden.startswith((b"EHLO", b"HELO")):
                self.transporte.write(b"250-localhost\r\n250 OK\r\n")
            elif orden.startswith((b"MAIL FROM", b"RCPT TO")):
                self.transporte.write(b"250 OK\r\n")
            elif orden.startswith(b"DATA"):
                self.en_datos = True
                self.transporte.write(b"354 Escriba el mensaje\r\n")
            elif orden.startswith(b"QUIT"):
                self.transporte.write(b"221 Cierre\r\n")
                self.transporte.close()
            elif orden.startswith(b"RSET"):
                self.transporte.write(b"250 OK\r\n")

    def _guardar(self, crudo: bytes) -> None:
        DESTINO.mkdir(exist_ok=True)

        mensaje = email.message_from_bytes(crudo)
        marca = datetime.now()
        archivo = DESTINO / f"{marca:%Y%m%d_%H%M%S}_{marca.microsecond}.eml"
        archivo.write_bytes(crudo)

        # Cuerpo en texto plano, para mostrarlo en la consola
        cuerpo = ""
        if mensaje.is_multipart():
            for parte in mensaje.walk():
                if parte.get_content_type() == "text/plain":
                    cuerpo = parte.get_payload(decode=True).decode("utf-8", "replace")
                    break
        else:
            cuerpo = mensaje.get_payload(decode=True).decode("utf-8", "replace")

        print()
        print("=" * 66)
        print(f"  CORREO RECIBIDO  ·  {marca:%H:%M:%S}")
        print("=" * 66)
        print(f"  De      : {mensaje['From']}")
        print(f"  Para    : {mensaje['To']}")
        print(f"  Asunto  : {mensaje['Subject']}")
        print("-" * 66)
        for linea in cuerpo.strip().split("\n"):
            print(f"  {linea}")
        print("-" * 66)
        print(f"  Guardado en: {archivo.name}")
        print()


async def main() -> None:
    servidor = await asyncio.get_running_loop().create_server(Buzon, "localhost", PUERTO)

    print("=" * 66)
    print(" Servidor de correo de prueba")
    print("=" * 66)
    print(f"  Escuchando en : localhost:{PUERTO}")
    print(f"  Guardando en  : {DESTINO}")
    print()
    print("  Configure en el archivo .env:")
    print("    SMTP_HOST=localhost")
    print(f"    SMTP_PUERTO={PUERTO}")
    print("    SMTP_TLS=False")
    print()
    print("  Presione Ctrl+C para detener.")

    async with servidor:
        await servidor.serve_forever()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n  Servidor detenido.")
        sys.exit(0)
