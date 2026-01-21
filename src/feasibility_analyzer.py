"""
Intelligent Feasibility Analyzer
Combines market scoring + financial projections to produce actionable recommendations
"""

from scoring_logic import FeasibilityScorer
from financials import FinancialModel, generate_pro_forma
import anthropic
import os


class FeasibilityAnalyzer:
    """
    Intelligent analyzer that combines market feasibility scores with financial projections
    to produce a clear PURSUE / CAUTION / PASS recommendation with AI-generated narrative.
    """

    def __init__(self):
        self.scorer = FeasibilityScorer()
        self.market_score = 0
        self.financial_metrics = {}
        self.recommendation = None

    def analyze_market(self, demographics, supply, site, competitor, economic):
        """
        Calculate market feasibility score from all inputs.

        Args:
            demographics: dict with {population, income, growth, renter_pct, age_pct}
            supply: dict with {sf_per_capita, occupancy, absorption_trend, pipeline}
            site: dict with {visibility, access, zoning, size}
            competitor: dict with {count, quality, pricing}
            economic: dict with {unemployment, business_growth, stability}

        Returns:
            dict with market score breakdown
        """

        # Calculate each category
        demo_score = self.scorer.calculate_demographics_score(
            demographics['population'],
            demographics['income'],
            demographics['growth'],
            demographics['renter_pct'],
            demographics['age_pct']
        )

        supply_score = self.scorer.calculate_supply_score(
            supply['sf_per_capita'],
            supply['occupancy'],
            supply['absorption_trend'],
            supply['pipeline']
        )

        site_score = self.scorer.calculate_site_score(
            site['visibility'],
            site['access'],
            site['zoning'],
            site['size']
        )

        competitor_score = self.scorer.calculate_competitor_score(
            competitor['count'],
            competitor['quality'],
            competitor['pricing']
        )

        economic_score = self.scorer.calculate_economic_score(
            economic['unemployment'],
            economic['business_growth'],
            economic['stability']
        )

        self.market_score = self.scorer.get_total_score()

        return {
            "total": self.market_score,
            "breakdown": self.scorer.get_score_breakdown(),
            "rubrics": {
                "demographics": self.scorer.get_demographics_rubric(
                    demographics['population'], demographics['income'],
                    demographics['growth'], demographics['renter_pct'], demographics['age_pct']
                ),
                "supply": self.scorer.get_supply_rubric(
                    supply['sf_per_capita'], supply['occupancy'],
                    supply['absorption_trend'], supply['pipeline']
                ),
                "site": self.scorer.get_site_rubric(
                    site['visibility'], site['access'], site['zoning'], site['size']
                ),
                "competitor": self.scorer.get_competitor_rubric(
                    competitor['count'], competitor['quality'], competitor['pricing']
                ),
                "economic": self.scorer.get_economic_rubric(
                    economic['unemployment'], economic['business_growth'], economic['stability']
                )
            }
        }

    def analyze_financials(self, land_cost, construction_cost_psf, rentable_sqft, avg_rent_psf,
                          stabilized_occ=90, cap_rate=7.5):
        """
        Run financial model and extract key metrics.

        Returns:
            dict with financial metrics
        """

        # Basic financial model
        model = FinancialModel(land_cost, construction_cost_psf, rentable_sqft, avg_rent_psf)
        returns = model.get_returns()

        # Pro forma projections
        total_cost = land_cost + (rentable_sqft * construction_cost_psf)
        pro_forma = generate_pro_forma(total_cost, rentable_sqft, avg_rent_psf,
                                      stabilized_occ, cap_rate)

        # Extract key metrics
        stabilized_noi = pro_forma['summary']['Stabilized NOI']
        exit_value = pro_forma['summary']['Exit Value']
        year_1_noi = pro_forma['summary']['Year 1 Total NOI']

        self.financial_metrics = {
            "total_cost": total_cost,
            "yield_on_cost": returns['Yield on Cost'],
            "stabilized_value": returns['Stabilized Value'],
            "equity_created": returns['Equity Created'],
            "stabilized_noi": stabilized_noi,
            "exit_value": exit_value,
            "year_1_noi": year_1_noi,
            "equity_multiple": (exit_value / (total_cost * 0.30)) if total_cost > 0 else 0
        }

        return self.financial_metrics

    def get_recommendation(self, address=None, market_data=None):
        """
        Generate final PURSUE / CAUTION / PASS recommendation based on
        market score + financial metrics.

        Returns:
            dict with {decision, confidence, key_reasons, narrative}
        """

        if self.market_score == 0 or not self.financial_metrics:
            return {
                "decision": "INCOMPLETE",
                "confidence": "N/A",
                "message": "Run both market and financial analysis first."
            }

        # Decision logic
        decision = "PASS"
        confidence = "Low"
        key_reasons = []

        # Market Score Thresholds (from scoring_logic.py)
        if self.market_score >= 80:
            decision = "PURSUE"
            confidence = "High"
            key_reasons.append(f"Strong market score ({self.market_score}/100)")
        elif self.market_score >= 65:
            decision = "CAUTION"
            confidence = "Moderate"
            key_reasons.append(f"Moderate market score ({self.market_score}/100)")
        else:
            decision = "PASS"
            confidence = "Low"
            key_reasons.append(f"Weak market score ({self.market_score}/100)")

        # Financial Overlay: Adjust recommendation based on returns
        yoc = self.financial_metrics.get('yield_on_cost', 0)
        equity_mult = self.financial_metrics.get('equity_multiple', 0)

        # Strong financials can upgrade CAUTION to PURSUE
        if decision == "CAUTION" and yoc >= 8.5 and equity_mult >= 2.0:
            decision = "PURSUE"
            confidence = "Moderate-High"
            key_reasons.append(f"Excellent returns override moderate market (YOC: {yoc}%, Equity Mult: {equity_mult:.1f}x)")

        # Weak financials can downgrade CAUTION to PASS
        elif decision == "CAUTION" and (yoc < 6.5 or equity_mult < 1.5):
            decision = "PASS"
            confidence = "Low"
            key_reasons.append(f"Insufficient returns for moderate market (YOC: {yoc}%, Equity Mult: {equity_mult:.1f}x)")

        # Add financial context to all decisions
        if yoc >= 8.5:
            key_reasons.append(f"Strong yield on cost ({yoc}%)")
        elif yoc < 6.5:
            key_reasons.append(f"Low yield on cost ({yoc}%)")

        if equity_mult >= 2.0:
            key_reasons.append(f"Excellent equity creation ({equity_mult:.1f}x multiple)")
        elif equity_mult < 1.5:
            key_reasons.append(f"Weak equity creation ({equity_mult:.1f}x multiple)")

        # Category-specific insights
        breakdown = self.scorer.get_score_breakdown()
        if breakdown['Demographics']['score'] < 15:
            key_reasons.append("Weak demographics (aging population, low income)")
        if breakdown['Supply Analysis']['score'] >= 20:
            key_reasons.append("Healthy supply/demand balance")
        elif breakdown['Supply Analysis']['score'] < 12:
            key_reasons.append("Oversupplied market or weak absorption")

        self.recommendation = {
            "decision": decision,
            "confidence": confidence,
            "key_reasons": key_reasons,
            "market_score": self.market_score,
            "financial_summary": {
                "yield_on_cost": f"{yoc:.1f}%",
                "equity_multiple": f"{equity_mult:.1f}x",
                "stabilized_value": f"${self.financial_metrics.get('stabilized_value', 0):,.0f}",
                "equity_created": f"${self.financial_metrics.get('equity_created', 0):,.0f}"
            }
        }

        # Generate AI narrative if Claude API key available
        if address and market_data:
            narrative = self._generate_ai_narrative(address, market_data)
            self.recommendation['narrative'] = narrative
        else:
            self.recommendation['narrative'] = self._generate_basic_narrative()

        return self.recommendation

    def _generate_basic_narrative(self):
        """Generate basic narrative without AI"""
        decision = self.recommendation['decision']

        if decision == "PURSUE":
            return f"""
**Recommendation: PURSUE this opportunity**

This project scores {self.market_score}/100 on market feasibility with a {self.recommendation['financial_summary']['yield_on_cost']}
yield on cost and {self.recommendation['financial_summary']['equity_multiple']} equity multiple.

Key Strengths:
{chr(10).join('• ' + r for r in self.recommendation['key_reasons'])}

Next Steps: Proceed with LOI and formal due diligence.
"""
        elif decision == "CAUTION":
            return f"""
**Recommendation: PROCEED WITH CAUTION**

This project scores {self.market_score}/100 on market feasibility with mixed financial indicators.

Key Considerations:
{chr(10).join('• ' + r for r in self.recommendation['key_reasons'])}

Next Steps: Require additional due diligence before committing capital.
"""
        else:
            return f"""
**Recommendation: PASS on this opportunity**

This project scores {self.market_score}/100 on market feasibility with insufficient returns.

Key Concerns:
{chr(10).join('• ' + r for r in self.recommendation['key_reasons'])}

Next Steps: Continue sourcing better opportunities.
"""

    def _generate_ai_narrative(self, address, market_data):
        """
        Use Claude API to generate intelligent narrative explaining the recommendation.

        Args:
            address: Property address
            market_data: Dict with demographics, competitors, etc.
        """

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            return self._generate_basic_narrative()

        try:
            client = anthropic.Anthropic(api_key=api_key)

            # Build context for Claude
            prompt = f"""You are a commercial real estate underwriting expert analyzing a self-storage acquisition opportunity.

PROPERTY: {address}

MARKET FEASIBILITY SCORE: {self.market_score}/100
DECISION: {self.recommendation['decision']}
CONFIDENCE: {self.recommendation['confidence']}

SCORE BREAKDOWN:
{self._format_score_breakdown()}

FINANCIAL METRICS:
- Yield on Cost: {self.recommendation['financial_summary']['yield_on_cost']}
- Equity Multiple: {self.recommendation['financial_summary']['equity_multiple']}
- Stabilized Value: {self.recommendation['financial_summary']['stabilized_value']}
- Equity Created: {self.recommendation['financial_summary']['equity_created']}

KEY FACTORS:
{chr(10).join('- ' + r for r in self.recommendation['key_reasons'])}

Write a 3-4 paragraph executive recommendation memo explaining:
1. Your decision ({self.recommendation['decision']}) and why
2. The most critical factors driving this recommendation
3. Specific risks or opportunities to monitor
4. Concrete next steps

Be direct, analytical, and actionable. Use specific numbers from the data."""

            message = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )

            return message.content[0].text

        except Exception as e:
            # Fallback to basic narrative if AI fails
            return self._generate_basic_narrative()

    def _format_score_breakdown(self):
        """Format score breakdown for AI prompt"""
        breakdown = self.scorer.get_score_breakdown()
        lines = []
        for category, scores in breakdown.items():
            if category != "Total":
                lines.append(f"- {category}: {scores['score']}/{scores['max']}")
        return "\n".join(lines)
