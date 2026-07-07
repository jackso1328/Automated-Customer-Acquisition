"""
server.py — Dashboard HTTP Server

Serves the static dashboard files and provides two API endpoints:
  GET  /api/opportunities  — Returns all scored leads as JSON.
  POST /api/generate-ad    — Triggers campaign generation for a specific lead.
"""

import os
import sys
import json
import http.server
import socketserver
import logging

PORT = 8000

# Resolve paths relative to this file, not the CWD
_DASHBOARD_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_DASHBOARD_DIR, ".."))
DB_FILE_PATH = os.path.join(_PROJECT_ROOT, "opportunities.json")

# Ensure the src/ package is importable
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


class DashboardHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Handles both static file serving and API endpoints."""

    def _send_json(self, status_code, data):
        """Helper to send a JSON response with proper headers."""
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def do_OPTIONS(self):
        """Handle CORS preflight requests."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        if self.path == "/api/opportunities":
            if not os.path.exists(DB_FILE_PATH):
                return self._send_json(200, [])
            try:
                with open(DB_FILE_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._send_json(200, data)
            except Exception as e:
                self._send_json(500, {"error": f"Failed to read data: {e}"})
        else:
            super().do_GET()

    def do_POST(self):
        if self.path == "/api/generate-ad":
            self._handle_generate_ad()
        else:
            self._send_json(404, {"error": "Endpoint not found"})

    def _handle_generate_ad(self):
        """Generates campaign assets for a specific opportunity and persists them."""
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            request_json = json.loads(self.rfile.read(content_length).decode("utf-8"))
            target_company = request_json.get("company_or_entity")

            if not target_company:
                return self._send_json(400, {"success": False, "error": "Missing company_or_entity"})

            if not os.path.exists(DB_FILE_PATH):
                return self._send_json(500, {"success": False, "error": "Database file not found"})

            # Read current data
            with open(DB_FILE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Find the target opportunity
            target_opp = next(
                (item for item in data if item.get("company_or_entity") == target_company),
                None
            )

            if not target_opp:
                return self._send_json(404, {"success": False, "error": "Opportunity not found"})

            # Generate campaign assets
            from src.ad_generator import generate_campaign_assets
            campaign = generate_campaign_assets(target_opp)

            if not campaign:
                return self._send_json(500, {"success": False, "error": "LLM generation failed"})

            # Persist campaign data back to JSON
            target_opp["campaign_assets"] = campaign
            with open(DB_FILE_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)

            self._send_json(200, {"success": True, "campaign": campaign})

        except Exception as e:
            logging.error(f"[Server] Error generating ad: {e}")
            self._send_json(500, {"success": False, "error": str(e)})


def run_dashboard_server():
    """Starts the dashboard HTTP server on the configured port."""
    os.chdir(_DASHBOARD_DIR)

    socketserver.TCPServer.allow_reuse_address = True

    with socketserver.TCPServer(("", PORT), DashboardHTTPRequestHandler) as httpd:
        print(f"\n[SBI Scout Dashboard] Active at: http://localhost:{PORT}")
        print("Keep this terminal open to view your live data feed.\n")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down dashboard server cleanly...")
            httpd.server_close()


if __name__ == "__main__":
    run_dashboard_server()