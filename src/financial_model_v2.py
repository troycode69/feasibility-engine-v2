"""
Enhanced Financial Model for Self-Storage Feasibility Analysis (V2)

McKinley-level institutional-grade financial modeling:
- 84-month (7-year) cash flows at monthly granularity
- Revenue by unit size category (5x5, 5x10, 10x10, 10x15, 10x20, 10x30)
- Climate-controlled vs non-CC rate differentiation
- Unit-level occupancy curves (smaller units lease faster)
- Detailed expense breakdown by month
- Support for sensitivity analysis and scenario modeling

Based on institutional self-storage underwriting standards.
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import json


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class UnitType:
    """Individual unit type configuration"""
    size: str  # "5x5", "5x10", "10x10", "10x15", "10x20", "10x30"
    sf_per_unit: int  # Square feet per unit
    unit_count: int  # Number of units
    climate_controlled: bool
    monthly_rate: float  # $/unit/month
    rate_psf: float = 0.0  # Calculated: monthly_rate / sf_per_unit
    total_sf: int = 0  # Calculated: sf_per_unit * unit_count
    lease_up_modifier: float = 1.0  # 1.2 = leases 20% faster, 0.8 = 20% slower

    def __post_init__(self):
        self.rate_psf = self.monthly_rate / self.sf_per_unit if self.sf_per_unit > 0 else 0
        self.total_sf = self.sf_per_unit * self.unit_count


@dataclass
class UnitMix:
    """Complete unit mix for a facility"""
    units: List[UnitType] = field(default_factory=list)

    @property
    def total_units(self) -> int:
        return sum(u.unit_count for u in self.units)

    @property
    def total_sf(self) -> int:
        return sum(u.total_sf for u in self.units)

    @property
    def total_monthly_gpr(self) -> float:
        """Gross potential revenue per month at 100% occupancy"""
        return sum(u.monthly_rate * u.unit_count for u in self.units)

    @property
    def weighted_avg_rate_psf(self) -> float:
        """Weighted average rate per SF"""
        total_rev = self.total_monthly_gpr
        total_sf = self.total_sf
        return total_rev / total_sf if total_sf > 0 else 0

    @property
    def cc_percentage(self) -> float:
        """Percentage of SF that is climate controlled"""
        cc_sf = sum(u.total_sf for u in self.units if u.climate_controlled)
        return (cc_sf / self.total_sf * 100) if self.total_sf > 0 else 0


@dataclass
class MonthlyCashFlow:
    """Single month's cash flow detail"""
    month: int  # 1-84
    date: str  # YYYY-MM

    # Occupancy
    occupancy_pct: float
    occupied_units: int
    occupied_sf: int

    # Revenue
    revenue_by_unit_type: Dict[str, float] = field(default_factory=dict)
    gross_potential_revenue: float = 0
    vacancy_loss: float = 0
    concessions: float = 0
    other_income: float = 0
    effective_gross_revenue: float = 0

    # Expenses (monthly)
    property_taxes: float = 0
    insurance: float = 0
    utilities: float = 0
    management_fee: float = 0
    onsite_labor: float = 0
    marketing: float = 0
    maintenance_repairs: float = 0
    administrative: float = 0
    total_operating_expenses: float = 0

    # NOI
    net_operating_income: float = 0

    # Below the line
    debt_service: float = 0
    capital_reserves: float = 0
    cash_flow_before_tax: float = 0

    # Cumulative
    cumulative_noi: float = 0
    cumulative_cash_flow: float = 0


@dataclass
class AnnualSummary:
    """Annual summary of financial performance"""
    year: int

    # Revenue
    gross_potential_revenue: float = 0
    effective_gross_revenue: float = 0

    # Occupancy
    avg_occupancy_pct: float = 0
    year_end_occupancy_pct: float = 0

    # Expenses & NOI
    total_operating_expenses: float = 0
    net_operating_income: float = 0
    expense_ratio: float = 0  # OpEx / EGR

    # Cash flow
    debt_service: float = 0
    capital_reserves: float = 0
    cash_flow_before_tax: float = 0

    # Returns (calculated at sale)
    property_value: float = 0  # NOI / Cap Rate
    equity_value: float = 0  # Property Value - Loan Balance


