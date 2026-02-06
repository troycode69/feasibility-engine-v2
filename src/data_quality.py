"""
Data Quality Scoring and Assessment Module

Provides comprehensive data quality evaluation:
- Score completeness by category (0-100)
- Flag critical missing data
- Analysis confidence level (High/Medium/Low)
- Data freshness tracking
- Missing data handling with industry benchmarks

This module helps users understand the reliability of the feasibility analysis
and what data gaps exist that should be filled.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum


# ============================================================================
# ENUMS AND DATA CLASSES
# ============================================================================

class ConfidenceLevel(Enum):
    """Analysis confidence levels."""
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    INSUFFICIENT = "Insufficient Data"


class DataCategory(Enum):
    """Data categories for quality assessment."""
    DEMOGRAPHICS = "Demographics"
    SUPPLY_DEMAND = "Supply/Demand"
    COMPETITORS = "Competitors"
    SITE = "Site Characteristics"
    ECONOMIC = "Economic Indicators"
    FINANCIAL = "Financial Inputs"
    RATES = "Rate Data"


@dataclass
class DataFieldSpec:
    """Specification for a data field."""
    name: str
    category: DataCategory
    required: bool  # Is this field critical?
    weight: float  # Importance weight (0-1)
    default_value: Any = None  # Industry benchmark default
    description: str = ""


@dataclass
class FieldQualityResult:
    """Quality assessment for a single field."""
    field_name: str
    category: DataCategory
    is_present: bool
    is_valid: bool
    value: Any
    source: str  # Where the data came from
    freshness_days: Optional[int] = None  # How old is the data
    using_default: bool = False
    default_value: Any = None
    warning: Optional[str] = None


@dataclass
class CategoryQualityScore:
    """Quality score for a data category."""
    category: DataCategory
    score: float  # 0-100
    fields_present: int
    fields_total: int
    critical_missing: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class DataQualityAssessment:
    """Complete data quality assessment."""
    overall_score: float  # 0-100
    confidence_level: ConfidenceLevel
    category_scores: Dict[DataCategory, CategoryQualityScore]
    field_results: List[FieldQualityResult]
    critical_issues: List[str]
    warnings: List[str]
    recommendations: List[str]
    data_freshness: str  # "Fresh", "Aging", "Stale"
    assessment_timestamp: datetime


# ============================================================================
# FIELD SPECIFICATIONS
# ============================================================================

# Define all fields and their specifications
DATA_FIELD_SPECS: List[DataFieldSpec] = [
    # Demographics
    DataFieldSpec("population_3mi", DataCategory.DEMOGRAPHICS, True, 1.0, 50000, "3-mile population"),
    DataFieldSpec("median_income", DataCategory.DEMOGRAPHICS, True, 0.9, 65000, "Median household income"),
    DataFieldSpec("population_growth", DataCategory.DEMOGRAPHICS, False, 0.7, 1.5, "Annual growth rate %"),
    DataFieldSpec("renter_pct", DataCategory.DEMOGRAPHICS, False, 0.6, 40, "Renter percentage"),
    DataFieldSpec("age_25_54_pct", DataCategory.DEMOGRAPHICS, False, 0.5, 40, "Age 25-54 percentage"),

    # Supply/Demand
    DataFieldSpec("sf_per_capita", DataCategory.SUPPLY_DEMAND, True, 1.0, 7.5, "SF per capita"),
    DataFieldSpec("avg_occupancy", DataCategory.SUPPLY_DEMAND, True, 0.9, 88, "Average market occupancy"),
    DataFieldSpec("pipeline_sf", DataCategory.SUPPLY_DEMAND, False, 0.7, 0, "Pipeline SF under construction"),
    DataFieldSpec("absorption_trend", DataCategory.SUPPLY_DEMAND, False, 0.5, "Moderate", "Market absorption trend"),

    # Competitors
    DataFieldSpec("competitor_count", DataCategory.COMPETITORS, True, 1.0, 5, "Number of competitors in 3mi"),
    DataFieldSpec("avg_competitor_rate", DataCategory.COMPETITORS, True, 0.9, 120, "Average 10x10 rate"),
    DataFieldSpec("total_competitive_sf", DataCategory.COMPETITORS, False, 0.7, 300000, "Total competitive NRSF"),
    DataFieldSpec("competitor_quality", DataCategory.COMPETITORS, False, 0.5, "Average", "Competitor quality assessment"),

    # Site Characteristics
    DataFieldSpec("visibility", DataCategory.SITE, True, 0.8, "Good", "Site visibility rating"),
    DataFieldSpec("access", DataCategory.SITE, True, 0.8, "Easy", "Site access rating"),
    DataFieldSpec("zoning", DataCategory.SITE, True, 0.9, "Likely", "Zoning approval status"),
    DataFieldSpec("site_size_acres", DataCategory.SITE, False, 0.6, 2.5, "Site size in acres"),

    # Economic
    DataFieldSpec("unemployment_rate", DataCategory.ECONOMIC, False, 0.7, 4.5, "Local unemployment rate"),
    DataFieldSpec("business_growth", DataCategory.ECONOMIC, False, 0.5, "Stable", "Business growth trend"),
    DataFieldSpec("economic_stability", DataCategory.ECONOMIC, False, 0.5, "Stable", "Economic stability assessment"),

    # Financial Inputs
    DataFieldSpec("land_cost", DataCategory.FINANCIAL, True, 1.0, None, "Land acquisition cost"),
    DataFieldSpec("construction_cost_psf", DataCategory.FINANCIAL, True, 1.0, 85, "Construction cost per SF"),
    DataFieldSpec("rentable_sqft", DataCategory.FINANCIAL, True, 1.0, None, "Total rentable square feet"),
    DataFieldSpec("interest_rate", DataCategory.FINANCIAL, False, 0.8, 7.0, "Loan interest rate"),
    DataFieldSpec("ltc_ratio", DataCategory.FINANCIAL, False, 0.6, 0.70, "Loan to cost ratio"),

    # Rate Data
    DataFieldSpec("market_rate_5x5", DataCategory.RATES, False, 0.4, 60, "5x5 unit rate"),
    DataFieldSpec("market_rate_5x10", DataCategory.RATES, False, 0.5, 90, "5x10 unit rate"),
    DataFieldSpec("market_rate_10x10", DataCategory.RATES, True, 0.9, 130, "10x10 unit rate"),
    DataFieldSpec("market_rate_10x15", DataCategory.RATES, False, 0.6, 175, "10x15 unit rate"),
    DataFieldSpec("market_rate_10x20", DataCategory.RATES, False, 0.5, 220, "10x20 unit rate"),
    DataFieldSpec("rate_data_source", DataCategory.RATES, False, 0.3, "Estimate", "Source of rate data"),
]


# ============================================================================
# DATA QUALITY ANALYZER
# ============================================================================

class DataQualityAnalyzer:
    """
    Analyzes data quality for feasibility analysis inputs.
    """

    def __init__(self):
        self.field_specs = {spec.name: spec for spec in DATA_FIELD_SPECS}

    def assess_quality(
        self,
        data: Dict[str, Any],
        data_sources: Dict[str, str] = None,
        data_timestamps: Dict[str, datetime] = None
    ) -> DataQualityAssessment:
        """
        Perform comprehensive data quality assessment.

        Args:
            data: Dict of field_name -> value
            data_sources: Dict of field_name -> source (e.g., "TractiQ", "Manual", "Default")
            data_timestamps: Dict of field_name -> datetime when data was obtained

        Returns:
            DataQualityAssessment with scores and recommendations
        """
        data_sources = data_sources or {}
        data_timestamps = data_timestamps or {}

        field_results = []
        category_fields: Dict[DataCategory, List[FieldQualityResult]] = {
            cat: [] for cat in DataCategory
        }

        # Assess each field
        for field_name, spec in self.field_specs.items():
            result = self._assess_field(field_name, spec, data, data_sources, data_timestamps)
            field_results.append(result)
            category_fields[spec.category].append(result)

        # Calculate category scores
        category_scores = {}
        for category, results in category_fields.items():
            category_scores[category] = self._calculate_category_score(category, results)

        # Calculate overall score
        overall_score = self._calculate_overall_score(category_scores)

        # Determine confidence level
        confidence_level = self._determine_confidence(overall_score, category_scores)

        # Compile issues and warnings
        critical_issues = []
        warnings = []
        for cat_score in category_scores.values():
            critical_issues.extend(cat_score.critical_missing)
            warnings.extend(cat_score.warnings)

        # Generate recommendations
        recommendations = self._generate_recommendations(category_scores, field_results)

        # Assess data freshness
        data_freshness = self._assess_freshness(data_timestamps)

        return DataQualityAssessment(
            overall_score=overall_score,
            confidence_level=confidence_level,
            category_scores=category_scores,
            field_results=field_results,
            critical_issues=critical_issues,
            warnings=warnings,
            recommendations=recommendations,
            data_freshness=data_freshness,
            assessment_timestamp=datetime.now()
        )

    def _assess_field(
        self,
        field_name: str,
        spec: DataFieldSpec,
        data: Dict,
        sources: Dict,
        timestamps: Dict
    ) -> FieldQualityResult:
        """Assess a single field."""
        value = data.get(field_name)
        source = sources.get(field_name, "Unknown")

        # Check if present and valid
        is_present = value is not None and value != ""
        is_valid = is_present and self._validate_value(field_name, value)

        # Calculate freshness
        freshness_days = None
        if field_name in timestamps:
            freshness_days = (datetime.now() - timestamps[field_name]).days

        # Check if using default
        using_default = not is_present or source == "Default"
        default_value = spec.default_value if using_default else None

        # Generate warning if needed
        warning = None
        if spec.required and not is_present:
            warning = f"Critical field '{spec.description}' is missing"
        elif using_default and spec.required:
            warning = f"Using industry default for '{spec.description}'"
        elif freshness_days and freshness_days > 90:
            warning = f"Data for '{spec.description}' is {freshness_days} days old"

        return FieldQualityResult(
            field_name=field_name,
            category=spec.category,
            is_present=is_present,
            is_valid=is_valid,
            value=value if is_valid else default_value,
            source=source,
            freshness_days=freshness_days,
            using_default=using_default,
            default_value=default_value,
            warning=warning
        )

    def _validate_value(self, field_name: str, value: Any) -> bool:
        """Validate a field value."""
        if value is None:
            return False

        # Numeric validation
        numeric_fields = [
            'population_3mi', 'median_income', 'population_growth', 'renter_pct',
            'age_25_54_pct', 'sf_per_capita', 'avg_occupancy', 'pipeline_sf',
            'competitor_count', 'avg_competitor_rate', 'total_competitive_sf',
            'site_size_acres', 'unemployment_rate', 'land_cost', 'construction_cost_psf',
            'rentable_sqft', 'interest_rate', 'ltc_ratio', 'market_rate_5x5',
            'market_rate_5x10', 'market_rate_10x10', 'market_rate_10x15', 'market_rate_10x20'
        ]

        if field_name in numeric_fields:
            try:
                float(value)
                return True
            except (ValueError, TypeError):
                return False

        return True

    def _calculate_category_score(
        self,
        category: DataCategory,
        results: List[FieldQualityResult]
    ) -> CategoryQualityScore:
        """Calculate quality score for a category."""
        if not results:
            return CategoryQualityScore(
                category=category, score=0, fields_present=0, fields_total=0
            )

        total_weight = 0
        weighted_score = 0
        fields_present = 0
        critical_missing = []
        warnings = []

        for result in results:
            spec = self.field_specs.get(result.field_name)
            if not spec:
                continue

            total_weight += spec.weight

            if result.is_present and result.is_valid:
                fields_present += 1
                # Penalize if using default
                if result.using_default:
                    weighted_score += spec.weight * 0.5
                else:
                    weighted_score += spec.weight * 1.0
            else:
                if spec.required:
                    critical_missing.append(f"Missing: {spec.description}")

            if result.warning:
                warnings.append(result.warning)

        score = (weighted_score / total_weight * 100) if total_weight > 0 else 0

        return CategoryQualityScore(
            category=category,
            score=round(score, 1),
            fields_present=fields_present,
            fields_total=len(results),
            critical_missing=critical_missing,
            warnings=warnings
        )

    def _calculate_overall_score(
        self,
        category_scores: Dict[DataCategory, CategoryQualityScore]
    ) -> float:
        """Calculate overall quality score."""
        # Category weights
        weights = {
            DataCategory.DEMOGRAPHICS: 0.20,
            DataCategory.SUPPLY_DEMAND: 0.20,
            DataCategory.COMPETITORS: 0.20,
            DataCategory.SITE: 0.15,
            DataCategory.ECONOMIC: 0.05,
            DataCategory.FINANCIAL: 0.15,
            DataCategory.RATES: 0.05,
        }

        weighted_sum = 0
        weight_total = 0

        for category, cat_score in category_scores.items():
            weight = weights.get(category, 0.1)
            weighted_sum += cat_score.score * weight
            weight_total += weight

        return round(weighted_sum / weight_total, 1) if weight_total > 0 else 0

    def _determine_confidence(
        self,
        overall_score: float,
        category_scores: Dict[DataCategory, CategoryQualityScore]
    ) -> ConfidenceLevel:
        """Determine analysis confidence level."""
        # Check for critical categories
        critical_categories = [
            DataCategory.DEMOGRAPHICS,
            DataCategory.SUPPLY_DEMAND,
            DataCategory.COMPETITORS,
            DataCategory.FINANCIAL
        ]

        critical_scores = [
            category_scores[cat].score
            for cat in critical_categories
            if cat in category_scores
        ]

        min_critical = min(critical_scores) if critical_scores else 0

        # Determine confidence
        if overall_score >= 80 and min_critical >= 70:
            return ConfidenceLevel.HIGH
        elif overall_score >= 60 and min_critical >= 50:
            return ConfidenceLevel.MEDIUM
        elif overall_score >= 40:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.INSUFFICIENT

    def _generate_recommendations(
        self,
        category_scores: Dict[DataCategory, CategoryQualityScore],
        field_results: List[FieldQualityResult]
    ) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []

        # Category-specific recommendations
        for category, score in category_scores.items():
            if score.score < 50:
                if category == DataCategory.COMPETITORS:
                    recommendations.append(
                        "Upload TractiQ competitor report for detailed competitive intelligence"
                    )
                elif category == DataCategory.RATES:
                    recommendations.append(
                        "Upload TractiQ Rate Trends report for accurate market rate data"
                    )
                elif category == DataCategory.DEMOGRAPHICS:
                    recommendations.append(
                        "Upload TractiQ Demographic Profile for verified population data"
                    )
                elif category == DataCategory.FINANCIAL:
                    recommendations.append(
                        "Enter land cost and development budget for financial analysis"
                    )

        # Field-specific recommendations
        defaults_used = [r for r in field_results if r.using_default and r.warning]
        if len(defaults_used) > 3:
            recommendations.append(
                f"{len(defaults_used)} fields using industry defaults - upload TractiQ data for accuracy"
            )

        # Freshness recommendations
        stale_fields = [
            r for r in field_results
            if r.freshness_days and r.freshness_days > 60
        ]
        if stale_fields:
            recommendations.append(
                "Some data is over 60 days old - consider refreshing market data"
            )

        return recommendations[:5]  # Top 5 recommendations

    def _assess_freshness(self, timestamps: Dict[str, datetime]) -> str:
        """Assess overall data freshness."""
        if not timestamps:
            return "Unknown"

        avg_age_days = sum(
            (datetime.now() - ts).days
            for ts in timestamps.values()
        ) / len(timestamps)

        if avg_age_days <= 30:
            return "Fresh"
        elif avg_age_days <= 90:
            return "Aging"
        else:
            return "Stale"

    def get_defaults_for_missing(
        self,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Get industry defaults for missing fields.

        Args:
            data: Current data dict

        Returns:
            Dict with defaults filled in for missing values
        """
        result = data.copy()

        for field_name, spec in self.field_specs.items():
            if field_name not in result or result[field_name] is None:
                if spec.default_value is not None:
                    result[field_name] = spec.default_value

        return result


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def assess_data_quality(
    data: Dict[str, Any],
    data_sources: Dict[str, str] = None,
    data_timestamps: Dict[str, datetime] = None
) -> DataQualityAssessment:
    """
    Convenience function to assess data quality.

    Usage:
        assessment = assess_data_quality({
            'population_3mi': 85000,
            'median_income': 68000,
            'sf_per_capita': 6.2,
            ...
        })

        print(f"Quality Score: {assessment.overall_score}/100")
        print(f"Confidence: {assessment.confidence_level.value}")
    """
    analyzer = DataQualityAnalyzer()
    return analyzer.assess_quality(data, data_sources, data_timestamps)


