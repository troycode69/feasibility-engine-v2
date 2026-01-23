"""
Financial Model for Self-Storage Feasibility Analysis

This module performs comprehensive financial analysis:
- Pro forma income & expense projections
- IRR (Internal Rate of Return)
- NPV (Net Present Value)
- Cap Rate calculations
- Break-even analysis
- Debt service coverage ratio (DSCR)
- Cash-on-cash return

Based on industry-standard self-storage underwriting methods.
"""

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field


@dataclass
class DevelopmentCosts:
    """All development costs"""
    land_cost: float = 0
    hard_costs: float = 0  # Construction
    soft_costs: float = 0  # A&E, permits, legal, etc.
    contingency: float = 0
    financing_costs: float = 0
    total_cost: float = 0

    def calculate_total(self):
        """Calculate total development cost"""
        self.total_cost = (
            self.land_cost +
            self.hard_costs +
            self.soft_costs +
            self.contingency +
            self.financing_costs
        )
        return self.total_cost


@dataclass
class FinancingTerms:
    """Loan terms"""
    loan_amount: float = 0
    interest_rate: float = 0  # Annual rate (e.g., 0.065 for 6.5%)
    term_years: int = 10
    amortization_years: int = 25
    monthly_payment: float = 0
    annual_debt_service: float = 0

    def calculate_payments(self):
        """Calculate loan payments"""
        if self.loan_amount == 0 or self.interest_rate == 0:
            return

        # Monthly payment calculation
        monthly_rate = self.interest_rate / 12
        n_payments = self.amortization_years * 12

        if monthly_rate == 0:
            self.monthly_payment = self.loan_amount / n_payments
        else:
            self.monthly_payment = self.loan_amount * (
                monthly_rate * (1 + monthly_rate) ** n_payments
            ) / ((1 + monthly_rate) ** n_payments - 1)

        self.annual_debt_service = self.monthly_payment * 12

        return self.monthly_payment


@dataclass
class StabilizedOperations:
    """Stabilized year operating assumptions"""
    gross_potential_revenue: float = 0
    vacancy_loss: float = 0  # Assume 5% at stabilization
    effective_gross_income: float = 0

    # Operating expenses
    property_taxes: float = 0
    insurance: float = 0
    utilities: float = 0
    management_fee: float = 0
    onsite_labor: float = 0
    marketing: float = 0
    maintenance_repairs: float = 0
    administrative: float = 0
    total_operating_expenses: float = 0

    net_operating_income: float = 0

    def calculate_noi(self):
        """Calculate NOI"""
        self.effective_gross_income = self.gross_potential_revenue - self.vacancy_loss

        self.total_operating_expenses = (
            self.property_taxes +
            self.insurance +
            self.utilities +
            self.management_fee +
            self.onsite_labor +
            self.marketing +
            self.maintenance_repairs +
            self.administrative
        )

        self.net_operating_income = self.effective_gross_income - self.total_operating_expenses

        return self.net_operating_income


@dataclass
class FinancialMetrics:
    """Key financial metrics"""
    cap_rate: float = 0  # Capitalization rate
    cash_on_cash_return: float = 0  # Year 1 cash return / equity invested
    dscr: float = 0  # Debt Service Coverage Ratio
    break_even_occupancy: float = 0  # % occupancy to cover debt service
    stabilized_occupancy: float = 95.0  # Target stabilized occupancy

    irr_10yr: float = 0  # 10-year IRR
    npv_10yr: float = 0  # 10-year NPV
    equity_multiple: float = 0  # Total cash returned / equity invested


@dataclass
class ProForma:
    """Complete pro forma financial model"""
    project_name: str = ""
    nrsf: int = 0
    analysis_date: str = ""

    # Inputs
    development_costs: DevelopmentCosts = field(default_factory=DevelopmentCosts)
    financing: FinancingTerms = field(default_factory=FinancingTerms)
    stabilized: StabilizedOperations = field(default_factory=StabilizedOperations)

    # Outputs
    metrics: FinancialMetrics = field(default_factory=FinancialMetrics)

    # Multi-year projections
    years_to_stabilization: int = 3
    occupancy_curve: List[float] = field(default_factory=list)  # Monthly occupancy %
    annual_noi: List[float] = field(default_factory=list)  # NOI for each year
    annual_cash_flow: List[float] = field(default_factory=list)  # After debt service


