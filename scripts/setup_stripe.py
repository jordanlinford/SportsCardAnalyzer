import stripe
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Stripe
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

def create_products_and_prices():
    """Create subscription products and prices in Stripe"""
    try:
        # Create Basic Plan Product
        basic_product = stripe.Product.create(
            name="Basic Plan",
            description="Enhanced sports card analysis with 50 cards, 5 display cases, and unlimited searches",
            metadata={
                "features": "unlimited_searches,50_cards,5_display_cases,basic_analysis,price_tracking,market_insights"
            }
        )
        
        # Create Basic Plan Price
        basic_price = stripe.Price.create(
            product=basic_product.id,
            unit_amount=999,  # $9.99
            currency="usd",
            recurring={
                "interval": "month"
            },
            metadata={
                "plan_type": "basic",
                "card_limit": "50",
                "display_case_limit": "5",
                "search_limit": "unlimited"
            }
        )
        
        # Create Premium Plan Product
        premium_product = stripe.Product.create(
            name="Premium Plan",
            description="Unlimited access to all features including unlimited cards, display cases, and advanced analytics",
            metadata={
                "features": "unlimited_searches,unlimited_cards,unlimited_display_cases,advanced_analytics,priority_support,bulk_analysis,custom_reports"
            }
        )
        
        # Create Premium Plan Price
        premium_price = stripe.Price.create(
            product=premium_product.id,
            unit_amount=1999,  # $19.99
            currency="usd",
            recurring={
                "interval": "month"
            },
            metadata={
                "plan_type": "premium",
                "card_limit": "unlimited",
                "display_case_limit": "unlimited",
                "search_limit": "unlimited"
            }
        )
        
        print("✅ Products and prices created successfully!")
        print("\nBasic Plan ($9.99/month):")
        print(f"Product ID: {basic_product.id}")
        print(f"Price ID: {basic_price.id}")
        print("Features:")
        print("- Unlimited searches")
        print("- Up to 50 cards in collection")
        print("- Up to 5 display cases")
        print("- Basic analysis and tracking")
        
        print("\nPremium Plan ($19.99/month):")
        print(f"Product ID: {premium_product.id}")
        print(f"Price ID: {premium_price.id}")
        print("Features:")
        print("- Unlimited searches")
        print("- Unlimited cards in collection")
        print("- Unlimited display cases")
        print("- Advanced analytics and features")
        
        # Update .env file with new price IDs
        with open('.env', 'r') as f:
            env_lines = f.readlines()
        
        with open('.env', 'w') as f:
            for line in env_lines:
                if line.startswith('STRIPE_BASIC_PLAN_PRICE_ID='):
                    f.write(f'STRIPE_BASIC_PLAN_PRICE_ID={basic_price.id}\n')
                elif line.startswith('STRIPE_PREMIUM_PLAN_PRICE_ID='):
                    f.write(f'STRIPE_PREMIUM_PLAN_PRICE_ID={premium_price.id}\n')
                else:
                    f.write(line)
        
        print("\n✅ .env file updated with new price IDs")
        
    except Exception as e:
        print(f"❌ Error creating products and prices: {str(e)}")

if __name__ == "__main__":
    create_products_and_prices() 