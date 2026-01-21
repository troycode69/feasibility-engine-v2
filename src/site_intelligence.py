"""
AI-Powered Site Intelligence Module
Automatically scores site attributes using Street View + AI vision
No manual input required - fully data-driven
"""

import requests
import base64
from io import BytesIO
import os
import anthropic
from typing import Dict, Tuple, Optional


class SiteIntelligence:
    """
    Analyzes property sites using Google Street View + Claude Vision AI
    to automatically score visibility, access, and site quality
    """

    def __init__(self, google_api_key: str = None, anthropic_api_key: str = None):
        self.google_api_key = google_api_key or os.environ.get('GOOGLE_MAPS_API_KEY')
        self.anthropic_api_key = anthropic_api_key or os.environ.get('ANTHROPIC_API_KEY')

        if self.anthropic_api_key:
            self.claude = anthropic.Anthropic(api_key=self.anthropic_api_key)
        else:
            self.claude = None

    def get_street_view_image(self, address: str, heading: int = 0) -> Optional[bytes]:
        """
        Fetch Street View image for a given address

        Args:
            address: Property address
            heading: Camera direction (0=North, 90=East, 180=South, 270=West)

        Returns:
            Image bytes or None if unavailable
        """
        if not self.google_api_key:
            print("Warning: No Google API key available for Street View")
            return None

        base_url = "https://maps.googleapis.com/maps/api/streetview"

        params = {
            'size': '640x640',
            'location': address,
            'heading': heading,
            'pitch': 0,
            'fov': 90,
            'key': self.google_api_key
        }

        try:
            response = requests.get(base_url, params=params, timeout=10)

            if response.status_code == 200 and len(response.content) > 1000:
                return response.content
            else:
                print(f"Street View not available for {address}")
                return None

        except Exception as e:
            print(f"Error fetching Street View: {e}")
            return None

    def get_multiple_views(self, address: str) -> Dict[str, bytes]:
        """
        Get Street View images from multiple angles

        Returns:
            Dict mapping direction to image bytes
        """
        views = {}
        directions = {
            'north': 0,
            'east': 90,
            'south': 180,
            'west': 270
        }

        for direction, heading in directions.items():
            img = self.get_street_view_image(address, heading)
            if img:
                views[direction] = img

        return views

    def analyze_site_with_ai(self, address: str) -> Dict[str, any]:
        """
        Use Claude Vision to analyze Street View images and score site attributes

        Returns:
            Dict with visibility, access, site_size, and quality scores
        """

        if not self.claude:
            print("Warning: No Anthropic API key - using default scores")
            return self._get_default_scores()

        # Get Street View images
        views = self.get_multiple_views(address)

        if not views:
            print(f"No Street View imagery available for {address}")
            return self._get_default_scores()

        # Use the best available view (prefer north or east)
        image_bytes = views.get('north') or views.get('east') or list(views.values())[0]

        # Encode image to base64
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')

        # Prompt for Claude Vision
        prompt = """You are a commercial real estate site analyst specializing in self-storage facilities.
Analyze this Street View image of a potential self-storage development site and score the following:

1. **VISIBILITY** (Excellent/Good/Fair/Poor):
   - Excellent: Highly visible corner lot, major intersection, traffic signal, clear sight lines
   - Good: Visible from arterial road, moderate traffic, decent exposure
   - Fair: Visible but set back, secondary road, limited exposure
   - Poor: Hidden, low traffic, poor sight lines

2. **ACCESS** (Excellent/Good/Fair/Poor):
   - Excellent: Multiple entry points, signalized intersection, easy turn movements
   - Good: Clear ingress/egress, right-turn access from arterial
   - Fair: Single access point, right-in/right-out only
   - Poor: Difficult access, no median breaks, awkward turning movements

3. **SITE QUALITY** (High/Medium/Low):
   - High: Level lot, cleared or lightly developed, good frontage, no visible constraints
   - Medium: Some topography, older structures, moderate constraints
   - Low: Steep slopes, wetlands, heavy vegetation, significant development challenges

Respond ONLY in this exact JSON format:
{
    "visibility": "Excellent/Good/Fair/Poor",
    "access": "Excellent/Good/Fair/Poor",
    "site_quality": "High/Medium/Low",
    "reasoning": "Brief 2-3 sentence explanation of your assessment"
}"""

        try:
            message = self.claude.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=500,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/jpeg",
                                    "data": image_base64
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ]
            )

            # Parse response
            import json
            response_text = message.content[0].text

            # Extract JSON from response (handle cases where Claude adds explanation)
            if '{' in response_text:
                json_start = response_text.index('{')
                json_end = response_text.rindex('}') + 1
                json_str = response_text[json_start:json_end]
                result = json.loads(json_str)
            else:
                print("Could not parse AI response, using defaults")
                return self._get_default_scores()

            # Add address to result
            result['address'] = address
            result['has_street_view'] = True

            return result

        except Exception as e:
            print(f"Error analyzing site with AI: {e}")
            return self._get_default_scores()

    def _get_default_scores(self) -> Dict[str, str]:
        """Return default/conservative scores when AI analysis unavailable"""
        return {
            'visibility': 'Good',
            'access': 'Good',
            'site_quality': 'Medium',
            'reasoning': 'Unable to perform AI analysis - using conservative default scores',
            'has_street_view': False
        }

    def get_site_size_assessment(self, parcel_sqft: int, proposed_nra: int) -> str:
        """
        Assess site size adequacy based on parcel size and proposed NRA

        Args:
            parcel_sqft: Total parcel square footage
            proposed_nra: Proposed net rentable area

        Returns:
            'Ideal', 'Adequate', 'Marginal', or 'Insufficient'
        """

        if parcel_sqft <= 0 or proposed_nra <= 0:
            return 'Adequate'  # Default if unknown

        # Rule of thumb: Need ~2.5-3x NRA for parking, landscaping, setbacks
        # Climate control building: 3:1 ratio ideal
        # Drive-up: 4:1 ratio ideal

        ratio = parcel_sqft / proposed_nra

        if ratio >= 4.0:
            return 'Ideal'  # Plenty of room for expansion
        elif ratio >= 3.0:
            return 'Adequate'  # Fits well
        elif ratio >= 2.5:
            return 'Marginal'  # Tight but workable
        else:
            return 'Insufficient'  # Too small

    def analyze_complete_site(self, address: str, parcel_sqft: int = None,
                             proposed_nra: int = None) -> Dict[str, any]:
        """
        Complete site analysis combining AI vision + size assessment

        Returns:
            Dict with all site scoring attributes
        """

        # AI-powered analysis
        ai_scores = self.analyze_site_with_ai(address)

        # Size assessment
        if parcel_sqft and proposed_nra:
            size_score = self.get_site_size_assessment(parcel_sqft, proposed_nra)
        else:
            size_score = 'Adequate'  # Default

        return {
            'visibility': ai_scores['visibility'],
            'access': ai_scores['access'],
            'site_quality': ai_scores.get('site_quality', 'Medium'),
            'site_size': size_score,
            'reasoning': ai_scores.get('reasoning', ''),
            'has_street_view': ai_scores.get('has_street_view', False)
        }


# Helper function for easy integration
def score_site_automatically(address: str, parcel_sqft: int = None,
                            proposed_nra: int = None) -> Dict[str, str]:
    """
    Convenience function to score a site automatically

    Usage:
        scores = score_site_automatically("123 Main St, Dallas, TX", 100000, 60000)
        print(scores['visibility'])  # "Excellent"
        print(scores['access'])      # "Good"
    """

    analyzer = SiteIntelligence()
    return analyzer.analyze_complete_site(address, parcel_sqft, proposed_nra)
