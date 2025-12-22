#!/usr/bin/env python3
"""
Test script to verify all modern enhancements to the Elite Armory website
"""

import os
import sys

def test_modern_css():
    """Test modern CSS enhancements"""
    print("🔍 Testing modern CSS enhancements...")
    
    try:
        with open('css/style.css', 'r') as f:
            style_css = f.read()
        
        with open('css/loading.css', 'r') as f:
            loading_css = f.read()
        
        modern_css_features = [
            ('css/style.css', '--modern-green'),
            ('css/style.css', '--hover-green'),
            ('css/style.css', '@keyframes fadeInUp'),
            ('css/style.css', '@keyframes pulse'),
            ('css/style.css', '@keyframes slideIn'),
            ('css/style.css', 'btn::before'),
            ('css/style.css', 'header::before'),
            ('css/style.css', 'nav.scrolled'),
            ('css/style.css', 'nav ul::before'),
            ('css/style.css', 'nav ul li a::before'),
            ('css/loading.css', '@keyframes headerGlow'),
            ('css/loading.css', '@keyframes textReveal'),
            ('css/loading.css', '@keyframes underlineGlow'),
            ('css/loading.css', '@keyframes lineDraw'),
            ('css/loading.css', '@keyframes containerGlow'),
            ('css/loading.css', 'pistol-drawing::before')
        ]
        
        missing_features = []
        for file, feature in modern_css_features:
            with open(file, 'r') as f:
                file_content = f.read()
            if feature not in file_content:
                missing_features.append(f"{feature} in {file}")
        
        if missing_features:
            print(f"❌ Missing modern CSS features: {', '.join(missing_features)}")
            return False
        else:
            print("✅ All modern CSS enhancements present")
            return True
            
    except Exception as e:
        print(f"❌ Error reading CSS files: {e}")
        return False

def test_modern_javascript():
    """Test modern JavaScript enhancements"""
    print("🔍 Testing modern JavaScript enhancements...")
    
    try:
        with open('js/main.js', 'r') as f:
            main_js = f.read()
        
        with open('js/loading.js', 'r') as f:
            loading_js = f.read()
        
        modern_js_features = [
            ('js/main.js', 'createDetailedPistolDrawing'),
            ('js/main.js', 'drawPistolForProduct'),
            ('js/main.js', 'addModernAnimations'),
            ('js/main.js', 'setupScrollEffects'),
            ('js/main.js', 'modern-tooltip'),
            ('js/loading.js', 'span.style.animationDelay'),
            ('js/loading.js', 'lineElement.style.transition'),
            ('js/loading.js', 'pistolDrawing.style.opacity')
        ]
        
        missing_features = []
        for file, feature in modern_js_features:
            with open(file, 'r') as f:
                file_content = f.read()
            if feature not in file_content:
                missing_features.append(f"{feature} in {file}")
        
        if missing_features:
            print(f"❌ Missing modern JavaScript features: {', '.join(missing_features)}")
            return False
        else:
            print("✅ All modern JavaScript enhancements present")
            return True
            
    except Exception as e:
        print(f"❌ Error reading JavaScript files: {e}")
        return False

def test_detailed_pistol_drawings():
    """Test detailed pistol drawings for products"""
    print("🔍 Testing detailed pistol drawings...")
    
    try:
        with open('js/main.js', 'r') as f:
            content = f.read()
        
        # Check for pistol drawing lines
        pistol_features = [
            'pistol-drawing-product',
            'pistol-line-product',
            'drawPistolForProduct',
            'createDetailedPistolDrawing'
        ]
        
        missing_features = []
        for feature in pistol_features:
            if feature not in content:
                missing_features.append(feature)
        
        if missing_features:
            print(f"❌ Missing pistol drawing features: {', '.join(missing_features)}")
            return False
        else:
            print("✅ Detailed pistol drawings implemented")
            return True
            
    except Exception as e:
        print(f"❌ Error testing pistol drawings: {e}")
        return False

def test_modern_animations():
    """Test modern animation features"""
    print("🔍 Testing modern animations...")
    
    try:
        with open('css/style.css', 'r') as f:
            style_css = f.read()
        
        with open('css/loading.css', 'r') as f:
            loading_css = f.read()
        
        animation_features = [
            ('css/style.css', '@keyframes fadeInUp'),
            ('css/style.css', '@keyframes pulse'),
            ('css/style.css', 'transition: all var(--transition-speed)'),
            ('css/loading.css', '@keyframes textReveal'),
            ('css/loading.css', '@keyframes lineDraw'),
            ('css/loading.css', '@keyframes headerGlow')
        ]
        
        missing_features = []
        for file, feature in animation_features:
            with open(file, 'r') as f:
                file_content = f.read()
            if feature not in file_content:
                missing_features.append(f"{feature} in {file}")
        
        if missing_features:
            print(f"❌ Missing animation features: {', '.join(missing_features)}")
            return False
        else:
            print("✅ Modern animations implemented")
            return True
            
    except Exception as e:
        print(f"❌ Error testing animations: {e}")
        return False

def test_modern_ui_elements():
    """Test modern UI elements"""
    print("🔍 Testing modern UI elements...")
    
    try:
        with open('css/style.css', 'r') as f:
            content = f.read()
        
        ui_features = [
            'header::before',
            'nav.scrolled',
            'nav ul::before',
            'nav ul li a::before',
            'logo h1:hover',
            'logo p::after',
            'btn::before',
            'product-card:nth-child'
        ]
        
        missing_features = []
        for feature in ui_features:
            if feature not in content:
                missing_features.append(feature)
        
        if missing_features:
            print(f"❌ Missing modern UI elements: {', '.join(missing_features)}")
            return False
        else:
            print("✅ Modern UI elements implemented")
            return True
            
    except Exception as e:
        print(f"❌ Error testing UI elements: {e}")
        return False

def test_responsive_design():
    """Test responsive design features"""
    print("🔍 Testing responsive design...")
    
    try:
        with open('css/style.css', 'r') as f:
            content = f.read()
        
        responsive_features = [
            '@media (max-width: 768px)',
            'flex-direction: column',
            'width: 95%',
            'height: 90%'
        ]
        
        missing_features = []
        for feature in responsive_features:
            if feature not in content:
                missing_features.append(feature)
        
        if missing_features:
            print(f"❌ Missing responsive features: {', '.join(missing_features)}")
            return False
        else:
            print("✅ Responsive design features present")
            return True
            
    except Exception as e:
        print(f"❌ Error testing responsive design: {e}")
        return False

def main():
    """Run all modern enhancement tests"""
    print("🧪 Running Modern Enhancement Tests")
    print("=" * 50)
    
    tests = [
        test_modern_css,
        test_modern_javascript,
        test_detailed_pistol_drawings,
        test_modern_animations,
        test_modern_ui_elements,
        test_responsive_design
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
        print("🎉 All modern enhancement tests passed!")
        print()
        print("🚀 Modern Features Summary:")
        print("   ✅ Modern animations and transitions")
        print("   ✅ Detailed pistol drawings for products")
        print("   ✅ Enhanced visual effects and interactivity")
        print("   ✅ Modern UI elements and animations")
        print("   ✅ Responsive design improvements")
        print()
        print("💻 Launch your modern website with:")
        print("   python3 launch_website.py")
        return True
    else:
        print("❌ Some modern enhancement tests failed.")
        return False

if __name__ == '__main__':
    # Change to website directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    success = main()
    sys.exit(0 if success else 1)