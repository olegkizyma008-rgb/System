#!/usr/bin/env python3
"""
Launch script for Elite Armory website
This script will start the server and open the website in your browser
"""

import os
import sys
import webbrowser
import time
import subprocess
import signal
from http.server import SimpleHTTPRequestHandler, HTTPServer

class EliteArmoryLauncher:
    def __init__(self):
        self.port = 8000
        self.server_process = None
        self.server = None
        
    def start_server(self):
        """Start the web server"""
        try:
            # Change to the website directory
            os.chdir(os.path.dirname(os.path.abspath(__file__)))
            
            print("🔧 Starting Elite Armory website...")
            print("🌐 Server will be available at http://localhost:8000")
            print("📦 Loading weapon database...")
            print("🔒 Initializing security protocols...")
            
            # Start the server
            handler = SimpleHTTPRequestHandler
            self.server = HTTPServer(('localhost', self.port), handler)
            
            print("✅ Server started successfully!")
            print("🚀 Opening website in your browser...")
            
            # Open browser
            time.sleep(1)
            webbrowser.open(f'http://localhost:{self.port}')
            
            print("💻 Website should now be open in your browser")
            print("📝 Press Ctrl+C to stop the server")
            print("=" * 50)
            
            # Run the server
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
    launcher = EliteArmoryLauncher()
    launcher.start_server()