@dataclass
class DevelopmentBudget:
    """Detailed development cost breakdown"""
    # Land
    land_cost: float = 0
    site_work: float = 0

    # Hard costs
    building_cost: float = 0
    sitework_civil: float = 0
    landscaping: float = 0
    signage: float = 0
    security_gates: float = 0
    total_hard_costs: float = 0

    # Soft costs
    architecture_engineering: float = 0
    permits_fees: float = 0
    legal: float = 0
    accounting: float = 0
    marketing_preleasing: float = 0
    development_fee: float = 0
    total_soft_costs: float = 0

    # Financing
    construction_interest: float = 0
    loan_fees: float = 0
    total_financing_costs: float = 0

    # Contingency
    hard_cost_contingency: float = 0
    soft_cost_contingency: float = 0
    total_contingency: float = 0

    # Totals
    total_development_cost: float = 0
    cost_per_sf: float = 0

    def calculate_totals(self, nrsf: int):
        """Calculate all totals"""
        self.total_hard_costs = (
            self.building_cost + self.sitework_civil +
            self.landscaping + self.signage + self.security_gates
        )
        self.total_soft_costs = (
            self.architecture_engineering + self.permits_fees +
            self.legal + self.accounting + self.marketing_preleasing +
            self.development_fee
        )
        self.total_financing_costs = self.construction_interest + self.loan_fees
        self.total_contingency = self.hard_cost_contingency + self.soft_cost_contingency

        self.total_development_cost = (
            self.land_cost + self.site_work +
            self.total_hard_costs + self.total_soft_costs +
            self.total_financing_costs + self.total_contingency
        )

        self.cost_per_sf = self.total_development_cost / nrsf if nrsf > 0 else 0


@dataclass
class FinancingStructure:
    """Debt financing structure"""
    # Construction loan
    construction_loan_amount: float = 0
    construction_ltc: float = 0.70  # 70% LTC
    construction_rate: float = 0.08  # 8%
    construction_term_months: int = 24

    # Permanent loan
    permanent_loan_amount: float = 0
    permanent_ltv: float = 0.65  # 65% LTV at stabilization
    permanent_rate: float = 0.065  # 6.5%
    permanent_term_years: int = 10
    permanent_amort_years: int = 25

    # Calculated
    monthly_debt_service: float = 0
    annual_debt_service: float = 0

    def calculate_permanent_payment(self):
        """Calculate permanent loan monthly payment"""
        if self.permanent_loan_amount == 0 or self.permanent_rate == 0:
            return 0

        monthly_rate = self.permanent_rate / 12
        n_payments = self.permanent_amort_years * 12

        payment = self.permanent_loan_amount * (
            monthly_rate * (1 + monthly_rate) ** n_payments
        ) / ((1 + monthly_rate) ** n_payments - 1)

        self.monthly_debt_service = payment
        self.annual_debt_service = payment * 12
        return payment


@dataclass
class ReturnMetrics:
    """Investment return metrics"""
    # Development returns
    development_yield: float = 0  # Stabilized NOI / Total Cost
    development_spread: float = 0  # Dev Yield - Exit Cap Rate

    # Operating returns
    stabilized_cap_rate: float = 0
    cash_on_cash_year1: float = 0
    dscr_stabilized: float = 0
    break_even_occupancy: float = 0

    # Investment returns
    irr_7yr: float = 0
    irr_10yr: float = 0
    npv_7yr: float = 0
    npv_10yr: float = 0
    equity_multiple_7yr: float = 0
    equity_multiple_10yr: float = 0

    # Sensitivity results (populated by sensitivity analysis)
    irr_range: Tuple[float, float] = (0, 0)  # (min, max) across scenarios


@dataclass
class EnhancedProForma:
    """Complete enhanced pro forma model"""
    # Project info
    project_name: str = ""
    address: str = ""
    analysis_date: str = ""

    # Physical
    unit_mix: UnitMix = field(default_factory=UnitMix)
    nrsf: int = 0

    # Financial structure
    development_budget: DevelopmentBudget = field(default_factory=DevelopmentBudget)
    financing: FinancingStructure = field(default_factory=FinancingStructure)

    # Assumptions
    months_to_stabilization: int = 36
    stabilized_occupancy: float = 92.0
    annual_rate_growth: float = 0.03  # 3%
    annual_expense_growth: float = 0.025  # 2.5%
    exit_cap_rate: float = 0.065  # 6.5%
    discount_rate: float = 0.10  # 10% for NPV

    # Projections
    monthly_cash_flows: List[MonthlyCashFlow] = field(default_factory=list)
    annual_summaries: List[AnnualSummary] = field(default_factory=list)

    # Returns
    metrics: ReturnMetrics = field(default_factory=ReturnMetrics)


# ============================================================================
# LEASE-UP CURVES
# ============================================================================