# ============================================================================
# CALCULATION FUNCTIONS
# ============================================================================

def calculate_cap_rate(noi: float, property_value: float) -> float:
    """
    Calculate capitalization rate.

    Cap Rate = NOI / Property Value

    Args:
        noi: Stabilized Net Operating Income
        property_value: Total development cost or market value

    Returns:
        Cap rate as decimal (e.g., 0.075 for 7.5%)
    """
    if property_value == 0:
        return 0.0

    return noi / property_value


def calculate_dscr(noi: float, annual_debt_service: float) -> float:
    """
    Calculate Debt Service Coverage Ratio.

    DSCR = NOI / Annual Debt Service

    Lenders typically require DSCR > 1.25

    Args:
        noi: Net Operating Income
        annual_debt_service: Annual loan payment

    Returns:
        DSCR (e.g., 1.35)
    """
    if annual_debt_service == 0:
        return 999.0  # No debt = infinite coverage

    return noi / annual_debt_service


def calculate_break_even_occupancy(total_operating_expenses: float,
                                   annual_debt_service: float,
                                   gross_potential_revenue: float) -> float:
    """
    Calculate break-even occupancy %.

    Break-even = (Operating Expenses + Debt Service) / Gross Potential Revenue

    Args:
        total_operating_expenses: Annual operating expenses
        annual_debt_service: Annual loan payment
        gross_potential_revenue: Revenue at 100% occupancy

    Returns:
        Break-even occupancy as % (e.g., 62.5)
    """
    if gross_potential_revenue == 0:
        return 0.0

    break_even = (total_operating_expenses + annual_debt_service) / gross_potential_revenue * 100

    return break_even


def calculate_cash_on_cash(cash_flow: float, equity_invested: float) -> float:
    """
    Calculate cash-on-cash return.

    Cash-on-Cash = Annual Cash Flow / Equity Invested

    Args:
        cash_flow: Pre-tax cash flow (NOI - debt service)
        equity_invested: Total equity invested (not loan proceeds)

    Returns:
        Cash-on-cash return as decimal (e.g., 0.085 for 8.5%)
    """
    if equity_invested == 0:
        return 0.0

    return cash_flow / equity_invested


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

    # Newton's method for finding IRR
    rate = initial_guess
    max_iterations = 100
    tolerance = 0.0001

    for iteration in range(max_iterations):
        # Calculate NPV at current rate
        npv = sum(cf / ((1 + rate) ** t) for t, cf in enumerate(cash_flows))

        # Calculate derivative (dNPV/dr)
        d_npv = sum(-t * cf / ((1 + rate) ** (t + 1)) for t, cf in enumerate(cash_flows))

        if abs(d_npv) < 1e-10:  # Avoid division by zero
            break

        # Newton's method update
        new_rate = rate - npv / d_npv

        # Check convergence
        if abs(new_rate - rate) < tolerance:
            return new_rate

        rate = new_rate

        # Bounds check
        if rate < -0.99 or rate > 10.0:  # Unrealistic IRR
            return 0.0

    return rate if abs(npv) < 1000 else 0.0  # Return 0 if didn't converge


def calculate_npv(cash_flows: List[float], discount_rate: float = 0.10) -> float:
    """
    Calculate Net Present Value.

    NPV = Sum of (Cash Flow / (1 + r)^t) for each year t

    Args:
        cash_flows: List of annual cash flows (year 0 = initial investment as negative)
        discount_rate: Discount rate (e.g., 0.10 for 10%)

    Returns:
        NPV in dollars
    """
    if len(cash_flows) < 2:
        return 0.0

    npv = 0.0
    for year, cf in enumerate(cash_flows):
        npv += cf / ((1 + discount_rate) ** year)

    return npv


