#!/usr/bin/env python3
"""
Simplified launch script for Elite Armory website
Uses minimal resources while maintaining all features
"""

import os
import webbrowser
import time
from http.server import SimpleHTTPRequestHandler, HTTPServer

class SimpleWeaponShopServer:
    def __init__(self, port=8000):
        self.port = port
        self.server = None
        
    def start(self):
        """Start the web server with minimal resource usage"""
        try:
            # Change to website directory
            os.chdir(os.path.dirname(os.path.abspath(__file__)))
            
            print("🔧 Starting Elite Armory website (simplified)...")
            print("🌐 Server will be available at http://localhost:8000")
            
            # Start simple server
            handler = SimpleHTTPRequestHandler
            self.server = HTTPServer(('localhost', self.port), handler)
            
            # Open browser
            time.sleep(1)
            webbrowser.open(f'http://localhost:{self.port}')
            
            print("🚀 Website launched! Enjoy your modern Elite Armory.")
            print("📝 Press Ctrl+C to stop the server")
            
            # Run server
            self.server.serve_forever()
            
        except KeyboardInterrupt:
            print("\n🛑 Shutting down server...")
            self.server.server_close()
            print("✅ Server stopped")
        except Exception as e:
            print(f"❌ Error: {e}")
            if self.server:
                self.server.server_close()

if __name__ == '__main__':
    server = SimpleWeaponShopServer()
    server.start()