def get_lease_up_curve(months_to_stabilization: int, stabilized_occupancy: float) -> List[float]:
    """
    Generate S-curve lease-up trajectory.

    Args:
        months_to_stabilization: Months to reach stabilized occupancy
        stabilized_occupancy: Target occupancy (e.g., 92.0 for 92%)

    Returns:
        List of 84 monthly occupancy percentages
    """
    import math

    occupancy_curve = []

    for month in range(1, 85):  # 84 months
        if month >= months_to_stabilization:
            # At or past stabilization
            occ = stabilized_occupancy
        else:
            # S-curve: starts slow, accelerates, then slows as approaching stabilization
            # Using logistic function
            x = (month / months_to_stabilization) * 12 - 6  # Map to [-6, 6] range
            s_curve = 1 / (1 + math.exp(-x))
            occ = s_curve * stabilized_occupancy

        occupancy_curve.append(round(occ, 2))

    return occupancy_curve


def get_unit_type_lease_up_modifier(size: str, climate_controlled: bool) -> float:
    """
    Get lease-up speed modifier by unit type.
    Smaller units and climate-controlled units typically lease faster.

    Args:
        size: Unit size (e.g., "5x5", "10x20")
        climate_controlled: Whether unit is climate controlled

    Returns:
        Modifier (1.0 = standard, 1.2 = 20% faster, 0.8 = 20% slower)
    """
    # Base modifier by size
    size_modifiers = {
        "5x5": 1.15,    # Small units lease fastest
        "5x10": 1.10,
        "10x10": 1.05,  # Sweet spot - most common
        "10x15": 1.00,
        "10x20": 0.95,
        "10x25": 0.90,
        "10x30": 0.85,  # Large units take longer
    }

    modifier = size_modifiers.get(size, 1.0)

    # Climate controlled bonus
    if climate_controlled:
        modifier += 0.05

    return modifier


# ============================================================================
# EXPENSE CALCULATIONS
# ============================================================================

def calculate_monthly_expenses(
    effective_gross_revenue: float,
    nrsf: int,
    month: int,
    base_expense_ratios: Dict[str, float],
    annual_expense_growth: float = 0.025
) -> Dict[str, float]:
    """
    Calculate monthly operating expenses with inflation.

    Args:
        effective_gross_revenue: Monthly EGR
        nrsf: Net rentable square feet
        month: Month number (1-84)
        base_expense_ratios: Base expense ratios as % of EGR
        annual_expense_growth: Annual expense inflation

    Returns:
        Dict of expense categories and amounts
    """
    # Calculate inflation factor
    years_elapsed = (month - 1) / 12
    inflation_factor = (1 + annual_expense_growth) ** years_elapsed

    # Base expense ratios (as % of EGR)
    default_ratios = {
        "property_taxes": 0.08,      # 8%
        "insurance": 0.02,           # 2%
        "utilities": 0.04,           # 4%
        "management_fee": 0.06,      # 6%
        "onsite_labor": 0.08,        # 8%
        "marketing": 0.03,           # 3%
        "maintenance_repairs": 0.03, # 3%
        "administrative": 0.02,      # 2%
    }

    ratios = {**default_ratios, **base_expense_ratios}

    expenses = {}
    for category, ratio in ratios.items():
        base_expense = effective_gross_revenue * ratio
        expenses[category] = base_expense * inflation_factor

    return expenses


def get_expense_ratios_by_size(nrsf: int) -> Dict[str, float]:
    """
    Get expense ratios based on facility size.
    Larger facilities have economies of scale.

    Args:
        nrsf: Net rentable square feet

    Returns:
        Dict of expense category ratios
    """
    if nrsf < 40000:
        # Small facility - higher expense ratio
        return {
            "property_taxes": 0.09,
            "insurance": 0.025,
            "utilities": 0.045,
            "management_fee": 0.07,
            "onsite_labor": 0.10,
            "marketing": 0.04,
            "maintenance_repairs": 0.035,
            "administrative": 0.025,
        }
    elif nrsf < 70000:
        # Medium facility
        return {
            "property_taxes": 0.08,
            "insurance": 0.02,
            "utilities": 0.04,
            "management_fee": 0.06,
            "onsite_labor": 0.08,
            "marketing": 0.03,
            "maintenance_repairs": 0.03,
            "administrative": 0.02,
        }
    else:
        # Large facility - economies of scale
        return {
            "property_taxes": 0.07,
            "insurance": 0.018,
            "utilities": 0.035,
            "management_fee": 0.05,
            "onsite_labor": 0.06,
            "marketing": 0.025,
            "maintenance_repairs": 0.025,
            "administrative": 0.015,
        }


# ============================================================================
# CORE PROJECTION ENGINE
# ============================================================================

