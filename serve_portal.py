# serve_portal.py
import http.server
import socketserver
import webbrowser
import os
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

PORT = int(os.environ.get("PORT", 8080))
HOST = os.environ.get("HOST", "0.0.0.0")
DIRECTORY = os.path.join(os.path.dirname(__file__), "portal_inmobiliario")

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

def main():
    if not os.path.exists(DIRECTORY):
        print(f"Error: No se encontró el directorio del portal: {DIRECTORY}")
        sys.exit(1)

    url = f"http://localhost:{PORT}" if HOST in ["0.0.0.0", ""] else f"http://{HOST}:{PORT}"
    print("=" * 65)
    print(f">> SERVIDOR PORTAL INMOBILIARIO — CIUDAD DE PANAMÁ")
    print(f">> Activo en: {url} (Host: {HOST}, Port: {PORT})")
    print(f">> Directorio: {DIRECTORY}")
    print(">> Presiona Ctrl+C para detener el servidor.")
    print("=" * 65)

    # Open browser only in local interactive mode (not in containers/cloud)
    if "PORT" not in os.environ and "DOCKER" not in os.environ:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer((HOST, PORT), Handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServidor detenido.")

if __name__ == "__main__":
    main()
