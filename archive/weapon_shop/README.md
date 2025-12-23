# Elite Armory - Weapon Trading Website

A full-featured website for weapons trading with a retro computer-style loading animation.

## Features

- **Retro Loading Animation**: Old computer-style green text loading sequence
- **ASCII Art Display**: Elite Armory logo in ASCII art
- **Pistol Drawing Animation**: Green line drawing of a pistol
- **Product Catalog**: 12 different weapons with descriptions and prices
- **Responsive Design**: Works on desktop and mobile devices
- **Modern UI**: Dark theme with green accents

## Installation

1. Clone this repository or download the files
2. Navigate to the project directory:
   ```bash
   cd weapon_shop
   ```
3. Install Python 3 if you don't have it already

## Running the Website

### Option 1: Using Python Server (Recommended)

```bash
python3 server.py
```

This will start a local server on `http://localhost:8000` and automatically open your browser.

### Option 2: Using Any Web Server

You can use any web server to serve the files. Just point it to the `weapon_shop` directory and open `index.html`.

## Project Structure

```
weapon_shop/
├── css/
│   ├── loading.css      # Loading animation styles
│   └── style.css         # Main website styles
├── images/
│   └── placeholder.jpg  # Fallback image
├── js/
│   ├── loading.js       # Loading animation logic
│   └── main.js           # Main website functionality
├── server.py            # Python web server
├── index.html           # Main HTML file
└── README.md            # This file
```

## Customization

### Adding More Products

Edit the `products` array in `js/main.js` to add more weapons. Each product should have:
- `id`: Unique identifier
- `name`: Product name
- `description`: Product description
- `price`: Price string
- `image`: Path to image file
- `category`: Product category

### Changing the Loading Sequence

Edit the `sequences` array in `js/loading.js` to change the loading text and timing.

### Styling

Modify the CSS files in the `css/` directory to change colors, layouts, and other visual elements.

## Legal Disclaimer

This is a demonstration website only. All weapon sales are subject to local, state, and federal laws. Proper licensing and background checks are required for any real weapon purchases.

## License

This project is for educational and demonstration purposes only.