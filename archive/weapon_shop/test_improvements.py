#!/usr/bin/env python3
"""
Test script to verify all improvements to the Elite Armory website
"""

import os
import sys

def test_file_structure():
    """Test that all required files exist"""
    print("🔍 Testing file structure...")
    
    required_files = [
        'index.html',
        'css/style.css',
        'css/loading.css',
        'js/main.js',
        'js/loading.js',
        'images/placeholder.jpg',
        'launch_website.py',
        'server.py',
        'start.sh'
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ Missing files: {', '.join(missing_files)}")
        return False
    else:
        print("✅ All required files present")
        return True

def test_html_structure():
    """Test HTML file structure"""
    print("🔍 Testing HTML structure...")
    
    try:
        with open('index.html', 'r') as f:
            content = f.read()
            
        required_elements = [
            '<div id="loading-screen"',
            '<div id="main-content"',
            'loading.js',
            'main.js',
            'product-grid'
        ]
        
        missing_elements = []
        for element in required_elements:
            if element not in content:
                missing_elements.append(element)
        
        if missing_elements:
            print(f"❌ Missing HTML elements: {', '.join(missing_elements)}")
            return False
        else:
            print("✅ HTML structure is correct")
            return True
            
    except Exception as e:
        print(f"❌ Error reading HTML file: {e}")
        return False

def test_css_improvements():
    """Test CSS improvements"""
    print("🔍 Testing CSS improvements...")
    
    try:
        with open('css/loading.css', 'r') as f:
            loading_css = f.read()
        
        with open('css/style.css', 'r') as f:
            style_css = f.read()
        
        required_css_features = [
            ('css/loading.css', 'blinking-cursor'),
            ('css/loading.css', 'scanlines'),
            ('css/loading.css', 'pistol-line'),
            ('css/style.css', 'product-image-container'),
            ('css/style.css', 'weapon-icon'),
            ('css/style.css', 'weapon-line')
        ]
        
        missing_features = []
        for file, feature in required_css_features:
            with open(file, 'r') as f:
                file_content = f.read()
            if feature not in file_content:
                missing_features.append(f"{feature} in {file}")
        
        if missing_features:
            print(f"❌ Missing CSS features: {', '.join(missing_features)}")
            return False
        else:
            print("✅ CSS improvements are present")
            return True
            
    except Exception as e:
        print(f"❌ Error reading CSS files: {e}")
        return False

def test_javascript_enhancements():
    """Test JavaScript enhancements"""
    print("🔍 Testing JavaScript enhancements...")
    
    try:
        with open('js/loading.js', 'r') as f:
            loading_js = f.read()
        
        with open('js/main.js', 'r') as f:
            main_js = f.read()
        
        required_js_features = [
            ('js/loading.js', 'BOOTING SECURE SYSTEM'),
            ('js/loading.js', 'WELCOME TO ELITE ARMORY'),
            ('js/loading.js', 'pistolLines'),
            ('js/main.js', 'createWeaponIcon'),
            ('js/main.js', 'addHoverEffects'),
            ('js/main.js', 'weapon-icon')
        ]
        
        missing_features = []
        for file, feature in required_js_features:
            with open(file, 'r') as f:
                file_content = f.read()
            if feature not in file_content:
                missing_features.append(f"{feature} in {file}")
        
        if missing_features:
            print(f"❌ Missing JavaScript features: {', '.join(missing_features)}")
            return False
        else:
            print("✅ JavaScript enhancements are present")
            return True
            
    except Exception as e:
        print(f"❌ Error reading JavaScript files: {e}")
        return False

def test_weapon_data():
    """Test weapon data structure"""
    print("🔍 Testing weapon data...")
    
    try:
        with open('js/main.js', 'r') as f:
            content = f.read()
        
        # Check for weapon categories
        categories = ['Handguns', 'Rifles', 'Shotguns']
        missing_categories = []
        
        for category in categories:
            if category not in content:
                missing_categories.append(category)
        
        if missing_categories:
            print(f"❌ Missing weapon categories: {', '.join(missing_categories)}")
            return False
        else:
            print("✅ Weapon data structure is correct")
            return True
            
    except Exception as e:
        print(f"❌ Error reading weapon data: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Running Elite Armory Website Improvement Tests")
    print("=" * 50)
    
    tests = [
        test_file_structure,
        test_html_structure,
        test_css_improvements,
        test_javascript_enhancements,
        test_weapon_data
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Website improvements are working correctly.")
        print()
        print("🚀 Ready to launch with:")
        print("   python3 launch_website.py")
        return True
    else:
        print("❌ Some tests failed. Please check the issues above.")
        return False

if __name__ == '__main__':
    # Change to website directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    success = main()
    sys.exit(0 if success else 1)