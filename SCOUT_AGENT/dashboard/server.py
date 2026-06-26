import os
import json
import http.server
import socketserver
import logging

PORT = 8000
# The JSON database is located one level up from the dashboard folder
DB_FILE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "opportunities.json"))

class DashboardHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # API Endpoint for fetching opportunities data dynamically
        if self.path == '/api/opportunities':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            # Allow cross-origin requests just in case
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            if os.path.exists(DB_FILE_PATH):
                try:
                    with open(DB_FILE_PATH, 'r', encoding='utf-8') as f:
                        data = f.read()
                    self.wfile.write(data.encode('utf-8'))
                except Exception as e:
                    self.wfile.write(json.dumps([{"error": f"Failed to read data: {str(e)}"}]).encode('utf-8'))
            else:
                self.wfile.write(json.dumps([]).encode('utf-8'))
        else:
            # Serve regular static assets (index.html, style.css, script.js)
            super().do_GET()

def run_dashboard_server():
    # Ensure we serve files out of the directory where server.py lives
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Allow port reuse immediately upon restarting to avoid address-already-in-use blocks
    socketserver.TCPServer.allow_reuse_address = True
    
    with socketserver.TCPServer(("", PORT), DashboardHTTPRequestHandler) as httpd:
        print(f"\n[SBI Scout Dashboard] Active and running locally at: http://localhost:{PORT}")
        print("Keep this terminal open to view your live data feed.\n")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down dashboard server cleanly...")
            httpd.server_close()

if __name__ == '__main__':
    run_dashboard_server()