def project_annual_noi(stabilized_noi: float, occupancy_curve: List[float],
                      stabilized_occupancy: float = 95.0, growth_rate: float = 0.02) -> List[float]:
    """
    Project NOI for each year based on occupancy ramp-up.

    Args:
        stabilized_noi: Stabilized NOI at target occupancy
        occupancy_curve: List of monthly occupancy percentages
        stabilized_occupancy: Target stabilized occupancy (e.g., 95.0)
        growth_rate: Annual revenue growth rate after stabilization (e.g., 0.02 for 2%)

    Returns:
        List of annual NOI values
    """
    annual_noi = []

    # Convert monthly occupancy to annual averages
    months_per_year = 12
    n_years = len(occupancy_curve) // months_per_year + 1

    for year in range(n_years):
        start_month = year * months_per_year
        end_month = min(start_month + months_per_year, len(occupancy_curve))

        if start_month >= len(occupancy_curve):
            # Beyond occupancy curve - assume stabilized with growth
            years_beyond = year - (len(occupancy_curve) // months_per_year)
            noi = stabilized_noi * ((1 + growth_rate) ** years_beyond)
        else:
            # Average occupancy for the year
            year_occupancies = occupancy_curve[start_month:end_month]
            avg_occupancy = sum(year_occupancies) / len(year_occupancies)

            # NOI proportional to occupancy vs stabilized
            noi = stabilized_noi * (avg_occupancy / stabilized_occupancy)

        annual_noi.append(noi)

    return annual_noi


def build_pro_forma(project_name: str, nrsf: int,
                   development_costs: Dict,
                   financing_terms: Dict,
                   revenue_assumptions: Dict,
                   expense_assumptions: Dict,
                   occupancy_curve: List[float],
                   exit_cap_rate: float = 0.07,
                   holding_period: int = 10) -> ProForma:
    """
    Build complete pro forma financial model.

    Args:
        project_name: Name of the project
        nrsf: Net Rentable Square Feet
        development_costs: Dict with land_cost, hard_costs, soft_costs, etc.
        financing_terms: Dict with loan_amount, interest_rate, term_years, amortization_years
        revenue_assumptions: Dict with avg_rate_psf, stabilized_occupancy
        expense_assumptions: Dict with expense ratios (as % of GPR)
        occupancy_curve: List of monthly occupancy percentages
        exit_cap_rate: Cap rate for exit value calculation
        holding_period: Years until sale

    Returns:
        Complete ProForma object
    """
    from datetime import datetime

    proforma = ProForma()
    proforma.project_name = project_name
    proforma.nrsf = nrsf
    proforma.analysis_date = datetime.now().strftime("%Y-%m-%d")

    # Development costs
    proforma.development_costs = DevelopmentCosts(
        land_cost=development_costs.get("land_cost", 0),
        hard_costs=development_costs.get("hard_costs", 0),
        soft_costs=development_costs.get("soft_costs", 0),
        contingency=development_costs.get("contingency", 0),
        financing_costs=development_costs.get("financing_costs", 0)
    )
    proforma.development_costs.calculate_total()

    # Financing
    proforma.financing = FinancingTerms(
        loan_amount=financing_terms.get("loan_amount", 0),
        interest_rate=financing_terms.get("interest_rate", 0),
        term_years=financing_terms.get("term_years", 10),
        amortization_years=financing_terms.get("amortization_years", 25)
    )
    proforma.financing.calculate_payments()

    # Stabilized operations
    avg_rate_psf = revenue_assumptions.get("avg_rate_psf", 0)
    stabilized_occ = revenue_assumptions.get("stabilized_occupancy", 95.0)

    gpr = nrsf * avg_rate_psf * 12  # Annual GPR at 100% occupancy
    vacancy_rate = 1.0 - (stabilized_occ / 100.0)

    proforma.stabilized = StabilizedOperations(
        gross_potential_revenue=gpr,
        vacancy_loss=gpr * vacancy_rate
    )

    # Operating expenses
    proforma.stabilized.property_taxes = gpr * expense_assumptions.get("property_taxes", 0.07)
    proforma.stabilized.insurance = gpr * expense_assumptions.get("insurance", 0.015)
    proforma.stabilized.utilities = gpr * expense_assumptions.get("utilities", 0.035)
    proforma.stabilized.management_fee = gpr * expense_assumptions.get("management_fee", 0.06)
    proforma.stabilized.onsite_labor = gpr * expense_assumptions.get("onsite_labor", 0.10)
    proforma.stabilized.marketing = gpr * expense_assumptions.get("marketing", 0.04)
    proforma.stabilized.maintenance_repairs = gpr * expense_assumptions.get("maintenance_repairs", 0.025)
    proforma.stabilized.administrative = gpr * expense_assumptions.get("administrative", 0.015)

    proforma.stabilized.calculate_noi()

    # Calculate key metrics
    proforma.metrics.cap_rate = calculate_cap_rate(
        proforma.stabilized.net_operating_income,
        proforma.development_costs.total_cost
    )

    proforma.metrics.dscr = calculate_dscr(
        proforma.stabilized.net_operating_income,
        proforma.financing.annual_debt_service
    )

    proforma.metrics.break_even_occupancy = calculate_break_even_occupancy(
        proforma.stabilized.total_operating_expenses,
        proforma.financing.annual_debt_service,
        proforma.stabilized.gross_potential_revenue
    )

    proforma.metrics.stabilized_occupancy = stabilized_occ

    # Project multi-year cash flows
    proforma.occupancy_curve = occupancy_curve
    proforma.annual_noi = project_annual_noi(
        proforma.stabilized.net_operating_income,
        occupancy_curve,
        stabilized_occ
    )

    # Calculate annual cash flows (NOI - debt service)
    proforma.annual_cash_flow = []
    for noi in proforma.annual_noi:
        cash_flow = noi - proforma.financing.annual_debt_service
        proforma.annual_cash_flow.append(cash_flow)

    # Calculate IRR and NPV
    equity_invested = proforma.development_costs.total_cost - proforma.financing.loan_amount

    # Build cash flow array for IRR/NPV (Year 0 = -equity, Years 1-N = cash flows, Year N includes exit)
    cash_flows = [-equity_invested]  # Initial investment

    for year in range(holding_period):
        if year < len(proforma.annual_cash_flow):
            cf = proforma.annual_cash_flow[year]
        else:
            # Beyond projection - assume stabilized
            cf = proforma.annual_cash_flow[-1]

        # Add exit value in final year
        if year == holding_period - 1:
            # Exit value = NOI / Exit Cap Rate
            exit_noi = proforma.annual_noi[year] if year < len(proforma.annual_noi) else proforma.stabilized.net_operating_income
            exit_value = exit_noi / exit_cap_rate
            # Subtract remaining loan balance (simplified - assume 70% of original)
            loan_balance = proforma.financing.loan_amount * 0.70
            exit_proceeds = exit_value - loan_balance
            cf += exit_proceeds

        cash_flows.append(cf)

    proforma.metrics.irr_10yr = calculate_irr(cash_flows) * 100  # Convert to percentage
    proforma.metrics.npv_10yr = calculate_npv(cash_flows, discount_rate=0.10)

    # Cash-on-cash return (Year 1)
    if len(proforma.annual_cash_flow) > 0:
        proforma.metrics.cash_on_cash_return = calculate_cash_on_cash(
            proforma.annual_cash_flow[0],
            equity_invested
        ) * 100  # Convert to percentage

    # Equity multiple
    total_cash_returned = sum(cash_flows[1:])  # Exclude initial investment
    proforma.metrics.equity_multiple = total_cash_returned / equity_invested if equity_invested > 0 else 0

    return proforma


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    print("=== Financial Model Test ===\n")

    # Test with 60,000 NRSF facility
    try:
        from benchmarks import get_occupancy_curve, calculate_construction_cost, get_expense_ratio
    except:
        from src.benchmarks import get_occupancy_curve, calculate_construction_cost, get_expense_ratio

    nrsf = 60000
    state = "TN"

    # Development costs
    construction = calculate_construction_cost(nrsf, state, "mid", "mixed")
    land_cost = 800000  # $800k land

    development_costs = {
        "land_cost": land_cost,
        "hard_costs": construction["hard_cost"],
        "soft_costs": construction["soft_cost"],
        "contingency": 0,
        "financing_costs": 150000
    }

    # Financing: 75% LTC
    total_cost = sum(development_costs.values())
    loan_amount = total_cost * 0.75

    financing_terms = {
        "loan_amount": loan_amount,
        "interest_rate": 0.065,  # 6.5%
        "term_years": 10,
        "amortization_years": 25
    }

    # Revenue assumptions
    revenue_assumptions = {
        "avg_rate_psf": 1.20,  # $1.20/SF/month average
        "stabilized_occupancy": 95.0
    }

    # Expenses
    expense_assumptions = get_expense_ratio(nrsf)

    # Occupancy curve
    occ_curve = get_occupancy_curve("standard")

    # Build pro forma
    proforma = build_pro_forma(
        project_name="Test Storage Facility",
        nrsf=nrsf,
        development_costs=development_costs,
        financing_terms=financing_terms,
        revenue_assumptions=revenue_assumptions,
        expense_assumptions=expense_assumptions,
        occupancy_curve=occ_curve["occupancy_pct"],
        exit_cap_rate=0.07,
        holding_period=10
    )

    print(f"Project: {proforma.project_name}")
    print(f"Size: {proforma.nrsf:,} NRSF")
    print(f"Analysis Date: {proforma.analysis_date}\n")

    print("=== DEVELOPMENT COSTS ===")
    print(f"Land: ${proforma.development_costs.land_cost:,.0f}")
    print(f"Hard Costs: ${proforma.development_costs.hard_costs:,.0f}")
    print(f"Soft Costs: ${proforma.development_costs.soft_costs:,.0f}")
    print(f"Financing Costs: ${proforma.development_costs.financing_costs:,.0f}")
    print(f"TOTAL: ${proforma.development_costs.total_cost:,.0f}\n")

    print("=== FINANCING ===")
    print(f"Loan Amount: ${proforma.financing.loan_amount:,.0f}")
    print(f"Interest Rate: {proforma.financing.interest_rate*100:.2f}%")
    print(f"Term: {proforma.financing.term_years} years / {proforma.financing.amortization_years} amortization")
    print(f"Monthly Payment: ${proforma.financing.monthly_payment:,.0f}")
    print(f"Annual Debt Service: ${proforma.financing.annual_debt_service:,.0f}\n")

    print("=== STABILIZED OPERATIONS ===")
    print(f"Gross Potential Revenue: ${proforma.stabilized.gross_potential_revenue:,.0f}")
    print(f"Vacancy Loss (5%): $({proforma.stabilized.vacancy_loss:,.0f})")
    print(f"Effective Gross Income: ${proforma.stabilized.effective_gross_income:,.0f}\n")

    print("Operating Expenses:")
    print(f"  Property Taxes: ${proforma.stabilized.property_taxes:,.0f}")
    print(f"  Insurance: ${proforma.stabilized.insurance:,.0f}")
    print(f"  Utilities: ${proforma.stabilized.utilities:,.0f}")
    print(f"  Management Fee: ${proforma.stabilized.management_fee:,.0f}")
    print(f"  Onsite Labor: ${proforma.stabilized.onsite_labor:,.0f}")
    print(f"  Marketing: ${proforma.stabilized.marketing:,.0f}")
    print(f"  Maintenance: ${proforma.stabilized.maintenance_repairs:,.0f}")
    print(f"  Administrative: ${proforma.stabilized.administrative:,.0f}")
    print(f"  TOTAL OPEX: ${proforma.stabilized.total_operating_expenses:,.0f}\n")

    print(f"Net Operating Income: ${proforma.stabilized.net_operating_income:,.0f}\n")

    print("=== KEY METRICS ===")
    print(f"Cap Rate: {proforma.metrics.cap_rate*100:.2f}%")
    print(f"DSCR: {proforma.metrics.dscr:.2f}x")
    print(f"Break-Even Occupancy: {proforma.metrics.break_even_occupancy:.1f}%")
    print(f"Cash-on-Cash Return (Yr 1): {proforma.metrics.cash_on_cash_return:.2f}%")
    print(f"10-Year IRR: {proforma.metrics.irr_10yr:.2f}%")
    print(f"10-Year NPV: ${proforma.metrics.npv_10yr:,.0f}")
    print(f"Equity Multiple: {proforma.metrics.equity_multiple:.2f}x\n")

    print("=== MULTI-YEAR PROJECTIONS ===")
    for year, (noi, cf) in enumerate(zip(proforma.annual_noi[:5], proforma.annual_cash_flow[:5])):
        print(f"Year {year+1}: NOI ${noi:,.0f} | Cash Flow ${cf:,.0f}")