def project_monthly_cash_flows(
    unit_mix: UnitMix,
    development_budget: DevelopmentBudget,
    financing: FinancingStructure,
    months_to_stabilization: int = 36,
    stabilized_occupancy: float = 92.0,
    annual_rate_growth: float = 0.03,
    annual_expense_growth: float = 0.025,
    start_date: Optional[date] = None,
    concession_months: int = 3,
    concession_rate: float = 0.50,  # 50% off first month
) -> List[MonthlyCashFlow]:
    """
    Project 84-month cash flows with unit-mix-specific revenue.

    Args:
        unit_mix: Unit mix configuration
        development_budget: Development costs
        financing: Financing structure
        months_to_stabilization: Months to reach stabilized occupancy
        stabilized_occupancy: Target occupancy percentage
        annual_rate_growth: Annual rate escalation
        annual_expense_growth: Annual expense inflation
        start_date: Operations start date
        concession_months: How many months to offer concessions during lease-up
        concession_rate: Concession amount as % of rent

    Returns:
        List of 84 MonthlyCashFlow objects
    """
    if start_date is None:
        start_date = date.today().replace(day=1)

    # Get base lease-up curve
    base_curve = get_lease_up_curve(months_to_stabilization, stabilized_occupancy)

    # Get expense ratios
    expense_ratios = get_expense_ratios_by_size(unit_mix.total_sf)

    cash_flows = []
    cumulative_noi = 0
    cumulative_cf = 0

    for month in range(1, 85):
        current_date = start_date + relativedelta(months=month-1)

        # Calculate occupancy for this month
        base_occupancy = base_curve[month - 1]

        # Calculate revenue by unit type (with individual lease-up modifiers)
        revenue_by_type = {}
        total_gpr = 0
        total_occupied_units = 0
        total_occupied_sf = 0

        # Apply rate growth
        years_elapsed = (month - 1) / 12
        rate_growth_factor = (1 + annual_rate_growth) ** years_elapsed

        for unit_type in unit_mix.units:
            # Adjust occupancy for unit type
            unit_occ = min(base_occupancy * unit_type.lease_up_modifier, stabilized_occupancy)

            # Calculate units occupied
            units_occupied = int(unit_type.unit_count * (unit_occ / 100))
            sf_occupied = units_occupied * unit_type.sf_per_unit

            # Calculate revenue with rate growth
            current_rate = unit_type.monthly_rate * rate_growth_factor
            unit_revenue = units_occupied * current_rate

            # Store
            key = f"{'CC' if unit_type.climate_controlled else 'NC'}_{unit_type.size}"
            revenue_by_type[key] = unit_revenue

            total_gpr += unit_type.unit_count * current_rate  # GPR at 100%
            total_occupied_units += units_occupied
            total_occupied_sf += sf_occupied

        # Calculate actual revenue
        actual_revenue = sum(revenue_by_type.values())
        vacancy_loss = total_gpr - actual_revenue

        # Concessions (during lease-up only)
        concessions = 0
        if month <= concession_months and concession_rate > 0:
            # Apply concessions to portion of new leases
            new_lease_estimate = total_occupied_units * 0.2  # ~20% of occupied are new
            concessions = new_lease_estimate * (total_gpr / unit_mix.total_units) * concession_rate

        # Other income (late fees, admin fees, merchandise)
        other_income = actual_revenue * 0.02  # ~2% of rent

        # Effective Gross Revenue
        egr = actual_revenue - concessions + other_income

        # Operating expenses
        expenses = calculate_monthly_expenses(
            egr, unit_mix.total_sf, month, expense_ratios, annual_expense_growth
        )
        total_expenses = sum(expenses.values())

        # NOI
        noi = egr - total_expenses

        # Debt service (monthly)
        debt_service = financing.monthly_debt_service

        # Capital reserves (1% of EGR)
        cap_reserves = egr * 0.01

        # Cash flow before tax
        cfbt = noi - debt_service - cap_reserves

        # Update cumulatives
        cumulative_noi += noi
        cumulative_cf += cfbt

        # Create cash flow record
        cf = MonthlyCashFlow(
            month=month,
            date=current_date.strftime("%Y-%m"),
            occupancy_pct=round(base_occupancy, 1),
            occupied_units=total_occupied_units,
            occupied_sf=total_occupied_sf,
            revenue_by_unit_type=revenue_by_type,
            gross_potential_revenue=total_gpr,
            vacancy_loss=vacancy_loss,
            concessions=concessions,
            other_income=other_income,
            effective_gross_revenue=egr,
            property_taxes=expenses.get("property_taxes", 0),
            insurance=expenses.get("insurance", 0),
            utilities=expenses.get("utilities", 0),
            management_fee=expenses.get("management_fee", 0),
            onsite_labor=expenses.get("onsite_labor", 0),
            marketing=expenses.get("marketing", 0),
            maintenance_repairs=expenses.get("maintenance_repairs", 0),
            administrative=expenses.get("administrative", 0),
            total_operating_expenses=total_expenses,
            net_operating_income=noi,
            debt_service=debt_service,
            capital_reserves=cap_reserves,
            cash_flow_before_tax=cfbt,
            cumulative_noi=cumulative_noi,
            cumulative_cash_flow=cumulative_cf,
        )

        cash_flows.append(cf)

    return cash_flows


