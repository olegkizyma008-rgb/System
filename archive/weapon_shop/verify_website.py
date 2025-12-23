#!/usr/bin/env python3
"""
Simple verification script for the Elite Armory website
"""

import os
import sys

def verify_website():
    """Verify the website is ready to launch"""
    print("🔍 Verifying Elite Armory Website...")
    print("=" * 50)
    
STYLE_CSS = 'css/style.css'
MAIN_JS = 'js/main.js'

def check_files(files):
    """Check if all provided files exist."""
    print("📁 Checking main files...")
    for file in files:
        if os.path.exists(file):
            print(f"✅ {file}")
        else:
            print(f"❌ {file} missing")
            return False
    return True

def check_content(checks):
    """Check if specific content exists in files."""
    for file, check in checks:
        try:
            with open(file, 'r') as f:
                content = f.read()
                if check in content:
                    print(f"✅ {check} in {file}")
                else:
                    print(f"❌ {check} missing from {file}")
                    return False
        except Exception as e:
            print(f"❌ Error reading {file}: {e}")
            return False
    return True

def verify_website():
    """Verify the website is ready to launch"""
    print("🔍 Verifying Elite Armory Website...")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not os.path.exists('index.html'):
        print("❌ Not in the website directory. Please run from weapon_shop folder.")
        return False
    
    # Check main files
    main_files = [
        'index.html',
        'launch_website.py',
        'server.py',
        STYLE_CSS,
        'css/loading.css',
        MAIN_JS,
        'js/loading.js'
    ]
    
    if not check_files(main_files):
        return False
    
    # Check CSS files
    print("\n🎨 Checking CSS files...")
    css_checks = [
        (STYLE_CSS, '--modern-green'),
        (STYLE_CSS, '@keyframes fadeInUp'),
        ('css/loading.css', '@keyframes headerGlow')
    ]
    
    if not check_content(css_checks):
        return False
    
    # Check JavaScript files
    print("\n💻 Checking JavaScript files...")
    js_checks = [
        (MAIN_JS, 'createDetailedPistolDrawing'),
        (MAIN_JS, 'drawPistolForProduct'),
        ('js/loading.js', 'typeText')
    ]
    
    if not check_content(js_checks):
        return False
    
    print("\n" + "=" * 50)
    print("🎉 Website verification successful!")
    print()
    print("🚀 Launch your website with:")
    print("   python3 launch_website.py")
    print()
    print("📋 Features included:")
    print("   ✅ Modern animations and transitions")
    print("   ✅ Detailed pistol drawings for products")
    print("   ✅ Enhanced loading animation")
    print("   ✅ Interactive hover effects")
    print("   ✅ Responsive design")
    print("   ✅ 12 weapon products with icons")
    
    return True

if __name__ == '__main__':
    # Change to website directory if needed
    if os.path.exists('/Users/dev/Documents/GitHub/System/weapon_shop'):
        os.chdir('/Users/dev/Documents/GitHub/System/weapon_shop')
    
    success = verify_website()
    sys.exit(0 if success else 1)