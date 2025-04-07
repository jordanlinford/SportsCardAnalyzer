import os

def generate_market_analyzer_icon():
    return '''<svg width="64" height="64" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="8" y="8" width="48" height="36" rx="4" stroke="currentColor" stroke-width="2"/>
        <path d="M16 36L24 28L32 32L40 20L48 24" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        <line x1="8" y1="48" x2="56" y2="48" stroke="currentColor" stroke-width="2"/>
    </svg>'''

def generate_price_predictor_icon():
    return '''<svg width="64" height="64" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="32" cy="32" r="24" stroke="currentColor" stroke-width="2"/>
        <path d="M32 16V20M32 44V48M16 32H20M44 32H48" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        <text x="32" y="36" text-anchor="middle" font-size="16" fill="currentColor">$</text>
    </svg>'''

def generate_calculator_icon():
    return '''<svg width="64" height="64" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="16" y="8" width="32" height="48" rx="4" stroke="currentColor" stroke-width="2"/>
        <rect x="20" y="12" width="24" height="12" rx="2" stroke="currentColor" stroke-width="2"/>
        <circle cx="24" cy="32" r="2" fill="currentColor"/>
        <circle cx="32" cy="32" r="2" fill="currentColor"/>
        <circle cx="40" cy="32" r="2" fill="currentColor"/>
        <circle cx="24" cy="40" r="2" fill="currentColor"/>
        <circle cx="32" cy="40" r="2" fill="currentColor"/>
        <circle cx="40" cy="40" r="2" fill="currentColor"/>
        <circle cx="24" cy="48" r="2" fill="currentColor"/>
        <circle cx="32" cy="48" r="2" fill="currentColor"/>
        <circle cx="40" cy="48" r="2" fill="currentColor"/>
    </svg>'''

def generate_recommendations_icon():
    return '''<svg width="64" height="64" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M8 32C8 16 16 8 32 8C48 8 56 16 56 32V40C56 48 48 56 32 56C16 56 8 48 8 40V32Z" stroke="currentColor" stroke-width="2"/>
        <path d="M32 20L35.8779 28.0164H44.5106L37.3164 32.9672L41.1943 40.9836L32 36.0328L22.8057 40.9836L26.6836 32.9672L19.4894 28.0164H28.1221L32 20Z" fill="currentColor"/>
    </svg>'''

def generate_trade_analyzer_icon():
    return '''<svg width="64" height="64" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M16 24L8 32L16 40" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M48 40L56 32L48 24" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M8 32H56" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
    </svg>'''

def generate_collection_manager_icon():
    return '''<svg width="64" height="64" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M16 16L32 8L48 16L32 24L16 16Z" stroke="currentColor" stroke-width="2"/>
        <path d="M16 16V48L32 56M48 16V48L32 56" stroke="currentColor" stroke-width="2"/>
        <path d="M24 20L32 24L40 20" stroke="currentColor" stroke-width="2"/>
    </svg>'''

def generate_display_case_icon():
    return '''<svg width="64" height="64" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="8" y="16" width="48" height="32" rx="4" stroke="currentColor" stroke-width="2"/>
        <path d="M16 16V48M48 16V48" stroke="currentColor" stroke-width="2"/>
        <rect x="24" y="24" width="16" height="24" rx="2" stroke="currentColor" stroke-width="2"/>
        <path d="M8 52H56" stroke="currentColor" stroke-width="2"/>
    </svg>'''

def generate_profile_icon():
    return '''<svg width="64" height="64" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="32" cy="24" r="12" stroke="currentColor" stroke-width="2"/>
        <path d="M12 52C12 44 20 36 32 36C44 36 52 44 52 52" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
    </svg>'''

def main():
    # Create icons directory if it doesn't exist
    icons_dir = os.path.join('static', 'icons')
    os.makedirs(icons_dir, exist_ok=True)

    # Generate all icons
    icons = {
        'market_analyzer': generate_market_analyzer_icon(),
        'price_predictor': generate_price_predictor_icon(),
        'calculator': generate_calculator_icon(),
        'recommendations': generate_recommendations_icon(),
        'trade_analyzer': generate_trade_analyzer_icon(),
        'collection_manager': generate_collection_manager_icon(),
        'display_case': generate_display_case_icon(),
        'profile': generate_profile_icon()
    }

    # Save each icon
    for name, svg in icons.items():
        with open(os.path.join(icons_dir, f'{name}.svg'), 'w') as f:
            f.write(svg)

if __name__ == "__main__":
    main() 