def summarize_annual(monthly_cash_flows: List[MonthlyCashFlow], exit_cap_rate: float, loan_balance: float) -> List[AnnualSummary]:
    """
    Aggregate monthly cash flows into annual summaries.

    Args:
        monthly_cash_flows: List of 84 monthly cash flows
        exit_cap_rate: Cap rate for property valuation
        loan_balance: Outstanding loan balance

    Returns:
        List of 7 AnnualSummary objects
    """
    summaries = []

    for year in range(1, 8):
        start_month = (year - 1) * 12
        end_month = year * 12

        year_months = monthly_cash_flows[start_month:end_month]

        if not year_months:
            continue

        summary = AnnualSummary(
            year=year,
            gross_potential_revenue=sum(m.gross_potential_revenue for m in year_months),
            effective_gross_revenue=sum(m.effective_gross_revenue for m in year_months),
            avg_occupancy_pct=sum(m.occupancy_pct for m in year_months) / len(year_months),
            year_end_occupancy_pct=year_months[-1].occupancy_pct,
            total_operating_expenses=sum(m.total_operating_expenses for m in year_months),
            net_operating_income=sum(m.net_operating_income for m in year_months),
            debt_service=sum(m.debt_service for m in year_months),
            capital_reserves=sum(m.capital_reserves for m in year_months),
            cash_flow_before_tax=sum(m.cash_flow_before_tax for m in year_months),
        )

        # Calculate expense ratio
        if summary.effective_gross_revenue > 0:
            summary.expense_ratio = summary.total_operating_expenses / summary.effective_gross_revenue

        # Property value based on NOI / cap rate
        if exit_cap_rate > 0:
            summary.property_value = summary.net_operating_income / exit_cap_rate
            summary.equity_value = summary.property_value - loan_balance

        summaries.append(summary)

    return summaries


# ============================================================================
# RETURN CALCULATIONS
# ============================================================================

def calculate_irr(cash_flows: List[float], initial_guess: float = 0.10) -> float:
    """
    Calculate Internal Rate of Return using Newton's method.

    Args:
        cash_flows: List of annual cash flows (year 0 = initial investment as negative)
        initial_guess: Starting guess for IRR

    Returns:
        IRR as decimal (e.g., 0.15 for 15%)
    """
    if len(cash_flows) < 2:
        return 0.0

    rate = initial_guess
    max_iterations = 100
    tolerance = 0.0001

    for _ in range(max_iterations):
        npv = sum(cf / ((1 + rate) ** t) for t, cf in enumerate(cash_flows))
        d_npv = sum(-t * cf / ((1 + rate) ** (t + 1)) for t, cf in enumerate(cash_flows))

        if abs(d_npv) < 1e-10:
            break

        new_rate = rate - npv / d_npv

        if abs(new_rate - rate) < tolerance:
            return max(min(new_rate, 1.0), -0.99)  # Bound to reasonable range

        rate = new_rate

        if rate < -0.99 or rate > 10.0:
            return 0.0

    return rate if -0.99 < rate < 1.0 else 0.0


def calculate_npv(cash_flows: List[float], discount_rate: float = 0.10) -> float:
    """
    Calculate Net Present Value.

    Args:
        cash_flows: List of annual cash flows (year 0 = initial investment as negative)
        discount_rate: Discount rate (e.g., 0.10 for 10%)

    Returns:
        NPV in dollars
    """
    return sum(cf / ((1 + discount_rate) ** t) for t, cf in enumerate(cash_flows))


