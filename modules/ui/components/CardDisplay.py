import streamlit as st
from PIL import Image
import io
import base64

class CardDisplay:
    @staticmethod
    def display_grid(cards, on_click=None, on_card_click=None):
        """Display a grid of cards with 5 per row and stylized edit buttons"""
        if cards is None or (hasattr(cards, 'empty') and cards.empty) or len(cards) == 0:
            st.info("No cards to display")
            return

        # Determine click handler
        click_handler = on_card_click if on_card_click else on_click

        # Convert DataFrame to list of dicts if needed
        if hasattr(cards, 'to_dict'):
            cards = cards.to_dict('records')

        # --- Custom CSS ---
        st.markdown("""
        <style>
            .card-container {
                position: relative;
                width: 100%;
                height: 200px;
                border-radius: 6px;
                overflow: hidden;
                transition: transform 0.2s ease-in-out;
                box-shadow: 0 1px 3px rgba(0,0,0,0.15);
                margin-bottom: 0.5rem;
                background: #f9f9f9;
                display: flex;
                align-items: center;
                justify-content: center;
            }

            .card-container:hover {
                transform: scale(1.02);
            }

            .card-image {
                max-width: 100%;
                max-height: 100%;
                object-fit: contain;
                padding: 5px;
            }

            .card-overlay {
                position: absolute;
                bottom: 0;
                width: 100%;
                background: rgba(0,0,0,0.75);
                color: #fff;
                font-size: 0.7rem;
                padding: 0.25rem;
                text-align: center;
                opacity: 0;
                transition: opacity 0.3s ease-in-out;
            }

            .card-container:hover .card-overlay {
                opacity: 1;
            }

            .edit-button {
                background-color: #0056d2;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 0.3rem 0.6rem;
                font-size: 0.75rem;
                cursor: pointer;
                width: 100%;
                margin-top: 0.25rem;
            }

            .edit-button:hover {
                background-color: #0041a8;
            }
        </style>
        """, unsafe_allow_html=True)

        # --- Layout ---
        cards_per_row = 5
        for i in range(0, len(cards), cards_per_row):
            row_cards = cards[i:i + cards_per_row]
            cols = st.columns(cards_per_row)
            for j, card in enumerate(row_cards):
                with cols[j]:
                    # Handle both dictionary and Card object inputs
                    if hasattr(card, 'photo'):
                        photo = card.photo or 'https://placehold.co/160x220?text=No+Image'
                        player = card.player_name
                        year = card.year
                        card_set = card.card_set
                        value = card.current_value
                    else:
                        photo = card.get('photo', '') or 'https://placehold.co/160x220?text=No+Image'
                        player = card.get('player_name', '')
                        year = card.get('year', '')
                        card_set = card.get('card_set', '')
                        value = card.get('current_value', 0)

                    # Card visual
                    st.markdown(f"""
                    <div class="card-container">
                        <img src="{photo}" class="card-image" onerror="this.src='https://placehold.co/160x220?text=No+Image';"/>
                        <div class="card-overlay">
                            <strong>{player}</strong><br/>
                            {year} {card_set}<br/>
                            ${value:,.2f}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    # Stylized Edit button
                    if click_handler:
                        button_id = f"edit_{i+j}"
                        clicked = st.button("Edit", key=button_id)
                        if clicked:
                            click_handler(i+j)

    @staticmethod
    def display_profit_calculator(card_data, market_data):
        """Display profit calculator for a card"""
        st.markdown("### Profit Calculator")
        
        # Get current market value
        current_value = market_data['metrics']['avg_price']
        
        # Get purchase price from user
        purchase_price = st.number_input(
            "Enter your purchase price ($)",
            min_value=0.0,
            value=0.0,
            step=0.01,
            format="%.2f"
        )
        
        # Calculate profit/loss
        profit_loss = current_value - purchase_price
        roi = (profit_loss / purchase_price * 100) if purchase_price > 0 else 0
        
        # Display results
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(
                "Current Market Value",
                f"${current_value:.2f}",
                help="Based on recent sales data"
            )
        with col2:
            st.metric(
                "Profit/Loss",
                f"${profit_loss:.2f}",
                f"{roi:.1f}% ROI",
                delta_color="inverse" if profit_loss < 0 else "normal"
            )
        with col3:
            st.metric(
                "Return on Investment",
                f"{roi:.1f}%",
                help="Percentage return on your investment"
            )
        
        # Get card condition
        condition = None
        if isinstance(card_data, dict):
            condition = card_data.get('condition', '').lower()
        elif isinstance(card_data, list) and len(card_data) > 0:
            condition = card_data[0].get('condition', '').lower()
        
        # If card is raw, show grading analysis
        if condition == 'raw':
            st.markdown("### Grading Analysis")
            
            # Default multipliers for PSA grades
            psa9_multiplier = 1.5  # PSA 9 typically 1.5x raw value
            psa10_multiplier = 3.0  # PSA 10 typically 3x raw value
            
            # Calculate PSA 9 and PSA 10 prices using multipliers
            psa9_price = current_value * psa9_multiplier
            psa10_price = current_value * psa10_multiplier
            
            # Try to get actual PSA sales data if available
            if 'sales' in market_data and isinstance(market_data['sales'], list):
                psa9_sales = [sale for sale in market_data['sales'] if 'psa 9' in sale.get('title', '').lower()]
                psa10_sales = [sale for sale in market_data['sales'] if 'psa 10' in sale.get('title', '').lower()]
                
                if psa9_sales:
                    psa9_price = psa9_sales[0]['price']
                if psa10_sales:
                    psa10_price = psa10_sales[0]['price']
            
            # Calculate grading costs
            grading_fee = 25.0
            shipping_cost = 10.0
            total_grading_cost = grading_fee + shipping_cost
            
            # Calculate break-even prices and profits
            break_even = purchase_price + total_grading_cost
            psa9_profit = psa9_price - break_even
            psa10_profit = psa10_price - break_even
            
            # Calculate ROI for each grade
            psa9_roi = (psa9_profit / break_even * 100) if break_even > 0 else 0
            psa10_roi = (psa10_profit / break_even * 100) if break_even > 0 else 0
            
            # Display grading metrics
            st.markdown("#### Potential Graded Values")
            col1, col2 = st.columns(2)
            with col1:
                st.metric(
                    "PSA 9 Value",
                    f"${psa9_price:.2f}",
                    f"{psa9_roi:+.1f}% vs Avg",
                    help="Estimated value if graded PSA 9"
                )
            with col2:
                st.metric(
                    "PSA 10 Value",
                    f"${psa10_price:.2f}",
                    f"{psa10_roi:+.1f}% vs Avg",
                    help="Estimated value if graded PSA 10"
                )
            
            # Display break-even analysis
            st.markdown("#### Break-Even Analysis")
            st.markdown(f"""
            - **Total Grading Cost:** ${total_grading_cost:.2f} (Grading: ${grading_fee:.2f} + Shipping: ${shipping_cost:.2f})
            - **Break-Even Price:** ${break_even:.2f}
            """)
            
            # Quick verdict
            st.markdown("#### Grading Recommendation")
            if psa10_profit > total_grading_cost * 2:
                st.success("🟢 **GRADE IT!** - High profit potential at PSA 10")
            elif psa9_profit > total_grading_cost:
                st.info("🔵 **Consider Grading** - Profitable at PSA 9")
            else:
                st.warning("🟡 **DON'T GRADE** - Grading costs exceed potential profit")

def render_card_display(card):
    """
    Renders a detailed view of a single card.
    
    Args:
        card (dict or Card): The card data to display
    """
    if not card:
        st.warning("No card data available")
        return

    # Create two columns for the layout
    col1, col2 = st.columns([1, 2])

    with col1:
        # Display card image
        if hasattr(card, 'photo'):
            photo = card.photo
        else:
            photo = card.get('photo', '')
        if photo:
            st.image(photo, use_column_width=True)
        else:
            st.image('https://placehold.co/300x400?text=No+Image', use_column_width=True)

    with col2:
        # Display card details
        if hasattr(card, 'player_name'):
            st.subheader(card.player_name)
        else:
            st.subheader(card.get('player_name', 'Unknown Player'))
        
        # Basic info
        if hasattr(card, 'year'):
            st.write(f"**Year:** {card.year}")
            st.write(f"**Set:** {card.card_set}")
            st.write(f"**Card Number:** {card.card_number}")
            st.write(f"**Condition:** {card.condition}")
            st.write(f"**Current Value:** ${card.current_value:,.2f}")
            if card.notes:
                st.write("**Notes:**")
                st.write(card.notes)
            if card.tags:
                st.write("**Tags:**")
                tag_cols = st.columns(4)
                for i, tag in enumerate(card.tags):
                    with tag_cols[i % 4]:
                        st.markdown(f"`{tag}`")
        else:
            st.write(f"**Year:** {card.get('year', 'N/A')}")
            st.write(f"**Set:** {card.get('card_set', 'N/A')}")
            st.write(f"**Card Number:** {card.get('card_number', 'N/A')}")
            st.write(f"**Condition:** {card.get('condition', 'N/A')}")
            st.write(f"**Current Value:** ${card.get('current_value', 0):,.2f}")
            if card.get('notes'):
                st.write("**Notes:**")
                st.write(card.get('notes'))
            tags = card.get('tags', [])
            if tags:
                st.write("**Tags:**")
                tag_cols = st.columns(4)
                for i, tag in enumerate(tags):
                    with tag_cols[i % 4]:
                        st.markdown(f"`{tag}`") 