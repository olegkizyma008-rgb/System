// Retro Computer Loading Animation
class LoadingAnimation {
    constructor() {
        this.terminalText = document.getElementById('terminal-text');
        this.asciiArt = document.getElementById('ascii-art');
        this.pistolDrawing = document.getElementById('pistol-drawing');
        this.mainContent = document.getElementById('main-content');
        this.loadingScreen = document.getElementById('loading-screen');
        
        this.sequences = [
            { text: 'ELITE ARMORY OS v3.14', delay: 30 },
            { text: 'BOOTING SECURE SYSTEM...', delay: 20 },
            { text: 'INITIALIZING ENCRYPTION MODULES...', delay: 25 },
            { text: 'LOADING WEAPON DATABASE (12 ITEMS)...', delay: 30 },
            { text: 'VERIFYING ACCESS CREDENTIALS...', delay: 20 },
            { text: 'ESTABLISHING MILITARY-GRADE CONNECTION...', delay: 25 },
            { text: 'DECRYPTING INVENTORY RECORDS...', delay: 30 },
            { text: 'PREPARING TACTICAL INTERFACE...', delay: 20 },
            { text: 'LOADING HIGH-RESOLUTION ASSETS...', delay: 25 },
            { text: 'INITIALIZING 3D RENDERING ENGINE...', delay: 30 },
            { text: 'ALL SYSTEMS OPERATIONAL.', delay: 20 },
            { text: 'WELCOME TO ELITE ARMORY, COMMANDER.', delay: 10 }
        ];
        
        this.currentSequence = 0;
        this.asciiArtLines = [
            '   ███████╗██╗     ██╗   ██╗███╗   ███╗██████╗ ███████╗██████╗ ',
            '   ██╔════╝██║     ██║   ██║████╗ ████║██╔══██╗██╔════╝██╔══██╗',
            '   █████╗  ██║     ██║   ██║██╔████╔██║██████╔╝█████╗  ██████╔╝',
            '   ██╔══╝  ██║     ██║   ██║██║╚██╔╝██║██╔══██╗██╔══╝  ██╔══██╗',
            '   ██║     ███████╗╚██████╔╝██║ ╚═╝ ██║██║  ██║███████╗██║  ██║',
            '   ╚═╝     ╚══════╝ ╚═════╝ ╚═╝     ╚═╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝',
            ' ',
            '   ███████╗██╗   ██╗██╗███╗   ██╗ ██████╗███████╗██████╗ ██╗     ',
            '   ██╔════╝██║   ██║██║████╗  ██║██╔════╝██╔════╝██╔══██╗██║     ',
            '   █████╗  ██║   ██║██║██╔██╗ ██║██║     █████╗  ██████╔╝██║     ',
            '   ██╔══╝  ██║   ██║██║██║╚██╗██║██║     ██╔══╝  ██╔══██╗██║     ',
            '   ██║     ╚██████╔╝██║██║ ╚████║╚██████╗███████╗██║  ██║███████╗',
            '   ╚═╝      ╚═════╝ ╚═╝╚═╝  ╚═══╝ ╚═════╝╚══════╝╚═╝  ╚═╝╚══════╝'
        ];
        
        this.pistolLines = [
            // Pistol grip
            { x1: 50, y1: 160, x2: 80, y2: 160 },
            { x1: 80, y1: 160, x2: 80, y2: 120 },
            { x1: 80, y1: 120, x2: 120, y2: 120 },
            
            // Pistol slide
            { x1: 120, y1: 120, x2: 120, y2: 100 },
            { x1: 120, y1: 100, x2: 180, y2: 100 },
            { x1: 180, y1: 100, x2: 180, y2: 110 },
            { x1: 180, y1: 110, x2: 200, y2: 110 },
            { x1: 200, y1: 110, x2: 200, y2: 150 },
            { x1: 200, y1: 150, x2: 150, y2: 150 },
            
            // Trigger guard
            { x1: 150, y1: 150, x2: 150, y2: 170 },
            { x1: 150, y1: 170, x2: 100, y2: 170 },
            { x1: 100, y1: 170, x2: 100, y2: 160 },
            
            // Barrel details
            { x1: 180, y1: 105, x2: 190, y2: 105 },
            { x1: 190, y1: 105, x2: 190, y2: 115 },
            
            // Slide details
            { x1: 130, y1: 105, x2: 140, y2: 105 },
            { x1: 140, y1: 105, x2: 140, y2: 115 },
            { x1: 140, y1: 115, x2: 150, y2: 115 }
        ];
    }
    
    start() {
        this.typeText(this.sequences[this.currentSequence]);
    }
    
    typeText(sequence) {
        let i = 0;
        const text = sequence.text;
        const delay = sequence.delay;
        
        const typingInterval = setInterval(() => {
            if (i < text.length) {
                const span = document.createElement('span');
                span.textContent = text.charAt(i);
                span.style.animationDelay = `${i * 0.05}s`;
                this.terminalText.appendChild(span);
                i++;
            } else {
                clearInterval(typingInterval);
                
                setTimeout(() => {
                    this.terminalText.innerHTML += '<br><br>';
                    
                    this.currentSequence++;
                    
                    if (this.currentSequence < this.sequences.length) {
                        this.typeText(this.sequences[this.currentSequence]);
                    } else {
                        this.showAsciiArt();
                    }
                }, 500);
            }
        }, delay);
    }
    
    showAsciiArt() {
        this.asciiArtLines.forEach((line, index) => {
            setTimeout(() => {
                this.asciiArt.innerHTML += line + '<br>';
            }, index * 100);
        });
        
        setTimeout(() => {
            this.drawPistol();
        }, this.asciiArtLines.length * 100 + 1000);
    }
    
    drawPistol() {
        // Remove the "PISTOL RENDERING..." text
        const pistolDrawing = document.querySelector('.pistol-drawing::before');
        if (pistolDrawing) {
            pistolDrawing.style.opacity = '0';
        }
        
        this.pistolLines.forEach((line, index) => {
            setTimeout(() => {
                const lineElement = document.createElement('div');
                lineElement.className = 'pistol-line';
                
                // Calculate angle and length
                const length = Math.sqrt(Math.pow(line.x2 - line.x1, 2) + Math.pow(line.y2 - line.y1, 2));
                const angle = Math.atan2(line.y2 - line.y1, line.x2 - line.x1) * 180 / Math.PI;
                
                lineElement.style.width = '0';
                lineElement.style.left = line.x1 + 'px';
                lineElement.style.top = line.y1 + 'px';
                lineElement.style.transform = `rotate(${angle}deg)`;
                lineElement.style.transformOrigin = '0 0';
                lineElement.style.transition = 'width 0.5s ease, background-color 0.3s';
                
                this.pistolDrawing.appendChild(lineElement);
                
                // Animate the line drawing
                setTimeout(() => {
                    lineElement.style.width = length + 'px';
                    lineElement.style.backgroundColor = '#00ff00';
                }, 10);
                
            }, index * 150);
        });
        
        setTimeout(() => {
            this.finishLoading();
        }, this.pistolLines.length * 150 + 1000);
    }
    
    finishLoading() {
        this.loadingScreen.style.opacity = '0';
        this.loadingScreen.style.transition = 'opacity 1s';
        
        setTimeout(() => {
            this.loadingScreen.style.display = 'none';
            this.mainContent.style.display = 'block';
        }, 1000);
    }
}

// Start the loading animation when the page loads
document.addEventListener('DOMContentLoaded', () => {
    const loading = new LoadingAnimation();
    loading.start();
});