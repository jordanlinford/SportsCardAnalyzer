from typing import Dict, Any

class TrendIndicator:
    @staticmethod
    def get_trend_arrow(trend_direction: str) -> str:
        """Get trend arrow based on direction."""
        return "↑" if trend_direction == 'hot' else "↓" if trend_direction == 'cooling' else "→"

    @staticmethod
    def get_market_status(sentiment: float) -> Dict[str, str]:
        """Get market status based on sentiment score."""
        if sentiment >= 7.5:
            return {
                "status": "↑",
                "summary": "The market shows exceptional strength with positive trends across multiple indicators."
            }
        elif sentiment >= 6:
            return {
                "status": "↑",
                "summary": "The market demonstrates solid performance with good fundamentals."
            }
        elif sentiment >= 4.5:
            return {
                "status": "→",
                "summary": "The market appears stable with balanced supply and demand."
            }
        else:
            return {
                "status": "↓",
                "summary": "The market shows some uncertainty and may require careful consideration."
            }

class RecommendationIndicator:
    @staticmethod
    def get_grading_recommendation(psa10_profit: float, psa9_profit: float, total_grading_cost: float) -> Dict[str, Any]:
        """Get grading recommendation based on profit analysis."""
        if psa10_profit and psa10_profit > total_grading_cost * 2:
            return {
                "recommendation": "GRADE IT!",
                "color": "success",
                "icon": "!"
            }
        elif psa9_profit and psa9_profit > total_grading_cost:
            return {
                "recommendation": "Consider Grading",
                "color": "info",
                "icon": "?"
            }
        else:
            return {
                "recommendation": "DON'T GRADE",
                "color": "warning",
                "icon": "×"
            } 