def calculate_return_metrics(
    annual_summaries: List[AnnualSummary],
    development_budget: DevelopmentBudget,
    financing: FinancingStructure,
    exit_cap_rate: float = 0.065,
    discount_rate: float = 0.10
) -> ReturnMetrics:
    """
    Calculate all return metrics.

    Args:
        annual_summaries: Annual financial summaries
        development_budget: Total development costs
        financing: Financing structure
        exit_cap_rate: Cap rate for exit valuation
        discount_rate: Discount rate for NPV

    Returns:
        ReturnMetrics with all calculated values
    """
    metrics = ReturnMetrics()

    if not annual_summaries:
        return metrics

    total_cost = development_budget.total_development_cost
    equity = total_cost - financing.permanent_loan_amount

    # Get stabilized year (usually year 3 or 4)
    stabilized_idx = min(3, len(annual_summaries) - 1)
    stabilized_noi = annual_summaries[stabilized_idx].net_operating_income

    # Development yield
    metrics.development_yield = stabilized_noi / total_cost if total_cost > 0 else 0
    metrics.development_spread = metrics.development_yield - exit_cap_rate

    # Stabilized cap rate
    metrics.stabilized_cap_rate = metrics.development_yield

    # Cash on cash (year 1)
    if equity > 0 and len(annual_summaries) > 0:
        metrics.cash_on_cash_year1 = annual_summaries[0].cash_flow_before_tax / equity

    # DSCR at stabilization
    if financing.annual_debt_service > 0:
        metrics.dscr_stabilized = stabilized_noi / financing.annual_debt_service

    # Break-even occupancy
    if len(annual_summaries) > 0:
        stabilized = annual_summaries[stabilized_idx]
        if stabilized.gross_potential_revenue > 0:
            required_revenue = stabilized.total_operating_expenses + financing.annual_debt_service
            metrics.break_even_occupancy = (required_revenue / stabilized.gross_potential_revenue) * 100

    # Build cash flow arrays for IRR/NPV
    # 7-year
    cf_7yr = [-equity]
    for i, year in enumerate(annual_summaries[:7]):
        cf = year.cash_flow_before_tax
        if i == 6:  # Final year - add sale proceeds
            exit_value = year.net_operating_income / exit_cap_rate
            # Simplified loan balance (assume 85% of original after 7 years)
            loan_balance = financing.permanent_loan_amount * 0.85
            sale_proceeds = exit_value - loan_balance
            cf += sale_proceeds
        cf_7yr.append(cf)

    # 10-year (extend with stabilized cash flow)
    cf_10yr = [-equity]
    for i in range(10):
        if i < len(annual_summaries):
            cf = annual_summaries[i].cash_flow_before_tax
        else:
            cf = annual_summaries[-1].cash_flow_before_tax  # Use last year's CF

        if i == 9:  # Final year - add sale proceeds
            noi = annual_summaries[min(i, len(annual_summaries)-1)].net_operating_income
            exit_value = noi / exit_cap_rate
            loan_balance = financing.permanent_loan_amount * 0.75  # ~75% remaining after 10yr
            sale_proceeds = exit_value - loan_balance
            cf += sale_proceeds
        cf_10yr.append(cf)

    # Calculate IRR and NPV
    metrics.irr_7yr = calculate_irr(cf_7yr) * 100
    metrics.irr_10yr = calculate_irr(cf_10yr) * 100
    metrics.npv_7yr = calculate_npv(cf_7yr, discount_rate)
    metrics.npv_10yr = calculate_npv(cf_10yr, discount_rate)

    # Equity multiple
    total_cf_7yr = sum(cf_7yr[1:])
    total_cf_10yr = sum(cf_10yr[1:])
    metrics.equity_multiple_7yr = total_cf_7yr / equity if equity > 0 else 0
    metrics.equity_multiple_10yr = total_cf_10yr / equity if equity > 0 else 0

    return metrics


# ============================================================================
# MAIN BUILD FUNCTION
# ============================================================================

