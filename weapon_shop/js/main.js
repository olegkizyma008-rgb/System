// Main Website Functionality
class WeaponShop {
    constructor() {
        this.productGrid = document.getElementById('product-grid');
        this.products = [];
        this.init();
    }
    
    async init() {
        await this.loadProducts();
        this.renderProducts();
        this.setupEventListeners();
    }
    
    async loadProducts() {
        // In a real application, this would fetch from an API
        // For now, we'll use local data
        this.products = [
            {
                id: 1,
                name: 'Glock 19 Gen 5',
                description: '9mm semi-automatic pistol with 15-round capacity. Compact and reliable for personal defense.',
                price: '$599.99',
                image: 'images/glock19.jpg',
                category: 'Handguns'
            },
            {
                id: 2,
                name: 'Sig Sauer P320',
                description: 'Modular 9mm pistol with interchangeable grip modules. Used by US military as M17.',
                price: '$649.99',
                image: 'images/p320.jpg',
                category: 'Handguns'
            },
            {
                id: 3,
                name: 'AR-15 Tactical',
                description: 'Semi-automatic rifle with 16" barrel, 30-round magazine, and adjustable stock.',
                price: '$1,299.99',
                image: 'images/ar15.jpg',
                category: 'Rifles'
            },
            {
                id: 4,
                name: 'Remington 870',
                description: '12-gauge pump-action shotgun with 18.5" barrel. Ideal for home defense.',
                price: '$499.99',
                image: 'images/remington870.jpg',
                category: 'Shotguns'
            },
            {
                id: 5,
                name: 'Springfield M1A',
                description: '.308 caliber semi-automatic rifle based on the M14 platform. Excellent for long-range shooting.',
                price: '$1,899.99',
                image: 'images/m1a.jpg',
                category: 'Rifles'
            },
            {
                id: 6,
                name: 'Smith & Wesson M&P Shield',
                description: 'Compact 9mm pistol for concealed carry. Lightweight and easy to conceal.',
                price: '$449.99',
                image: 'images/mpshield.jpg',
                category: 'Handguns'
            },
            {
                id: 7,
                name: 'Ruger 10/22',
                description: '.22 LR semi-automatic rifle. Perfect for training and small game hunting.',
                price: '$299.99',
                image: 'images/ruger1022.jpg',
                category: 'Rifles'
            },
            {
                id: 8,
                name: 'Mossberg 500',
                description: '12-gauge pump-action shotgun with 28" barrel. Versatile for hunting and sport.',
                price: '$429.99',
                image: 'images/mossberg500.jpg',
                category: 'Shotguns'
            },
            {
                id: 9,
                name: 'FN SCAR 17S',
                description: '7.62x51mm semi-automatic rifle. Military-grade performance for civilian use.',
                price: '$3,499.99',
                image: 'images/scar17s.jpg',
                category: 'Rifles'
            },
            {
                id: 10,
                name: 'Beretta 92FS',
                description: '9mm semi-automatic pistol with 15-round capacity. Classic Italian design.',
                price: '$699.99',
                image: 'images/beretta92fs.jpg',
                category: 'Handguns'
            },
            {
                id: 11,
                name: 'Heckler & Koch USP',
                description: '.45 ACP pistol with 12-round capacity. Renowned for reliability and accuracy.',
                price: '$999.99',
                image: 'images/usp.jpg',
                category: 'Handguns'
            },
            {
                id: 12,
                name: 'AK-47 Classic',
                description: '7.62x39mm semi-automatic rifle. Legendary reliability in all conditions.',
                price: '$899.99',
                image: 'images/ak47.jpg',
                category: 'Rifles'
            }
        ];
    }
    
    renderProducts() {
        this.productGrid.innerHTML = '';
        
        this.products.forEach((product, index) => {
            const productCard = document.createElement('div');
            productCard.className = 'product-card';
            
            // Create weapon icon based on category
            const weaponIcon = this.createWeaponIcon(product.category);
            
            // Add detailed pistol drawing for handguns
            let pistolDrawing = '';
            if (product.category.toLowerCase() === 'handguns') {
                pistolDrawing = `
                    <div class="pistol-drawing-product" id="pistol-drawing-${index}">
                        <!-- Pistol will be drawn here -->
                    </div>
                `;
            }
            
            productCard.innerHTML = `
                <div class="product-image-container">
                    <img src="${product.image}" alt="${product.name}" class="product-image" onerror="this.style.display='none'; this.nextElementSibling.style.display='block'">
                    ${weaponIcon}
                    ${pistolDrawing}
                </div>
                <div class="product-info">
                    <h3>${product.name}</h3>
                    <p>${product.description}</p>
                    <div class="product-price">${product.price}</div>
                    <button class="btn" onclick="alert('Added ${product.name} to cart!')">Add to Cart</button>
                </div>
            `;
            
            this.productGrid.appendChild(productCard);
            
            // Draw detailed pistol for handguns
            if (product.category.toLowerCase() === 'handguns') {
                this.drawPistolForProduct(index);
            }
        });
        
        // Add hover effects
        this.addHoverEffects();
        
        // Add modern animations
        this.addModernAnimations();
    }
    