def fill_missing_with_defaults(data: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """
    Fill missing data with industry defaults and track what was filled.

    Returns:
        Tuple of (filled_data, list_of_fields_defaulted)
    """
    analyzer = DataQualityAnalyzer()
    filled = analyzer.get_defaults_for_missing(data)

    # Track what was filled
    defaulted = [
        field for field in filled
        if field not in data or data[field] is None
    ]

    return filled, defaulted


def get_quality_summary_html(assessment: DataQualityAssessment) -> str:
    """
    Generate HTML summary of data quality for display in Streamlit.

    Args:
        assessment: DataQualityAssessment object

    Returns:
        HTML string for st.markdown(unsafe_allow_html=True)
    """
    # Color coding
    score_color = (
        '#28a745' if assessment.overall_score >= 80
        else '#ffc107' if assessment.overall_score >= 60
        else '#dc3545'
    )

    confidence_color = {
        ConfidenceLevel.HIGH: '#28a745',
        ConfidenceLevel.MEDIUM: '#ffc107',
        ConfidenceLevel.LOW: '#fd7e14',
        ConfidenceLevel.INSUFFICIENT: '#dc3545'
    }.get(assessment.confidence_level, '#666')

    # Category bars
    category_bars = ""
    for cat, score in assessment.category_scores.items():
        bar_color = (
            '#28a745' if score.score >= 70
            else '#ffc107' if score.score >= 50
            else '#dc3545'
        )
        category_bars += f"""
        <div style="margin-bottom: 10px;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 2px;">
                <span>{cat.value}</span>
                <span>{score.score:.0f}%</span>
            </div>
            <div style="background: #e0e0e0; border-radius: 4px; height: 8px;">
                <div style="background: {bar_color}; width: {score.score}%; height: 100%; border-radius: 4px;"></div>
            </div>
        </div>
        """

    # Critical issues
    issues_html = ""
    if assessment.critical_issues:
        issues_list = "".join(f"<li>{issue}</li>" for issue in assessment.critical_issues[:5])
        issues_html = f"""
        <div style="background: #f8d7da; border-left: 4px solid #dc3545; padding: 10px; margin: 10px 0; border-radius: 4px;">
            <strong>Critical Issues:</strong>
            <ul style="margin: 5px 0; padding-left: 20px;">{issues_list}</ul>
        </div>
        """

    # Recommendations
    rec_html = ""
    if assessment.recommendations:
        rec_list = "".join(f"<li>{rec}</li>" for rec in assessment.recommendations[:3])
        rec_html = f"""
        <div style="background: #d1ecf1; border-left: 4px solid #17a2b8; padding: 10px; margin: 10px 0; border-radius: 4px;">
            <strong>Recommendations:</strong>
            <ul style="margin: 5px 0; padding-left: 20px;">{rec_list}</ul>
        </div>
        """

    return f"""
    <div style="background: #f8f9fa; padding: 20px; border-radius: 8px;">
        <div style="display: flex; justify-content: space-between; margin-bottom: 20px;">
            <div>
                <h4 style="margin: 0; color: #0C2340;">Data Quality Score</h4>
                <h1 style="margin: 5px 0; color: {score_color};">{assessment.overall_score:.0f}/100</h1>
            </div>
            <div style="text-align: right;">
                <h4 style="margin: 0; color: #0C2340;">Analysis Confidence</h4>
                <h2 style="margin: 5px 0; color: {confidence_color};">{assessment.confidence_level.value}</h2>
                <small>Data Freshness: {assessment.data_freshness}</small>
            </div>
        </div>

        <h5 style="margin-bottom: 10px; color: #0C2340;">Category Scores</h5>
        {category_bars}

        {issues_html}
        {rec_html}
    </div>
    """


# ============================================================================
# TEST
# ============================================================================

if __name__ == "__main__":
    # Test with sample data
    test_data = {
        'population_3mi': 85000,
        'median_income': 68000,
        'population_growth': 2.5,
        'sf_per_capita': 6.2,
        'avg_occupancy': 89,
        'competitor_count': 5,
        'avg_competitor_rate': 135,
        'visibility': 'Good',
        'access': 'Easy',
        'zoning': 'Likely',
        'land_cost': 1200000,
        'construction_cost_psf': 85,
        'rentable_sqft': 75000,
        'market_rate_10x10': 135,
    }

    assessment = assess_data_quality(test_data)

    print("=" * 60)
    print("DATA QUALITY ASSESSMENT")
    print("=" * 60)
    print(f"\nOverall Score: {assessment.overall_score}/100")
    print(f"Confidence: {assessment.confidence_level.value}")
    print(f"Data Freshness: {assessment.data_freshness}")

    print("\nCategory Scores:")
    for cat, score in assessment.category_scores.items():
        print(f"  {cat.value}: {score.score:.0f}% ({score.fields_present}/{score.fields_total} fields)")

    if assessment.critical_issues:
        print("\nCritical Issues:")
        for issue in assessment.critical_issues:
            print(f"  - {issue}")

    if assessment.recommendations:
        print("\nRecommendations:")
        for rec in assessment.recommendations:
            print(f"  - {rec}")

    print("\n" + "=" * 60)
