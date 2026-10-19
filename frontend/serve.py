import http.server
import socketserver
import webbrowser
import os
import sys

PORT = 8080
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def log_message(self, format, *args):
        # Clean formatted terminal output for project evaluation
        sys.stdout.write(f"[Touchless PDF Studio] {self.address_string()} - {format % args}\n")

if __name__ == "__main__":
    os.chdir(DIRECTORY)
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        url = f"http://localhost:{PORT}/index.html"
        print("=" * 64)
        print("  TOUCHLESS PDF EVALUATION STUDIO — LOCAL WEB SERVER")
        print("=" * 64)
        print(f"\n  [OK] Server running at: {url}")
        print("  [OK] Opening in default web browser...\n")
        print("  Controls available on this web demo:")
        print("   - Wave Right ➔ : Next Page")
        print("   - Wave Left ⬅ : Previous Page")
        print("   - Peace Sign ✌️: Smooth Document Scrolling")
        print("   - L-Shape Up/Down: Zoom In / Out")
        print("   - Index Point 👆: Presentation Laser Pointer")
        print("   - Pinch Fingers 👌: Click Toolbar Buttons")
        print("   - Fullscreen ⛶ : F Key or Fullscreen button")
        print("\n  Press Ctrl+C to stop the server.\n")
        print("=" * 64)
        try:
            webbrowser.open(url)
        except Exception:
            pass
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server cleanly.")