    drawPistolForProduct(index) {
        const pistolContainer = document.getElementById(`pistol-drawing-${index}`);
        if (!pistolContainer) return;
        
        const pistolLines = this.createDetailedPistolDrawing();
        
        pistolLines.forEach((line, lineIndex) => {
            setTimeout(() => {
                const lineElement = document.createElement('div');
                lineElement.className = 'pistol-line-product';
                
                // Calculate angle and length
                const length = Math.sqrt(Math.pow(line.x2 - line.x1, 2) + Math.pow(line.y2 - line.y1, 2));
                const angle = Math.atan2(line.y2 - line.y1, line.x2 - line.x1) * 180 / Math.PI;
                
                lineElement.style.width = length + 'px';
                lineElement.style.left = line.x1 + 'px';
                lineElement.style.top = line.y1 + 'px';
                lineElement.style.transform = `rotate(${angle}deg)`;
                lineElement.style.transformOrigin = '0 0';
                
                pistolContainer.appendChild(lineElement);
            }, lineIndex * 50); // Staggered animation
        });
        
        // Show the pistol drawing
        setTimeout(() => {
            pistolContainer.classList.add('show');
        }, pistolLines.length * 50);
    }
    
    addModernAnimations() {
        // Animate product cards on scroll
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.style.opacity = '1';
                }
            });
        }, { threshold: 0.1 });
        
        document.querySelectorAll('.product-card').forEach(card => {
            observer.observe(card);
        });
        
        // Add pulse animation to buttons
        document.querySelectorAll('.btn').forEach(btn => {
            btn.addEventListener('mouseenter', function() {
                this.style.animation = 'pulse 0.5s ease';
            });
            
            btn.addEventListener('animationend', function() {
                this.style.animation = 'none';
            });
        });
    }
    
    createWeaponIcon(category) {
        let iconHTML = '';
        
        switch(category.toLowerCase()) {
            case 'handguns':
                iconHTML = `
                    <div class="weapon-icon handgun-icon" style="display: none;">
                        <div class="weapon-line" style="width: 60px; height: 2px; margin: 8px 0;"></div>
                        <div class="weapon-line" style="width: 20px; height: 2px; margin: 4px 0;"></div>
                        <div class="weapon-line" style="width: 40px; height: 2px; margin: 4px 0;"></div>
                    </div>
                `;
                break;
            case 'rifles':
                iconHTML = `
                    <div class="weapon-icon rifle-icon" style="display: none;">
                        <div class="weapon-line" style="width: 80px; height: 2px; margin: 8px 0;"></div>
                        <div class="weapon-line" style="width: 10px; height: 2px; margin: 4px 0;"></div>
                        <div class="weapon-line" style="width: 60px; height: 2px; margin: 4px 0;"></div>
                        <div class="weapon-line" style="width: 10px; height: 2px; margin: 4px 0;"></div>
                    </div>
                `;
                break;
            case 'shotguns':
                iconHTML = `
                    <div class="weapon-icon shotgun-icon" style="display: none;">
                        <div class="weapon-line" style="width: 70px; height: 2px; margin: 8px 0;"></div>
                        <div class="weapon-line" style="width: 15px; height: 2px; margin: 4px 0;"></div>
                        <div class="weapon-line" style="width: 50px; height: 2px; margin: 4px 0;"></div>
                        <div class="weapon-line" style="width: 15px; height: 2px; margin: 4px 0;"></div>
                    </div>
                `;
                break;
            default:
                iconHTML = `
                    <div class="weapon-icon default-icon" style="display: none;">
                        <div class="weapon-line" style="width: 50px; height: 2px; margin: 8px 0;"></div>
                        <div class="weapon-line" style="width: 20px; height: 2px; margin: 4px 0;"></div>
                        <div class="weapon-line" style="width: 30px; height: 2px; margin: 4px 0;"></div>
                    </div>
                `;
        }
        
        return iconHTML;
    }
    
    createDetailedPistolDrawing() {
        // Detailed pistol drawing lines
        const pistolLines = [
            // Grip
            { x1: 10, y1: 60, x2: 30, y2: 60 },
            { x1: 30, y1: 60, x2: 30, y2: 20 },
            { x1: 30, y1: 20, x2: 50, y2: 20 },
            
            // Slide
            { x1: 50, y1: 20, x2: 50, y2: 10 },
            { x1: 50, y1: 10, x2: 80, y2: 10 },
            { x1: 80, y1: 10, x2: 80, y2: 15 },
            { x1: 80, y1: 15, x2: 90, y2: 15 },
            { x1: 90, y1: 15, x2: 90, y2: 50 },
            { x1: 90, y1: 50, x2: 60, y2: 50 },
            
            // Trigger guard
            { x1: 60, y1: 50, x2: 60, y2: 65 },
            { x1: 60, y1: 65, x2: 30, y2: 65 },
            { x1: 30, y1: 65, x2: 30, y2: 60 },
            
            // Barrel details
            { x1: 82, y1: 12, x2: 85, y2: 12 },
            { x1: 85, y1: 12, x2: 85, y2: 18 },
            
            // Slide details
            { x1: 55, y1: 12, x2: 60, y2: 12 },
            { x1: 60, y1: 12, x2: 60, y2: 18 },
            { x1: 60, y1: 18, x2: 65, y2: 18 }
        ];
        
        return pistolLines;
    }
    
    addHoverEffects() {
        const cards = document.querySelectorAll('.product-card');
        cards.forEach(card => {
            card.addEventListener('mouseenter', function() {
                this.style.transform = 'translateY(-5px)';
                this.style.boxShadow = '0 10px 20px rgba(0, 255, 0, 0.2)';
            });
            
            card.addEventListener('mouseleave', function() {
                this.style.transform = 'translateY(0)';
                this.style.boxShadow = '0 5px 10px rgba(0, 255, 0, 0.1)';
            });
        });
    }
    
    setupEventListeners() {
        // Smooth scrolling for navigation links
        document.querySelectorAll('nav a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function (e) {
                e.preventDefault();
                const targetId = this.getAttribute('href');
                const targetElement = document.querySelector(targetId);
                
                if (targetElement) {
                    targetElement.scrollIntoView({
                        behavior: 'smooth'
                    });
                }
            });
        });
        
        // Modern scroll effects
        this.setupScrollEffects();
    }
    
    setupScrollEffects() {
        // Navigation scroll effect
        const nav = document.querySelector('nav');
        if (nav) {
            window.addEventListener('scroll', () => {
                if (window.scrollY > 50) {
                    nav.classList.add('scrolled');
                } else {
                    nav.classList.remove('scrolled');
                }
            });
        }
        
        // Parallax effect for header
        const header = document.querySelector('header');
        if (header) {
            window.addEventListener('scroll', () => {
                const scrollPosition = window.scrollY;
                header.style.transform = `translateY(${scrollPosition * 0.5}px)`;
                header.style.opacity = 1 - (scrollPosition * 0.001);
            });
        }
        
        // Add modern tooltips
        document.querySelectorAll('.btn').forEach(btn => {
            btn.addEventListener('mouseenter', function() {
                const tooltip = document.createElement('div');
                tooltip.className = 'modern-tooltip';
                tooltip.textContent = 'Add to Cart';
                tooltip.style.position = 'absolute';
                tooltip.style.bottom = '100%';
                tooltip.style.left = '50%';
                tooltip.style.transform = 'translateX(-50%)';
                tooltip.style.background = 'var(--primary-color)';
                tooltip.style.color = '#000';
                tooltip.style.padding = '5px 10px';
                tooltip.style.borderRadius = '3px';
                tooltip.style.fontSize = '12px';
                tooltip.style.opacity = '0';
                tooltip.style.transition = 'opacity 0.3s';
                tooltip.style.zIndex = '1000';
                
                this.appendChild(tooltip);
                
                setTimeout(() => {
                    tooltip.style.opacity = '1';
                }, 10);
                
                this.addEventListener('mouseleave', function() {
                    tooltip.style.opacity = '0';
                    setTimeout(() => tooltip.remove(), 300);
                }, { once: true });
            });
        });
    }
}

// Initialize the weapon shop when the main content is displayed
document.addEventListener('DOMContentLoaded', () => {
    // Wait for the loading animation to finish before initializing the shop
    const checkMainContent = setInterval(() => {
        const mainContent = document.getElementById('main-content');
        if (mainContent && mainContent.style.display === 'block') {
            clearInterval(checkMainContent);
            new WeaponShop();
        }
    }, 100);
});