#!/usr/bin/env python3
"""
Simple Python server for Elite Armory website
"""

from http.server import SimpleHTTPRequestHandler, HTTPServer
import webbrowser
import threading
import time

class WeaponShopServer:
    def __init__(self, port=8000):
        self.port = port
        self.server = None
        
    def start(self):
        """Start the web server"""
        handler = SimpleHTTPRequestHandler
        
        self.server = HTTPServer(('localhost', self.port), handler)
        
        print(f"Starting Elite Armory server on http://localhost:{self.port}")
        print("Press Ctrl+C to stop the server")
        
        # Open browser after a short delay
        def open_browser():
            time.sleep(1)
            webbrowser.open(f'http://localhost:{self.port}')
        
        browser_thread = threading.Thread(target=open_browser)
        browser_thread.daemon = True
        browser_thread.start()
        
        try:
            self.server.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server...")
            self.server.server_close()

if __name__ == '__main__':
    server = WeaponShopServer()
    server.start()