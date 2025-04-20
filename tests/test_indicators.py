import unittest
from modules.ui.indicators import TrendIndicator, RecommendationIndicator

class TestIndicators(unittest.TestCase):
    def test_trend_indicator(self):
        # Test trend arrows
        self.assertEqual(TrendIndicator.get_trend_arrow('hot'), "↑")
        self.assertEqual(TrendIndicator.get_trend_arrow('cooling'), "↓")
        self.assertEqual(TrendIndicator.get_trend_arrow('stable'), "→")
        
        # Test market status
        status = TrendIndicator.get_market_status(8.0)
        self.assertEqual(status['status'], "↑")
        self.assertIn("exceptional strength", status['summary'].lower())
        
        status = TrendIndicator.get_market_status(6.5)
        self.assertEqual(status['status'], "↑")
        self.assertIn("solid performance", status['summary'].lower())
        
        status = TrendIndicator.get_market_status(5.0)
        self.assertEqual(status['status'], "→")
        self.assertIn("stable", status['summary'].lower())
        
        status = TrendIndicator.get_market_status(3.0)
        self.assertEqual(status['status'], "↓")
        self.assertIn("uncertainty", status['summary'].lower())

    def test_recommendation_indicator(self):
        # Test grading recommendations
        rec = RecommendationIndicator.get_grading_recommendation(100, 50, 20)
        self.assertEqual(rec['recommendation'], "GRADE IT!")
        self.assertEqual(rec['color'], "success")
        self.assertEqual(rec['icon'], "!")
        
        rec = RecommendationIndicator.get_grading_recommendation(30, 25, 20)
        self.assertEqual(rec['recommendation'], "Consider Grading")
        self.assertEqual(rec['color'], "info")
        self.assertEqual(rec['icon'], "?")
        
        rec = RecommendationIndicator.get_grading_recommendation(15, 10, 20)
        self.assertEqual(rec['recommendation'], "DON'T GRADE")
        self.assertEqual(rec['color'], "warning")
        self.assertEqual(rec['icon'], "×")

if __name__ == '__main__':
    unittest.main() 