def build_enhanced_pro_forma(
    project_name: str,
    address: str,
    unit_mix: UnitMix,
    land_cost: float,
    construction_cost_psf: float = 85.0,
    soft_cost_pct: float = 0.15,
    contingency_pct: float = 0.05,
    ltc: float = 0.70,
    interest_rate: float = 0.065,
    loan_term_years: int = 10,
    amort_years: int = 25,
    months_to_stabilization: int = 36,
    stabilized_occupancy: float = 92.0,
    annual_rate_growth: float = 0.03,
    annual_expense_growth: float = 0.025,
    exit_cap_rate: float = 0.065,
    discount_rate: float = 0.10,
) -> EnhancedProForma:
    """
    Build complete enhanced pro forma model.

    Args:
        project_name: Project name
        address: Site address
        unit_mix: Configured unit mix
        land_cost: Land acquisition cost
        construction_cost_psf: Hard cost per SF
        soft_cost_pct: Soft costs as % of hard costs
        contingency_pct: Contingency as % of hard+soft
        ltc: Loan-to-cost ratio
        interest_rate: Permanent loan interest rate
        loan_term_years: Loan term
        amort_years: Amortization period
        months_to_stabilization: Months to reach stabilized occupancy
        stabilized_occupancy: Target occupancy %
        annual_rate_growth: Annual rate escalation
        annual_expense_growth: Annual expense inflation
        exit_cap_rate: Exit cap rate for valuation
        discount_rate: Discount rate for NPV

    Returns:
        Complete EnhancedProForma model
    """
    nrsf = unit_mix.total_sf

    # Development budget
    budget = DevelopmentBudget()
    budget.land_cost = land_cost
    budget.building_cost = nrsf * construction_cost_psf
    budget.sitework_civil = budget.building_cost * 0.08
    budget.landscaping = 25000
    budget.signage = 15000
    budget.security_gates = 35000

    budget.architecture_engineering = budget.building_cost * 0.04
    budget.permits_fees = budget.building_cost * 0.02
    budget.legal = 25000
    budget.accounting = 15000
    budget.marketing_preleasing = 50000
    budget.development_fee = budget.building_cost * 0.05

    budget.total_soft_costs = (
        budget.architecture_engineering + budget.permits_fees +
        budget.legal + budget.accounting + budget.marketing_preleasing +
        budget.development_fee
    )

    budget.total_hard_costs = (
        budget.building_cost + budget.sitework_civil +
        budget.landscaping + budget.signage + budget.security_gates
    )

    budget.hard_cost_contingency = budget.total_hard_costs * contingency_pct
    budget.soft_cost_contingency = budget.total_soft_costs * contingency_pct

    # Financing costs (construction interest estimate)
    pre_finance_cost = (
        budget.land_cost + budget.total_hard_costs +
        budget.total_soft_costs + budget.hard_cost_contingency + budget.soft_cost_contingency
    )
    budget.construction_interest = pre_finance_cost * ltc * interest_rate * 1.0  # ~1 year avg draw
    budget.loan_fees = pre_finance_cost * ltc * 0.01  # 1% loan fee

    budget.calculate_totals(nrsf)

    # Financing structure
    financing = FinancingStructure()
    financing.construction_ltc = ltc
    financing.construction_loan_amount = budget.total_development_cost * ltc
    financing.construction_rate = interest_rate + 0.015  # Construction typically higher

    financing.permanent_loan_amount = budget.total_development_cost * ltc
    financing.permanent_ltv = ltc
    financing.permanent_rate = interest_rate
    financing.permanent_term_years = loan_term_years
    financing.permanent_amort_years = amort_years
    financing.calculate_permanent_payment()

    # Project monthly cash flows
    monthly_cfs = project_monthly_cash_flows(
        unit_mix=unit_mix,
        development_budget=budget,
        financing=financing,
        months_to_stabilization=months_to_stabilization,
        stabilized_occupancy=stabilized_occupancy,
        annual_rate_growth=annual_rate_growth,
        annual_expense_growth=annual_expense_growth,
    )

    # Summarize annually
    loan_balance = financing.permanent_loan_amount * 0.90  # Approx
    annual_summaries = summarize_annual(monthly_cfs, exit_cap_rate, loan_balance)

    # Calculate return metrics
    metrics = calculate_return_metrics(
        annual_summaries=annual_summaries,
        development_budget=budget,
        financing=financing,
        exit_cap_rate=exit_cap_rate,
        discount_rate=discount_rate,
    )

    # Assemble pro forma
    proforma = EnhancedProForma(
        project_name=project_name,
        address=address,
        analysis_date=datetime.now().strftime("%Y-%m-%d"),
        unit_mix=unit_mix,
        nrsf=nrsf,
        development_budget=budget,
        financing=financing,
        months_to_stabilization=months_to_stabilization,
        stabilized_occupancy=stabilized_occupancy,
        annual_rate_growth=annual_rate_growth,
        annual_expense_growth=annual_expense_growth,
        exit_cap_rate=exit_cap_rate,
        discount_rate=discount_rate,
        monthly_cash_flows=monthly_cfs,
        annual_summaries=annual_summaries,
        metrics=metrics,
    )

    return proforma


# ============================================================================
# HELPER: CREATE DEFAULT UNIT MIX
# ============================================================================

