"""
Enhanced 7-Year Self-Storage Lease-Up Model
Matches Excel "7 Year Projection" sheet with detailed revenue/expense breakouts
"""
import pandas as pd
import numpy as np
import json
import os
from datetime import datetime
from dateutil.relativedelta import relativedelta

class EnhancedLeaseUpModel:
    def __init__(self):
        """Initialize with attrition table, expense benchmarks, and seasonality"""
        self.load_data()

    def load_data(self):
        """Load all required data files"""
        base_dir = os.path.dirname(os.path.abspath(__file__))

        # Load attrition table
        attrition_path = os.path.join(base_dir, '../data/attrition_table.json')
        with open(attrition_path, 'r') as f:
            attrition_data = json.load(f)
        self.attrition_df = pd.DataFrame(attrition_data)

        # Load expense benchmarks
        benchmarks_path = os.path.join(base_dir, '../data/expense_benchmarks.json')
        with open(benchmarks_path, 'r') as f:
            self.benchmarks = json.load(f)

        # Load seasonality
        seasonality_path = os.path.join(base_dir, '../data/seasonality_factors.json')
        with open(seasonality_path, 'r') as f:
            self.seasonality = json.load(f)

        self.revenue_seasonality = pd.DataFrame(self.seasonality['revenue']).set_index('month')
        self.expense_seasonality = pd.DataFrame(self.seasonality['expense']).set_index('month')

    def get_vacate_rate(self, rental_month, months_since_rental):
        """
        Get vacate rate based on rental month and months since rental

        Args:
            rental_month: Month of year when tenant moved in (1-12)
            months_since_rental: How many months since move-in (1, 2, 3, ...)
        """
        match = self.attrition_df[
            (self.attrition_df['rental_month'] == rental_month) &
            (self.attrition_df['vacate_month'] == months_since_rental)
        ]
        if len(match) > 0:
            return match.iloc[0]['vacate_rate']
        return 0.05  # Default 5% monthly attrition if no match

    def generate_projection(self,
                          total_sf,
                          total_units,
                          start_date,
                          starting_rate_psf_annual,
                          stabilized_occupancy=0.92,
                          months_to_stabilization=36,
                          new_tenant_rate_growth=0.04,
                          existing_tenant_rate_increase=0.12,
                          land_cost=0,
                          construction_cost_psf=65,
                          loan_amount=0,
                          interest_rate=0.075,
                          loan_term_years=25,
                          property_characteristics=None):
        """
        Generate enhanced 7-year projection with detailed breakouts

        Args:
            property_characteristics: Dict with keys:
                - multi_story: bool
                - climate_controlled_pct: float (0-1)
                - golf_cart: bool
                - apartment: bool
        """
        if property_characteristics is None:
            property_characteristics = {
                'multi_story': True,
                'climate_controlled_pct': 1.0,
                'golf_cart': False,
                'apartment': False
            }

        # Initialize projection DataFrame (84 months)
        months = 84
        dates = [start_date + relativedelta(months=i) for i in range(months)]

        proj = pd.DataFrame({
            'date': dates,
            'month_num': range(1, months + 1),
            'year': [((i // 12) + 1) for i in range(months)]
        })

        # Calculate financing
        total_cost = land_cost + (construction_cost_psf * total_sf)
        if loan_amount == 0:
            loan_amount = total_cost * 0.65

        monthly_rate = interest_rate / 12
        num_payments = loan_term_years * 12
        if monthly_rate > 0:
            monthly_payment = loan_amount * (monthly_rate * (1 + monthly_rate)**num_payments) / \
                            ((1 + monthly_rate)**num_payments - 1)
        else:
            monthly_payment = loan_amount / num_payments

        # Initialize all columns
        self._initialize_columns(proj)

        # Track rental cohorts: {month_num: {'units': X, 'rental_month': M, 'rate': R}}
        rental_cohorts = {}
        avg_unit_sf = total_sf / total_units

        # Main projection loop
        for i in range(len(proj)):
            month_num = proj.loc[i, 'month_num']
            current_date = proj.loc[i, 'date']
            calendar_month = current_date.month
            year_num = proj.loc[i, 'year']

            # === OCCUPANCY CALCULATIONS ===
            target_occ = self._calculate_target_occupancy(
                month_num, months_to_stabilization, stabilized_occupancy
            )
            proj.loc[i, 'target_occupancy'] = target_occ

            # Beginning occupancy
            if i == 0:
                beginning_units = 0
                beginning_sf = 0
            else:
                beginning_units = proj.loc[i-1, 'ending_occupied_units']
                beginning_sf = proj.loc[i-1, 'ending_occupied_sf']

            # Calculate vacates from cohorts
            total_vacates = 0.0
            updated_cohorts = {}

            for cohort_month_num, cohort_data in rental_cohorts.items():
                cohort_units = cohort_data['units']
                cohort_rental_month = cohort_data['rental_month']
                months_since_rental = month_num - cohort_month_num + 1

                # Get vacate rate
                vacate_rate = self.get_vacate_rate(cohort_rental_month, months_since_rental)
                cohort_vacates = cohort_units * vacate_rate
                total_vacates += cohort_vacates

                # Update cohort (reduce by vacates)
                remaining_units = cohort_units - cohort_vacates
                if remaining_units > 0.01:
                    updated_cohorts[cohort_month_num] = {
                        'units': remaining_units,
                        'rental_month': cohort_rental_month,
                        'rate': cohort_data['rate']
                    }

            rental_cohorts = updated_cohorts
            proj.loc[i, 'vacates'] = total_vacates

            # Calculate required rentals
            target_sf = target_occ * total_sf
            required_rentals_sf = target_sf - (beginning_sf - total_vacates * avg_unit_sf)
            required_rentals_units = max(0, required_rentals_sf / avg_unit_sf)

            proj.loc[i, 'rentals'] = required_rentals_units
            proj.loc[i, 'net_rentals'] = required_rentals_units - total_vacates
            proj.loc[i, 'ending_occupied_units'] = beginning_units + required_rentals_units - total_vacates
            proj.loc[i, 'ending_occupied_sf'] = proj.loc[i, 'ending_occupied_units'] * avg_unit_sf
            proj.loc[i, 'occupancy_pct'] = proj.loc[i, 'ending_occupied_sf'] / total_sf

            # Add new rental cohort with current rate
            years_elapsed = (month_num - 1) / 12
            new_move_in_rate = starting_rate_psf_annual * (1 + new_tenant_rate_growth)**years_elapsed

            if required_rentals_units > 0:
                rental_cohorts[month_num] = {
                    'units': required_rentals_units,
                    'rental_month': calendar_month,
                    'rate': new_move_in_rate
                }

            # Calculate weighted average in-place rate
            total_revenue_potential = 0
            total_units = 0
            for cohort_data in rental_cohorts.values():
                cohort_units = cohort_data['units']
                cohort_rate = cohort_data['rate']
                # Apply existing tenant rate increases (12% annually)
                years_in_place = (month_num - 1) / 12
                increased_rate = cohort_rate * (1 + existing_tenant_rate_increase * years_in_place)
                total_revenue_potential += cohort_units * avg_unit_sf * increased_rate
                total_units += cohort_units

            if total_units > 0:
                in_place_rate = total_revenue_potential / (total_units * avg_unit_sf)
            else:
                in_place_rate = new_move_in_rate

            proj.loc[i, 'avg_rent_rate_new_moveins'] = new_move_in_rate
            proj.loc[i, 'in_place_rate_psf_annual'] = in_place_rate

            # === REVENUE CALCULATIONS ===
            occupied_sf = proj.loc[i, 'ending_occupied_sf']
            monthly_in_place_rate = in_place_rate / 12

            # Rental income
            gross_rental = occupied_sf * monthly_in_place_rate
            proj.loc[i, 'rental_income'] = gross_rental

            # Discounts and writeoffs
            discount_pct = self.benchmarks['revenue']['discounts_pct']
            writeoff_pct = self.benchmarks['revenue']['writeoffs_pct']
            proj.loc[i, 'discounts'] = -gross_rental * discount_pct
            proj.loc[i, 'writeoffs'] = -gross_rental * writeoff_pct
            proj.loc[i, 'net_rental_income'] = gross_rental * (1 - discount_pct - writeoff_pct)

            # Ancillary income
            admin_fees = required_rentals_units * self.benchmarks['revenue']['admin_fee_per_rental']
            late_fees = gross_rental * self.benchmarks['revenue']['late_fee_pct']
            merchandise = required_rentals_units * self.benchmarks['revenue']['merchandise_per_rental']

            # Insurance income
            occupied_units = proj.loc[i, 'ending_occupied_units']
            insurance_penetration = self.benchmarks['revenue']['insurance_penetration']
            insurance_premium = self.benchmarks['revenue']['insurance_premium_per_unit']
            insurance_income = occupied_units * insurance_penetration * insurance_premium

            proj.loc[i, 'admin_fees'] = admin_fees
            proj.loc[i, 'late_fees'] = late_fees
            proj.loc[i, 'merchandise_income'] = merchandise
            proj.loc[i, 'insurance_income'] = insurance_income
            proj.loc[i, 'ancillary_income'] = admin_fees + late_fees + merchandise + insurance_income
            proj.loc[i, 'total_revenue'] = proj.loc[i, 'net_rental_income'] + proj.loc[i, 'ancillary_income']

            # === EXPENSE CALCULATIONS ===
            # Apply annual escalation
            expense_escalator = (1 + self.benchmarks['growth']['expense_annual'])**(year_num - 1)

            # Payroll
            base_salary = 72000  # Annual base salary
            fte_count = max(1, total_sf / 60000)  # 1 FTE per 60k SF
            annual_payroll = base_salary * fte_count
            medical = fte_count * self.benchmarks['payroll']['medical_per_fte']
            payroll_taxes = annual_payroll * self.benchmarks['payroll']['payroll_tax_pct']
            workers_comp = annual_payroll * self.benchmarks['payroll']['workers_comp_pct']
            proj.loc[i, 'payroll'] = (annual_payroll + medical + payroll_taxes + workers_comp) / 12 * expense_escalator

            # Utilities
            utilities = 0
            for key, psf_value in self.benchmarks['utilities'].items():
                utilities += total_sf * psf_value / 12
            proj.loc[i, 'utilities'] = utilities * expense_escalator

            # Operating expenses
            operating = 0
            for key, value in self.benchmarks['operating'].items():
                if 'per_month' in key:
                    operating += value
                elif 'psf' in key:
                    operating += total_sf * value / 12
                elif 'pct' in key:
                    operating += proj.loc[i, 'total_revenue'] * value
            proj.loc[i, 'operating_expenses'] = operating * expense_escalator

            # Landscaping
            proj.loc[i, 'landscaping'] = self.benchmarks['operating']['landscaping_psf'] * total_sf / 12 * expense_escalator

            # Repairs & Maintenance
            rm = total_sf * self.benchmarks['repairs_maintenance']['base_psf'] / 12
            if property_characteristics.get('multi_story'):
                rm += total_sf * self.benchmarks['repairs_maintenance']['elevator_psf'] / 12
            if property_characteristics.get('golf_cart'):
                rm += self.benchmarks['repairs_maintenance']['golf_cart_annual'] / 12
            proj.loc[i, 'repairs_maintenance'] = rm * expense_escalator

            # Marketing
            proj.loc[i, 'marketing'] = self.benchmarks['marketing']['annual_budget'] / 12 * expense_escalator

            # Property taxes (separate escalator)
            tax_escalator = (1 + self.benchmarks['growth']['property_tax_annual'])**(year_num - 1)
            proj.loc[i, 'property_taxes'] = total_sf * self.benchmarks['other']['property_tax_psf'] / 12 * tax_escalator

            # Insurance
            proj.loc[i, 'insurance'] = total_sf * self.benchmarks['other']['insurance_psf'] / 12 * expense_escalator

            # Management fees
            proj.loc[i, 'management_fee'] = proj.loc[i, 'total_revenue'] * self.benchmarks['other']['management_fee_pct']

            # Total expenses
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

            # NOI
            proj.loc[i, 'noi'] = proj.loc[i, 'total_revenue'] - proj.loc[i, 'total_expenses']

            # === DEBT SERVICE ===
            if i == 0:
                beginning_balance = loan_amount
            else:
                beginning_balance = proj.loc[i-1, 'ending_loan_balance']

            interest = beginning_balance * monthly_rate
            principal = monthly_payment - interest
            ending_balance = beginning_balance - principal

            proj.loc[i, 'beginning_loan_balance'] = beginning_balance
            proj.loc[i, 'interest_payment'] = interest
            proj.loc[i, 'principal_payment'] = principal
            proj.loc[i, 'ending_loan_balance'] = ending_balance
            proj.loc[i, 'debt_service'] = monthly_payment
            proj.loc[i, 'levered_cash_flow'] = proj.loc[i, 'noi'] - monthly_payment

            # DSCR
            if monthly_payment > 0:
                proj.loc[i, 'dscr'] = proj.loc[i, 'noi'] / monthly_payment
            else:
                proj.loc[i, 'dscr'] = 0

        return proj

    def _initialize_columns(self, df):
        """Initialize all projection columns"""
        # Occupancy
        df['target_occupancy'] = 0.0
        df['rentals'] = 0.0
        df['vacates'] = 0.0
        df['net_rentals'] = 0.0
        df['ending_occupied_units'] = 0.0
        df['ending_occupied_sf'] = 0.0
        df['occupancy_pct'] = 0.0
        df['avg_rent_rate_new_moveins'] = 0.0
        df['in_place_rate_psf_annual'] = 0.0

        # Revenue
        df['rental_income'] = 0.0
        df['discounts'] = 0.0
        df['writeoffs'] = 0.0
        df['net_rental_income'] = 0.0
        df['admin_fees'] = 0.0
        df['late_fees'] = 0.0
        df['merchandise_income'] = 0.0
        df['insurance_income'] = 0.0
        df['ancillary_income'] = 0.0
        df['total_revenue'] = 0.0

        # Expenses
        df['payroll'] = 0.0
        df['utilities'] = 0.0
        df['operating_expenses'] = 0.0
        df['landscaping'] = 0.0
        df['repairs_maintenance'] = 0.0
        df['marketing'] = 0.0
        df['property_taxes'] = 0.0
        df['insurance'] = 0.0
        df['management_fee'] = 0.0
        df['total_expenses'] = 0.0
        df['noi'] = 0.0

        # Debt
        df['beginning_loan_balance'] = 0.0
        df['interest_payment'] = 0.0
        df['principal_payment'] = 0.0
        df['ending_loan_balance'] = 0.0
        df['debt_service'] = 0.0
        df['levered_cash_flow'] = 0.0
        df['dscr'] = 0.0

    def _calculate_target_occupancy(self, month_num, months_to_stab, stabilized_occ):
        """Calculate target occupancy using S-curve"""
        if month_num <= months_to_stab:
            progress = month_num / months_to_stab
            return stabilized_occ * (1 / (1 + np.exp(-10 * (progress - 0.5))))
        return stabilized_occ

    def generate_annual_summary(self, monthly_projection, purchase_price, equity_contribution):
        """Generate annual summary matching Excel 7 Year Projection layout"""
        proj = monthly_projection.copy()

        annual = proj.groupby('year').agg({
            # Occupancy metrics
            'rentals': 'sum',
            'vacates': 'sum',
            'net_rentals': 'sum',
            'ending_occupied_units': 'last',
            'ending_occupied_sf': 'mean',
            'occupancy_pct': 'mean',
            'avg_rent_rate_new_moveins': 'mean',
            'in_place_rate_psf_annual': 'mean',

            # Revenue
            'rental_income': 'sum',
            'discounts': 'sum',
            'writeoffs': 'sum',
            'net_rental_income': 'sum',
            'ancillary_income': 'sum',
            'total_revenue': 'sum',

            # Expenses
            'payroll': 'sum',
            'utilities': 'sum',
            'operating_expenses': 'sum',
            'landscaping': 'sum',
            'repairs_maintenance': 'sum',
            'marketing': 'sum',
            'property_taxes': 'sum',
            'insurance': 'sum',
            'management_fee': 'sum',
            'total_expenses': 'sum',
            'noi': 'sum',

            # Debt
            'debt_service': 'sum',
            'interest_payment': 'sum',
            'principal_payment': 'sum',
            'levered_cash_flow': 'sum',
            'ending_loan_balance': 'last'
        }).reset_index()

        # Calculate metrics
        annual['dscr'] = annual['noi'] / annual['debt_service']
        annual['cap_rate'] = annual['noi'] / purchase_price
        annual['cash_on_cash'] = annual['levered_cash_flow'] / equity_contribution

        return annual
