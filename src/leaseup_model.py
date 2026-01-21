"""
7-Year Self-Storage Lease-Up Model
Based on cohort-based attrition modeling with seasonality adjustments
"""
import pandas as pd
import numpy as np
import json
import os
from datetime import datetime
from dateutil.relativedelta import relativedelta

class LeaseUpModel:
    def __init__(self):
        """Initialize with attrition curves and seasonality data"""
        self.load_base_data()

    def load_base_data(self):
        """Load attrition curves and seasonality from JSON"""
        base_dir = os.path.dirname(os.path.abspath(__file__))

        # Load attrition curves
        attrition_path = os.path.join(base_dir, '../data/attrition_curves.json')
        with open(attrition_path, 'r') as f:
            attrition_data = json.load(f)

        # Convert to DataFrame for easy lookup
        self.attrition_df = pd.DataFrame(attrition_data)

        # Load seasonality
        seasonality_path = os.path.join(base_dir, '../data/seasonality_factors.json')
        with open(seasonality_path, 'r') as f:
            self.seasonality = json.load(f)

        # Convert to DataFrames
        self.revenue_seasonality = pd.DataFrame(self.seasonality['revenue']).set_index('month')
        self.expense_seasonality = pd.DataFrame(self.seasonality['expense']).set_index('month')

    def get_vacate_rate(self, rental_month, vacate_month):
        """Get vacate rate for a specific rental month -> vacate month combination"""
        match = self.attrition_df[
            (self.attrition_df['rental_month'] == rental_month) &
            (self.attrition_df['vacate_month'] == vacate_month)
        ]
        if len(match) > 0:
            return match.iloc[0]['vacate_rate']
        return 0.0

    def calculate_los(self, rental_month, current_month):
        """Calculate Length of Stay (LOS) in months"""
        los = current_month - rental_month
        if los < 0:
            los += 12  # Wrap around year
        return los

    def generate_projection(self,
                          total_sf,
                          total_units,
                          start_date,
                          starting_rate_psf,  # Annual rate $/SF
                          stabilized_occupancy=0.90,
                          months_to_stabilization=24,
                          rate_growth_annual=0.04,
                          land_cost=0,
                          construction_cost_psf=65,
                          loan_amount=0,
                          interest_rate=0.0625,
                          loan_term_years=30):
        """
        Generate 7-year (84-month) operating projection

        Parameters:
        - total_sf: Net Rentable Area
        - total_units: Total unit count
        - start_date: Projection start date (datetime)
        - starting_rate_psf: Starting annual rate per SF
        - stabilized_occupancy: Target stabilization (default 90%)
        - months_to_stabilization: Months to reach stabilization (default 24)
        - rate_growth_annual: Annual rate growth % (default 4%)
        - land_cost: Land acquisition cost
        - construction_cost_psf: Construction cost per SF
        - loan_amount: Loan amount (if 0, will calculate)
        - interest_rate: Annual interest rate
        - loan_term_years: Loan term in years

        Returns: DataFrame with monthly projections
        """

        # Initialize projection DataFrame
        months = 84  # 7 years
        dates = [start_date + relativedelta(months=i) for i in range(months)]

        proj = pd.DataFrame({
            'date': dates,
            'month_num': range(1, months + 1)
        })

        # Calculate total development cost
        total_cost = land_cost + (construction_cost_psf * total_sf)

        # Calculate loan parameters
        if loan_amount == 0:
            loan_amount = total_cost * 0.70  # 70% LTV default

        monthly_rate = interest_rate / 12
        num_payments = loan_term_years * 12
        if monthly_rate > 0:
            monthly_payment = loan_amount * (monthly_rate * (1 + monthly_rate)**num_payments) / ((1 + monthly_rate)**num_payments - 1)
        else:
            monthly_payment = loan_amount / num_payments

        # Initialize columns
        proj['target_occupancy'] = 0.0
        proj['rentals'] = 0.0
        proj['vacates'] = 0.0
        proj['net_rentals'] = 0.0
        proj['ending_occupied_units'] = 0.0
        proj['ending_occupied_sf'] = 0.0
        proj['occupancy_pct'] = 0.0
        proj['avg_rent_rate'] = starting_rate_psf
        proj['rental_income'] = 0.0
        proj['discounts'] = 0.0
        proj['writeoffs'] = 0.0
        proj['net_rental_income'] = 0.0
        proj['ancillary_income'] = 0.0
        proj['total_revenue'] = 0.0

        # Expense lines
        proj['payroll'] = 0.0
        proj['utilities'] = 0.0
        proj['operating_expenses'] = 0.0
        proj['landscaping'] = 0.0
        proj['repairs_maintenance'] = 0.0
        proj['marketing'] = 0.0
        proj['property_taxes'] = 0.0
        proj['insurance'] = 0.0
        proj['management_fee'] = 0.0
        proj['total_expenses'] = 0.0
        proj['noi'] = 0.0

        # Debt service
        proj['debt_service'] = monthly_payment
        proj['interest_payment'] = 0.0
        proj['principal_payment'] = 0.0
        proj['loan_balance'] = loan_amount
        proj['levered_cash_flow'] = 0.0
        proj['dscr'] = 0.0

        # Track rental cohorts for attrition modeling
        rental_cohorts = {}  # {month_num: {'units': X, 'rental_month': M}}

        avg_unit_sf = total_sf / total_units

        # Annual expense assumptions (will be seasonalized)
        annual_payroll = 72000  # $6k/month base
        annual_utilities_psf = 0.85  # $/SF/year
        annual_operating_psf = 1.20
        annual_landscaping = 25000
        annual_rm_psf = 0.55
        annual_marketing = 12000
        annual_property_tax_psf = 1.20
        annual_insurance_psf = 0.27
        management_fee_pct = 0.06  # 6% of revenue

        # Lease-up curve (S-curve to stabilization)
        for i in range(len(proj)):
            month_num = proj.loc[i, 'month_num']
            current_date = proj.loc[i, 'date']
            calendar_month = current_date.month

            # Target occupancy (S-curve)
            if month_num <= months_to_stabilization:
                # Sigmoid curve
                progress = month_num / months_to_stabilization
                target_occ = stabilized_occupancy * (1 / (1 + np.exp(-10 * (progress - 0.5))))
            else:
                target_occ = stabilized_occupancy

            proj.loc[i, 'target_occupancy'] = target_occ

            # Get seasonality factors
            rev_season = self.revenue_seasonality.loc[calendar_month]
            exp_season = self.expense_seasonality.loc[calendar_month]

            # Calculate required rentals to hit target
            if i == 0:
                beginning_units = 0
                beginning_sf = 0
            else:
                beginning_units = proj.loc[i-1, 'ending_occupied_units']
                beginning_sf = proj.loc[i-1, 'ending_occupied_sf']

            # Calculate vacates from existing cohorts
            total_vacates = 0.0
            for cohort_month, cohort_data in rental_cohorts.items():
                cohort_units = cohort_data['units']
                cohort_rental_month = cohort_data['rental_month']

                # Determine vacate month (current month in year)
                vacate_rate = self.get_vacate_rate(cohort_rental_month, calendar_month)

                # Apply seasonality adjustment to vacates
                vacate_adj = rev_season['vacates_factor']
                cohort_vacates = cohort_units * vacate_rate * vacate_adj
                total_vacates += cohort_vacates

            proj.loc[i, 'vacates'] = total_vacates

            # Calculate required rentals
            target_sf = target_occ * total_sf
            required_rentals_sf = target_sf - (beginning_sf - total_vacates * avg_unit_sf)
            required_rentals_units = max(0, required_rentals_sf / avg_unit_sf)

            # Apply seasonality to rentals
            rental_season_factor = rev_season['rentals_factor'] * 12  # Annualized factor
            actual_rentals = required_rentals_units * rental_season_factor

            proj.loc[i, 'rentals'] = actual_rentals
            proj.loc[i, 'net_rentals'] = actual_rentals - total_vacates
            proj.loc[i, 'ending_occupied_units'] = beginning_units + actual_rentals - total_vacates
            proj.loc[i, 'ending_occupied_sf'] = proj.loc[i, 'ending_occupied_units'] * avg_unit_sf
            proj.loc[i, 'occupancy_pct'] = proj.loc[i, 'ending_occupied_sf'] / total_sf

            # Add this month's rentals as a new cohort
            if actual_rentals > 0:
                rental_cohorts[month_num] = {
                    'units': actual_rentals,
                    'rental_month': calendar_month
                }

            # Update rental cohorts (remove fully churned)
            rental_cohorts = {k: v for k, v in rental_cohorts.items() if v['units'] > 0.01}

            # Calculate rent rate with growth
            years_elapsed = month_num / 12
            current_rate = starting_rate_psf * (1 + rate_growth_annual)**years_elapsed
            proj.loc[i, 'avg_rent_rate'] = current_rate

            # Revenue calculations
            monthly_rate = current_rate / 12
            occupied_sf = proj.loc[i, 'ending_occupied_sf']
            gross_rental = occupied_sf * monthly_rate

            # Discounts and writeoffs
            discount_pct = 0.025 + (rev_season['discount_factor'] - 1) * 0.01  # Base 2.5% + seasonal adj
            writeoff_pct = 0.01

            proj.loc[i, 'rental_income'] = gross_rental
            proj.loc[i, 'discounts'] = -gross_rental * discount_pct
            proj.loc[i, 'writeoffs'] = -gross_rental * writeoff_pct
            proj.loc[i, 'net_rental_income'] = gross_rental * (1 - discount_pct - writeoff_pct)

            # Ancillary income (insurance, fees, etc.) - 10% of rental income
            proj.loc[i, 'ancillary_income'] = proj.loc[i, 'net_rental_income'] * 0.10
            proj.loc[i, 'total_revenue'] = proj.loc[i, 'net_rental_income'] + proj.loc[i, 'ancillary_income']

            # Expenses with seasonality
            proj.loc[i, 'payroll'] = annual_payroll / 12
            proj.loc[i, 'utilities'] = (annual_utilities_psf * total_sf / 12) * \
                                       (exp_season['electric_factor'] + exp_season['gas_factor']) * 6
            proj.loc[i, 'operating_expenses'] = (annual_operating_psf * total_sf / 12)
            proj.loc[i, 'landscaping'] = (annual_landscaping / 12) * exp_season['landscape_factor'] * 12
            proj.loc[i, 'repairs_maintenance'] = (annual_rm_psf * total_sf / 12)
            proj.loc[i, 'marketing'] = (annual_marketing / 12) * exp_season['marketing_factor'] * 12
            proj.loc[i, 'property_taxes'] = (annual_property_tax_psf * total_sf / 12)
            proj.loc[i, 'insurance'] = (annual_insurance_psf * total_sf / 12)
            proj.loc[i, 'management_fee'] = proj.loc[i, 'total_revenue'] * management_fee_pct

            proj.loc[i, 'total_expenses'] = (
                proj.loc[i, 'payroll'] +
                proj.loc[i, 'utilities'] +
                proj.loc[i, 'operating_expenses'] +
                proj.loc[i, 'landscaping'] +
                proj.loc[i, 'repairs_maintenance'] +
                proj.loc[i, 'marketing'] +
                proj.loc[i, 'property_taxes'] +
                proj.loc[i, 'insurance'] +
                proj.loc[i, 'management_fee']
            )

            proj.loc[i, 'noi'] = proj.loc[i, 'total_revenue'] - proj.loc[i, 'total_expenses']

            # Debt service
            if i == 0:
                beginning_balance = loan_amount
            else:
                beginning_balance = proj.loc[i-1, 'loan_balance']

            interest = beginning_balance * monthly_rate
            principal = monthly_payment - interest
            ending_balance = beginning_balance - principal

            proj.loc[i, 'interest_payment'] = interest
            proj.loc[i, 'principal_payment'] = principal
            proj.loc[i, 'loan_balance'] = ending_balance
            proj.loc[i, 'levered_cash_flow'] = proj.loc[i, 'noi'] - monthly_payment

            if monthly_payment > 0:
                proj.loc[i, 'dscr'] = proj.loc[i, 'noi'] / monthly_payment
            else:
                proj.loc[i, 'dscr'] = 0

        return proj

    def generate_summary(self, projection_df):
        """Generate annual summary from monthly projections"""
        proj = projection_df.copy()
        proj['year'] = ((proj['month_num'] - 1) // 12) + 1

        annual_summary = proj.groupby('year').agg({
            'total_revenue': 'sum',
            'total_expenses': 'sum',
            'noi': 'sum',
            'debt_service': 'sum',
            'levered_cash_flow': 'sum',
            'occupancy_pct': 'mean',
            'avg_rent_rate': 'mean'
        }).reset_index()

        annual_summary.columns = [
            'Year',
            'Total Revenue',
            'Total Expenses',
            'NOI',
            'Debt Service',
            'Levered Cash Flow',
            'Avg Occupancy %',
            'Avg Rent Rate'
        ]

        return annual_summary