def create_default_unit_mix(
    target_nrsf: int,
    avg_rate_psf: float = 1.25,
    cc_percentage: float = 40.0,
    market_rates: Optional[Dict[str, float]] = None
) -> UnitMix:
    """
    Create a default unit mix based on target NRSF.

    Args:
        target_nrsf: Target net rentable square feet
        avg_rate_psf: Average market rate per SF
        cc_percentage: Percentage of SF to be climate controlled
        market_rates: Optional dict of market rates by unit size

    Returns:
        Configured UnitMix
    """
    # Default rate multipliers by size (relative to avg)
    # Smaller units command higher $/SF, larger units lower
    size_multipliers = {
        "5x5": 1.60,
        "5x10": 1.35,
        "10x10": 1.15,
        "10x15": 1.00,
        "10x20": 0.90,
        "10x30": 0.80,
    }

    # Default mix distribution (% of total units)
    mix_distribution = {
        "5x5": 0.08,
        "5x10": 0.22,
        "10x10": 0.35,
        "10x15": 0.18,
        "10x20": 0.12,
        "10x30": 0.05,
    }

    size_sf = {
        "5x5": 25,
        "5x10": 50,
        "10x10": 100,
        "10x15": 150,
        "10x20": 200,
        "10x30": 300,
    }

    # Calculate weighted average SF per unit
    avg_sf = sum(size_sf[s] * mix_distribution[s] for s in size_sf)
    total_units = int(target_nrsf / avg_sf)

    # CC premium
    cc_premium = 1.20  # 20% premium for climate controlled

    units = []
    cc_sf_target = target_nrsf * (cc_percentage / 100)
    cc_sf_assigned = 0

    for size, pct in mix_distribution.items():
        unit_count = max(1, int(total_units * pct))
        sf = size_sf[size]

        # Determine if CC or non-CC
        # Assign CC to smaller units first (more valuable)
        is_cc = cc_sf_assigned < cc_sf_target and sf <= 150

        if is_cc:
            cc_sf_assigned += sf * unit_count

        # Calculate rate
        base_rate_psf = avg_rate_psf * size_multipliers[size]
        if is_cc:
            base_rate_psf *= cc_premium

        monthly_rate = base_rate_psf * sf

        # Override with market rates if provided
        if market_rates:
            rate_key = f"rate_{'cc' if is_cc else 'noncc'}-{size}"
            if rate_key in market_rates and market_rates[rate_key] > 0:
                monthly_rate = market_rates[rate_key] * sf

        unit = UnitType(
            size=size,
            sf_per_unit=sf,
            unit_count=unit_count,
            climate_controlled=is_cc,
            monthly_rate=monthly_rate,
            lease_up_modifier=get_unit_type_lease_up_modifier(size, is_cc),
        )
        units.append(unit)

    return UnitMix(units=units)


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    print("=== Enhanced Financial Model V2 Test ===\n")

    # Create unit mix for 60,000 SF facility
    unit_mix = create_default_unit_mix(
        target_nrsf=60000,
        avg_rate_psf=1.25,
        cc_percentage=40.0
    )

    print(f"Unit Mix Summary:")
    print(f"  Total SF: {unit_mix.total_sf:,}")
    print(f"  Total Units: {unit_mix.total_units}")
    print(f"  Monthly GPR: ${unit_mix.total_monthly_gpr:,.0f}")
    print(f"  Avg Rate/SF: ${unit_mix.weighted_avg_rate_psf:.2f}")
    print(f"  CC %: {unit_mix.cc_percentage:.1f}%")
    print()

    # Build pro forma
    proforma = build_enhanced_pro_forma(
        project_name="Test Facility",
        address="123 Main St, Nashville, TN",
        unit_mix=unit_mix,
        land_cost=800000,
        construction_cost_psf=85,
        ltc=0.70,
        interest_rate=0.065,
        months_to_stabilization=36,
        stabilized_occupancy=92.0,
    )

    print(f"Development Budget:")
    print(f"  Land: ${proforma.development_budget.land_cost:,.0f}")
    print(f"  Hard Costs: ${proforma.development_budget.total_hard_costs:,.0f}")
    print(f"  Soft Costs: ${proforma.development_budget.total_soft_costs:,.0f}")
    print(f"  Total: ${proforma.development_budget.total_development_cost:,.0f}")
    print(f"  Cost/SF: ${proforma.development_budget.cost_per_sf:.2f}")
    print()

    print(f"Financing:")
    print(f"  Loan Amount: ${proforma.financing.permanent_loan_amount:,.0f}")
    print(f"  Monthly Payment: ${proforma.financing.monthly_debt_service:,.0f}")
    print(f"  Annual Debt Service: ${proforma.financing.annual_debt_service:,.0f}")
    print()

    print(f"Return Metrics:")
    print(f"  Development Yield: {proforma.metrics.development_yield*100:.2f}%")
    print(f"  DSCR (Stabilized): {proforma.metrics.dscr_stabilized:.2f}x")
    print(f"  Break-even Occ: {proforma.metrics.break_even_occupancy:.1f}%")
    print(f"  IRR (7-year): {proforma.metrics.irr_7yr:.2f}%")
    print(f"  IRR (10-year): {proforma.metrics.irr_10yr:.2f}%")
    print(f"  NPV (7-year): ${proforma.metrics.npv_7yr:,.0f}")
    print(f"  Equity Multiple (7-year): {proforma.metrics.equity_multiple_7yr:.2f}x")
    print()

    print(f"Annual Summaries:")
    for summary in proforma.annual_summaries:
        print(f"  Year {summary.year}: NOI ${summary.net_operating_income:,.0f} | "
              f"Occ {summary.avg_occupancy_pct:.1f}% | CF ${summary.cash_flow_before_tax:,.0f}")
