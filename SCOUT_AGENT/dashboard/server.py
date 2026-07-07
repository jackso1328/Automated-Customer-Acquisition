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

    def do_POST(self):
        if self.path == '/api/generate-ad':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            
            try:
                request_json = json.loads(post_data.decode('utf-8'))
                target_company = request_json.get("company_or_entity")
                
                import sys
                src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
                if src_path not in sys.path:
                    sys.path.insert(0, src_path)
                    
                from src.ad_generator import generate_campaign_assets
                
                if os.path.exists(DB_FILE_PATH):
                    with open(DB_FILE_PATH, 'r+', encoding='utf-8') as f:
                        data = json.load(f)
                        
                        target_opp = None
                        for item in data:
                            if item.get("company_or_entity") == target_company:
                                target_opp = item
                                break
                                
                        if target_opp:
                            campaign = generate_campaign_assets(target_opp)
                            if campaign:
                                target_opp["campaign_assets"] = campaign
                                f.seek(0)
                                json.dump(data, f, indent=4)
                                f.truncate()
                                
                                self.send_response(200)
                                self.send_header('Content-Type', 'application/json')
                                self.end_headers()
                                self.wfile.write(json.dumps({"success": True, "campaign": campaign}).encode('utf-8'))
                            else:
                                self.send_response(500)
                                self.send_header('Content-Type', 'application/json')
                                self.end_headers()
                                self.wfile.write(json.dumps({"success": False, "error": "LLM generation failed"}).encode('utf-8'))
                        else:
                            self.send_response(404)
                            self.send_header('Content-Type', 'application/json')
                            self.end_headers()
                            self.wfile.write(json.dumps({"success": False, "error": "Opportunity not found"}).encode('utf-8'))
                else:
                    self.send_response(500)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"success": False, "error": "DB not found"}).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

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