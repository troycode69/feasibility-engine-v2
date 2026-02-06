"""
Chart Generation Engine for Self-Storage Feasibility Reports

McKinley-level professional visualizations:
- 7-year NOI waterfall chart
- Occupancy ramp-up curve
- Cash flow timeline (stacked bar)
- Sensitivity tornado diagram
- Scoring radar chart
- Competitor rate scatter plot
- SF per capita comparison bars

Outputs PNG images and base64 encoded strings for PDF embedding.
"""

import io
import base64
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np


# ============================================================================
# STYLING CONSTANTS
# ============================================================================

# Brand colors
NAVY = '#0C2340'
ORANGE = '#F39C12'
LIGHT_GRAY = '#f8f9fa'
DARK_GRAY = '#666666'

# Chart colors
COLORS = {
    'primary': NAVY,
    'secondary': ORANGE,
    'positive': '#28a745',
    'negative': '#dc3545',
    'neutral': '#6c757d',
    'light': LIGHT_GRAY,
}

# Style settings
plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.sans-serif': ['Helvetica', 'Arial', 'DejaVu Sans'],
    'font.size': 10,
    'axes.titlesize': 12,
    'axes.labelsize': 10,
    'xtick.labelsize': 9,
    'ytick.labelsize': 9,
    'legend.fontsize': 9,
    'figure.titlesize': 14,
    'axes.spines.top': False,
    'axes.spines.right': False,
})


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def fig_to_base64(fig: plt.Figure) -> str:
    """Convert matplotlib figure to base64 string for HTML embedding."""
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    buf.close()
    plt.close(fig)
    return img_base64


def save_fig_to_file(fig: plt.Figure, filepath: str) -> str:
    """Save figure to file and return the path."""
    fig.savefig(filepath, format='png', dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    return filepath


def format_currency(value: float, decimal_places: int = 0) -> str:
    """Format number as currency string."""
    if abs(value) >= 1_000_000:
        return f"${value/1_000_000:.1f}M"
    elif abs(value) >= 1_000:
        return f"${value/1_000:.0f}K"
    else:
        return f"${value:,.{decimal_places}f}"


# ============================================================================
# CHART GENERATORS
# ============================================================================

def generate_noi_waterfall(
    years: List[int],
    noi_values: List[float],
    title: str = "Net Operating Income Projection",
) -> str:
    """
    Generate 7-year NOI waterfall/bar chart.

    Args:
        years: List of years [1, 2, 3, ...]
        noi_values: List of annual NOI values
        title: Chart title

    Returns:
        Base64 encoded PNG image
    """
    fig, ax = plt.subplots(figsize=(10, 5))

    # Create bar chart
    x = np.arange(len(years))
    bars = ax.bar(x, [v/1000 for v in noi_values], color=NAVY, width=0.6)

    # Add value labels on bars
    for bar, val in zip(bars, noi_values):
        height = bar.get_height()
        ax.annotate(format_currency(val),
                   xy=(bar.get_x() + bar.get_width() / 2, height),
                   xytext=(0, 3),
                   textcoords="offset points",
                   ha='center', va='bottom', fontsize=9, fontweight='bold')

    # Styling
    ax.set_xlabel('Year', fontweight='bold')
    ax.set_ylabel('NOI ($000s)', fontweight='bold')
    ax.set_title(title, fontweight='bold', fontsize=14, color=NAVY)
    ax.set_xticks(x)
    ax.set_xticklabels([f'Year {y}' for y in years])
    ax.set_ylim(0, max([v/1000 for v in noi_values]) * 1.15)
    ax.yaxis.grid(True, linestyle='--', alpha=0.3)

    # Add stabilization line if NOI plateaus
    if len(noi_values) > 3 and noi_values[-1] > 0:
        stabilized = noi_values[-1] / 1000
        ax.axhline(y=stabilized, color=ORANGE, linestyle='--', linewidth=2, label='Stabilized NOI')
        ax.legend(loc='lower right')

    fig.tight_layout()
    return fig_to_base64(fig)


def generate_occupancy_curve(
    months: List[int],
    occupancy_pcts: List[float],
    stabilized_occ: float = 92.0,
    title: str = "Lease-Up Projection",
) -> str:
    """
    Generate occupancy ramp-up curve.

    Args:
        months: List of months [1, 2, 3, ...]
        occupancy_pcts: List of occupancy percentages
        stabilized_occ: Target stabilized occupancy
        title: Chart title

    Returns:
        Base64 encoded PNG image
    """
    fig, ax = plt.subplots(figsize=(10, 5))

    # Plot occupancy curve
    ax.plot(months, occupancy_pcts, color=NAVY, linewidth=2.5, label='Projected Occupancy')
    ax.fill_between(months, occupancy_pcts, alpha=0.1, color=NAVY)

    # Add stabilization line
    ax.axhline(y=stabilized_occ, color=ORANGE, linestyle='--', linewidth=2, label=f'Stabilized ({stabilized_occ:.0f}%)')

    # Find stabilization month
    stab_month = None
    for i, occ in enumerate(occupancy_pcts):
        if occ >= stabilized_occ * 0.99:
            stab_month = months[i]
            break

    if stab_month:
        ax.axvline(x=stab_month, color=DARK_GRAY, linestyle=':', alpha=0.7)
        ax.annotate(f'Month {stab_month}', xy=(stab_month, stabilized_occ/2),
                   xytext=(5, 0), textcoords='offset points', fontsize=9, alpha=0.7)

    # Styling
    ax.set_xlabel('Month', fontweight='bold')
    ax.set_ylabel('Occupancy (%)', fontweight='bold')
    ax.set_title(title, fontweight='bold', fontsize=14, color=NAVY)
    ax.set_xlim(1, max(months))
    ax.set_ylim(0, 100)
    ax.legend(loc='lower right')
    ax.yaxis.grid(True, linestyle='--', alpha=0.3)

    fig.tight_layout()
    return fig_to_base64(fig)


def generate_cash_flow_chart(
    years: List[int],
    noi: List[float],
    debt_service: List[float],
    cash_flow: List[float],
    title: str = "Annual Cash Flow Summary",
) -> str:
    """
    Generate stacked bar chart showing NOI, debt service, and cash flow.

    Args:
        years: List of years
        noi: Annual NOI values
        debt_service: Annual debt service values
        cash_flow: Annual cash flow values
        title: Chart title

    Returns:
        Base64 encoded PNG image
    """
    fig, ax = plt.subplots(figsize=(10, 5))

    x = np.arange(len(years))
    width = 0.25

    # Bars
    bars1 = ax.bar(x - width, [v/1000 for v in noi], width, label='NOI', color=NAVY)
    bars2 = ax.bar(x, [v/1000 for v in debt_service], width, label='Debt Service', color=ORANGE)
    bars3 = ax.bar(x + width, [v/1000 for v in cash_flow], width, label='Cash Flow',
                   color=[COLORS['positive'] if v >= 0 else COLORS['negative'] for v in cash_flow])

    # Styling
    ax.set_xlabel('Year', fontweight='bold')
    ax.set_ylabel('Amount ($000s)', fontweight='bold')
    ax.set_title(title, fontweight='bold', fontsize=14, color=NAVY)
    ax.set_xticks(x)
    ax.set_xticklabels([f'Year {y}' for y in years])
    ax.legend(loc='upper left')
    ax.yaxis.grid(True, linestyle='--', alpha=0.3)
    ax.axhline(y=0, color='black', linewidth=0.5)

    fig.tight_layout()
    return fig_to_base64(fig)


def generate_sensitivity_tornado(
    variables: List[str],
    low_values: List[float],
    high_values: List[float],
    base_value: float,
    metric_name: str = "IRR",
    title: str = "Sensitivity Analysis",
) -> str:
    """
    Generate tornado diagram for sensitivity analysis.

    Args:
        variables: List of variable names
        low_values: Values at low end of sensitivity range
        high_values: Values at high end of sensitivity range
        base_value: Base case value
        metric_name: Name of metric (IRR, NPV, etc.)
        title: Chart title

    Returns:
        Base64 encoded PNG image
    """
    fig, ax = plt.subplots(figsize=(10, max(5, len(variables) * 0.6)))

    y_pos = np.arange(len(variables))

    # Calculate bar lengths
    low_bars = [base_value - low for low in low_values]
    high_bars = [high - base_value for high in high_values]

    # Plot bars
    bars_low = ax.barh(y_pos, [-b for b in low_bars], align='center', color=COLORS['negative'], alpha=0.8)
    bars_high = ax.barh(y_pos, high_bars, align='center', color=COLORS['positive'], alpha=0.8)

    # Add base line
    ax.axvline(x=0, color=NAVY, linewidth=2)

    # Add value labels
    for i, (low, high) in enumerate(zip(low_values, high_values)):
        ax.annotate(f'{low:.1f}%', xy=(-low_bars[i] - 0.5, i), va='center', ha='right', fontsize=8)
        ax.annotate(f'{high:.1f}%', xy=(high_bars[i] + 0.5, i), va='center', ha='left', fontsize=8)

    # Styling
    ax.set_yticks(y_pos)
    ax.set_yticklabels(variables)
    ax.set_xlabel(f'Impact on {metric_name} (%)', fontweight='bold')
    ax.set_title(title, fontweight='bold', fontsize=14, color=NAVY)
    ax.xaxis.grid(True, linestyle='--', alpha=0.3)

    # Add legend
    legend_elements = [
        mpatches.Patch(color=COLORS['negative'], alpha=0.8, label='Downside'),
        mpatches.Patch(color=COLORS['positive'], alpha=0.8, label='Upside'),
    ]
    ax.legend(handles=legend_elements, loc='lower right')

    # Add base case annotation
    ax.annotate(f'Base: {base_value:.1f}%', xy=(0, -0.7), ha='center',
               fontsize=10, fontweight='bold', color=NAVY)

    fig.tight_layout()
    return fig_to_base64(fig)


def generate_scoring_radar(
    categories: List[str],
    scores: List[float],
    max_scores: List[float],
    title: str = "Site Scoring Summary",
) -> str:
    """
    Generate radar/spider chart for scoring breakdown.

    Args:
        categories: Category names
        scores: Achieved scores
        max_scores: Maximum possible scores
        title: Chart title

    Returns:
        Base64 encoded PNG image
    """
    # Calculate angles
    N = len(categories)
    angles = [n / float(N) * 2 * np.pi for n in range(N)]
    angles += angles[:1]  # Complete the loop

    # Normalize scores to percentages
    normalized = [s/m * 100 if m > 0 else 0 for s, m in zip(scores, max_scores)]
    normalized += normalized[:1]

    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))

    # Plot
    ax.plot(angles, normalized, 'o-', linewidth=2, color=NAVY)
    ax.fill(angles, normalized, alpha=0.25, color=NAVY)

    # Add category labels
    ax.set_xticks(angles[:-1])
    category_labels = [f"{cat}\n({s:.0f}/{m:.0f})" for cat, s, m in zip(categories, scores, max_scores)]
    ax.set_xticklabels(category_labels, fontsize=10)

    # Set radial limits
    ax.set_ylim(0, 100)
    ax.set_yticks([25, 50, 75, 100])
    ax.set_yticklabels(['25%', '50%', '75%', '100%'], fontsize=8)

    ax.set_title(title, fontweight='bold', fontsize=14, color=NAVY, pad=20)

    # Add total score in center
    total = sum(scores)
    max_total = sum(max_scores)
    ax.annotate(f'{total:.0f}/{max_total:.0f}', xy=(0, 0), ha='center', va='center',
               fontsize=20, fontweight='bold', color=NAVY)

    fig.tight_layout()
    return fig_to_base64(fig)


def generate_competitor_scatter(
    distances: List[float],
    rates: List[float],
    names: List[str],
    subject_rate: Optional[float] = None,
    title: str = "Competitor Rate Positioning",
) -> str:
    """
    Generate scatter plot of competitor rates vs distance.

    Args:
        distances: Distance from subject (miles)
        rates: Rate per SF
        names: Competitor names
        subject_rate: Subject property proposed rate
        title: Chart title

    Returns:
        Base64 encoded PNG image
    """
    fig, ax = plt.subplots(figsize=(10, 6))

    # Plot competitors
    ax.scatter(distances, rates, s=100, c=NAVY, alpha=0.6, edgecolors='white', linewidth=1)

    # Add labels for closest competitors
    sorted_indices = sorted(range(len(distances)), key=lambda i: distances[i])
    for i in sorted_indices[:5]:  # Label closest 5
        ax.annotate(names[i][:20], xy=(distances[i], rates[i]),
                   xytext=(5, 5), textcoords='offset points', fontsize=8, alpha=0.7)

    # Add subject rate line
    if subject_rate:
        ax.axhline(y=subject_rate, color=ORANGE, linestyle='--', linewidth=2,
                  label=f'Subject Rate: ${subject_rate:.2f}/SF')

    # Add market average line
    avg_rate = sum(rates) / len(rates) if rates else 0
    ax.axhline(y=avg_rate, color=DARK_GRAY, linestyle=':', linewidth=1.5,
              label=f'Market Avg: ${avg_rate:.2f}/SF')

    # Styling
    ax.set_xlabel('Distance from Subject (miles)', fontweight='bold')
    ax.set_ylabel('Rate ($/SF)', fontweight='bold')
    ax.set_title(title, fontweight='bold', fontsize=14, color=NAVY)
    ax.legend(loc='upper right')
    ax.xaxis.grid(True, linestyle='--', alpha=0.3)
    ax.yaxis.grid(True, linestyle='--', alpha=0.3)

    fig.tight_layout()
    return fig_to_base64(fig)


def generate_sf_per_capita_comparison(
    radii: List[str],
    values: List[float],
    target: float = 6.5,
    title: str = "SF Per Capita by Radius",
) -> str:
    """
    Generate bar chart comparing SF per capita at different radii.

    Args:
        radii: Radius labels ["1 Mile", "3 Miles", "5 Miles"]
        values: SF per capita values
        target: Target/equilibrium SF per capita
        title: Chart title

    Returns:
        Base64 encoded PNG image
    """
    fig, ax = plt.subplots(figsize=(8, 5))

    x = np.arange(len(radii))

    # Color bars based on under/over supplied
    colors = [COLORS['positive'] if v < target else COLORS['negative'] for v in values]
    bars = ax.bar(x, values, color=colors, width=0.5, alpha=0.8)

    # Add target line
    ax.axhline(y=target, color=NAVY, linestyle='--', linewidth=2,
              label=f'Target: {target} SF/capita')

    # Add value labels
    for bar, val in zip(bars, values):
        status = "Under" if val < target else "Over"
        ax.annotate(f'{val:.1f}\n({status})',
                   xy=(bar.get_x() + bar.get_width() / 2, val),
                   xytext=(0, 5), textcoords='offset points',
                   ha='center', va='bottom', fontsize=10, fontweight='bold')

    # Styling
    ax.set_xlabel('Trade Area Radius', fontweight='bold')
    ax.set_ylabel('SF Per Capita', fontweight='bold')
    ax.set_title(title, fontweight='bold', fontsize=14, color=NAVY)
    ax.set_xticks(x)
    ax.set_xticklabels(radii)
    ax.set_ylim(0, max(values) * 1.3)
    ax.legend(loc='upper right')
    ax.yaxis.grid(True, linestyle='--', alpha=0.3)

    fig.tight_layout()
    return fig_to_base64(fig)


def generate_scenario_comparison(
    scenarios: List[str],
    irrs: List[float],
    npvs: List[float],
    title: str = "Scenario Comparison",
) -> str:
    """
    Generate grouped bar chart comparing scenarios.

    Args:
        scenarios: Scenario names
        irrs: IRR values for each scenario
        npvs: NPV values for each scenario (in $1000s)
        title: Chart title

    Returns:
        Base64 encoded PNG image
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    x = np.arange(len(scenarios))
    colors = [COLORS['negative'], NAVY, COLORS['positive']]

    # IRR bars
    bars1 = ax1.bar(x, irrs, color=colors, width=0.5)
    ax1.axhline(y=12, color=DARK_GRAY, linestyle='--', label='12% Hurdle')
    ax1.set_ylabel('IRR (%)', fontweight='bold')
    ax1.set_title('IRR by Scenario', fontweight='bold', color=NAVY)
    ax1.set_xticks(x)
    ax1.set_xticklabels(scenarios)
    ax1.legend()

    for bar, val in zip(bars1, irrs):
        ax1.annotate(f'{val:.1f}%', xy=(bar.get_x() + bar.get_width()/2, val),
                    xytext=(0, 3), textcoords='offset points', ha='center', fontweight='bold')

    # NPV bars
    bars2 = ax2.bar(x, [n/1000 for n in npvs], color=colors, width=0.5)
    ax2.axhline(y=0, color='black', linewidth=0.5)
    ax2.set_ylabel('NPV ($000s)', fontweight='bold')
    ax2.set_title('NPV by Scenario', fontweight='bold', color=NAVY)
    ax2.set_xticks(x)
    ax2.set_xticklabels(scenarios)

    for bar, val in zip(bars2, npvs):
        ax2.annotate(format_currency(val), xy=(bar.get_x() + bar.get_width()/2, val/1000),
                    xytext=(0, 3), textcoords='offset points', ha='center', fontweight='bold')

    fig.suptitle(title, fontweight='bold', fontsize=14, color=NAVY)
    fig.tight_layout()
    return fig_to_base64(fig)


# ============================================================================
# NEW CHART TYPES - Premium Visualizations
# ============================================================================

def generate_market_cycle_gauge(
    cycle_phase: str,
    cycle_position: float = 50,
    title: str = "Market Cycle Position"
) -> str:
    """
    Generate a gauge chart showing market cycle position.

    Args:
        cycle_phase: Current phase ("Recovery", "Expansion", "Hypersupply", "Recession")
        cycle_position: Position within the phase (0-100, where 50 is middle of phase)
        title: Chart title

    Returns:
        Base64 encoded PNG
    """
    fig, ax = plt.subplots(figsize=(8, 5), subplot_kw={'projection': 'polar'})

    # Define cycle phases and their colors
    phases = ["Recovery", "Expansion", "Hypersupply", "Recession"]
    phase_colors = ['#28a745', '#17a2b8', '#ffc107', '#dc3545']

    # Create the gauge (half circle)
    theta = np.linspace(0, np.pi, 100)

    # Draw colored segments for each phase
    for i, (phase, color) in enumerate(zip(phases, phase_colors)):
        start = i * np.pi / 4
        end = (i + 1) * np.pi / 4
        phase_theta = np.linspace(start, end, 25)
        ax.fill_between(phase_theta, 0.7, 1.0, color=color, alpha=0.7)
        # Add phase label
        mid_angle = (start + end) / 2
        ax.text(mid_angle, 1.15, phase, ha='center', va='center', fontsize=9, fontweight='bold')

    # Draw needle based on current phase and position
    phase_idx = phases.index(cycle_phase) if cycle_phase in phases else 0
    needle_angle = (phase_idx + cycle_position / 100) * np.pi / 4

    ax.annotate('', xy=(needle_angle, 0.9), xytext=(needle_angle, 0),
                arrowprops=dict(arrowstyle='->', color=NAVY, lw=3))

    # Center point
    ax.scatter([needle_angle], [0], color=NAVY, s=100, zorder=5)

    ax.set_ylim(0, 1.3)
    ax.set_theta_zero_location('W')
    ax.set_theta_direction(-1)
    ax.set_thetamin(0)
    ax.set_thetamax(180)
    ax.axis('off')

    # Add title and current phase
    fig.suptitle(title, fontweight='bold', fontsize=14, color=NAVY, y=0.95)
    ax.text(np.pi/2, -0.3, f"Current: {cycle_phase}", ha='center', va='center',
            fontsize=12, fontweight='bold', color=NAVY)

    fig.tight_layout()
    return fig_to_base64(fig)


def generate_absorption_timeline(
    months: List[int],
    projected_absorption: List[float],
    market_new_supply: List[float] = None,
    stabilization_month: int = 36,
    title: str = "Absorption Timeline"
) -> str:
    """
    Generate absorption timeline showing projected lease-up vs market supply.

    Args:
        months: List of month numbers
        projected_absorption: Projected SF absorbed per month
        market_new_supply: New supply entering market per month
        stabilization_month: Expected month of stabilization
        title: Chart title

    Returns:
        Base64 encoded PNG
    """
    fig, ax = plt.subplots(figsize=(10, 5))

    # Cumulative absorption
    cumulative_absorption = np.cumsum(projected_absorption)
    ax.fill_between(months, 0, cumulative_absorption, alpha=0.3, color=COLORS['positive'])
    ax.plot(months, cumulative_absorption, color=COLORS['positive'], linewidth=2, label='Cumulative Absorption')

    # New supply if provided
    if market_new_supply:
        cumulative_supply = np.cumsum(market_new_supply)
        ax.plot(months, cumulative_supply, color=COLORS['negative'], linewidth=2,
                linestyle='--', label='New Supply')

    # Stabilization marker
    ax.axvline(x=stabilization_month, color=ORANGE, linestyle=':', linewidth=2, label='Stabilization')
    ax.annotate(f'Stabilization\nMonth {stabilization_month}',
                xy=(stabilization_month, max(cumulative_absorption) * 0.8),
                xytext=(stabilization_month + 5, max(cumulative_absorption) * 0.9),
                fontsize=9, fontweight='bold',
                arrowprops=dict(arrowstyle='->', color=ORANGE))

    ax.set_xlabel('Months')
    ax.set_ylabel('Cumulative SF Absorbed')
    ax.set_title(title, fontweight='bold', color=NAVY)
    ax.legend(loc='lower right')
    ax.set_xlim(min(months), max(months))
    ax.set_ylim(0)

    # Format y-axis
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/1000:.0f}K'))

    fig.tight_layout()
    return fig_to_base64(fig)


def generate_rate_heatmap(
    unit_sizes: List[str],
    competitors: List[str],
    rates: List[List[float]],
    subject_rates: List[float] = None,
    title: str = "Rate Competitiveness Heatmap"
) -> str:
    """
    Generate heatmap showing rate comparison across unit sizes and competitors.

    Args:
        unit_sizes: List of unit size labels (e.g., ["5x5", "5x10", "10x10"])
        competitors: List of competitor names
        rates: 2D list of rates [competitor][unit_size]
        subject_rates: Subject property rates for comparison
        title: Chart title

    Returns:
        Base64 encoded PNG
    """
    fig, ax = plt.subplots(figsize=(10, max(6, len(competitors) * 0.4)))

    # Convert to numpy array for heatmap
    rate_array = np.array(rates)

    # Handle missing values
    rate_array = np.nan_to_num(rate_array, nan=0)

    # Create heatmap
    im = ax.imshow(rate_array, cmap='RdYlGn_r', aspect='auto')

    # Set ticks
    ax.set_xticks(np.arange(len(unit_sizes)))
    ax.set_yticks(np.arange(len(competitors)))
    ax.set_xticklabels(unit_sizes)
    ax.set_yticklabels(competitors)

    # Rotate x labels
    plt.setp(ax.get_xticklabels(), rotation=45, ha='right')

    # Add rate values in cells
    for i in range(len(competitors)):
        for j in range(len(unit_sizes)):
            if rate_array[i, j] > 0:
                text = ax.text(j, i, f'${rate_array[i, j]:.2f}',
                              ha='center', va='center', color='white', fontsize=8)

    # Add subject property row if provided
    if subject_rates:
        ax.axhline(y=-0.5, color=ORANGE, linewidth=3)
        for j, rate in enumerate(subject_rates):
            if rate > 0:
                ax.annotate(f'Subject: ${rate:.2f}', xy=(j, -0.3),
                           ha='center', fontsize=8, color=ORANGE, fontweight='bold')

    ax.set_title(title, fontweight='bold', color=NAVY, pad=20)

    # Add colorbar
    cbar = ax.figure.colorbar(im, ax=ax)
    cbar.ax.set_ylabel('$/SF/Month', rotation=-90, va='bottom')

    fig.tight_layout()
    return fig_to_base64(fig)


def generate_pipeline_timeline(
    projects: List[Dict],
    title: str = "Development Pipeline Timeline"
) -> str:
    """
    Generate Gantt-style chart showing development pipeline.

    Args:
        projects: List of dicts with 'name', 'start_date', 'end_date', 'sf', 'status'
        title: Chart title

    Returns:
        Base64 encoded PNG
    """
    fig, ax = plt.subplots(figsize=(12, max(5, len(projects) * 0.6)))

    # Status colors
    status_colors = {
        'Under Construction': ORANGE,
        'Planned': COLORS['neutral'],
        'Approved': '#17a2b8',
        'Completed': COLORS['positive']
    }

    y_positions = range(len(projects))

    for i, project in enumerate(projects):
        name = project.get('name', f'Project {i+1}')[:25]
        start = project.get('start_month', 0)
        duration = project.get('duration_months', 12)
        sf = project.get('sf', 0)
        status = project.get('status', 'Planned')

        color = status_colors.get(status, COLORS['neutral'])

        # Draw bar
        ax.barh(i, duration, left=start, color=color, alpha=0.8, edgecolor='white', linewidth=1)

        # Add label
        ax.text(start + duration/2, i, f'{name}\n{sf:,} SF',
               ha='center', va='center', fontsize=8, color='white', fontweight='bold')

    ax.set_yticks(y_positions)
    ax.set_yticklabels([p.get('name', '')[:20] for p in projects])
    ax.set_xlabel('Months from Today')
    ax.set_title(title, fontweight='bold', color=NAVY)

    # Add legend
    legend_patches = [mpatches.Patch(color=color, label=status)
                     for status, color in status_colors.items()]
    ax.legend(handles=legend_patches, loc='upper right', fontsize=8)

    # Add today marker
    ax.axvline(x=0, color=NAVY, linestyle='--', linewidth=2, label='Today')

    ax.set_xlim(-6, max(p.get('start_month', 0) + p.get('duration_months', 12) for p in projects) + 6)

    fig.tight_layout()
    return fig_to_base64(fig)


def generate_demand_driver_pie(
    drivers: Dict[str, float],
    title: str = "Demand Driver Breakdown"
) -> str:
    """
    Generate pie chart showing demand driver breakdown.

    Args:
        drivers: Dict mapping driver name to percentage
        title: Chart title

    Returns:
        Base64 encoded PNG
    """
    fig, ax = plt.subplots(figsize=(8, 6))

    labels = list(drivers.keys())
    sizes = list(drivers.values())

    # Colors
    colors = [NAVY, ORANGE, COLORS['positive'], '#17a2b8', COLORS['neutral'], '#6f42c1'][:len(labels)]

    # Create pie
    wedges, texts, autotexts = ax.pie(sizes, labels=labels, autopct='%1.1f%%',
                                       colors=colors, startangle=90,
                                       explode=[0.02] * len(labels))

    # Style
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontweight('bold')

    ax.set_title(title, fontweight='bold', color=NAVY, pad=20)

    fig.tight_layout()
    return fig_to_base64(fig)


def generate_risk_return_scatter(
    scenarios: List[Dict],
    hurdle_rate: float = 12.0,
    title: str = "Risk-Return Analysis"
) -> str:
    """
    Generate scatter plot showing IRR vs Risk Score for different scenarios.

    Args:
        scenarios: List of dicts with 'name', 'irr', 'risk_score', 'npv'
        hurdle_rate: Minimum acceptable IRR
        title: Chart title

    Returns:
        Base64 encoded PNG
    """
    fig, ax = plt.subplots(figsize=(10, 6))

    # Extract data
    names = [s.get('name', '') for s in scenarios]
    irrs = [s.get('irr', 0) for s in scenarios]
    risks = [s.get('risk_score', 50) for s in scenarios]
    npvs = [abs(s.get('npv', 1000000)) for s in scenarios]

    # Normalize NPV for bubble size
    max_npv = max(npvs) if npvs else 1
    sizes = [300 + (npv / max_npv) * 1000 for npv in npvs]

    # Color based on IRR vs hurdle
    colors = [COLORS['positive'] if irr >= hurdle_rate else COLORS['negative'] for irr in irrs]

    # Create scatter
    scatter = ax.scatter(risks, irrs, s=sizes, c=colors, alpha=0.6, edgecolors='white', linewidth=2)

    # Add labels
    for i, name in enumerate(names):
        ax.annotate(name, (risks[i], irrs[i]), xytext=(5, 5),
                   textcoords='offset points', fontsize=9, fontweight='bold')

    # Hurdle rate line
    ax.axhline(y=hurdle_rate, color=ORANGE, linestyle='--', linewidth=2, label=f'Hurdle Rate ({hurdle_rate}%)')

    # Quadrant labels
    ax.text(25, ax.get_ylim()[1] * 0.9, 'High Return\nLow Risk', ha='center', fontsize=10,
           color=COLORS['positive'], fontweight='bold', alpha=0.7)
    ax.text(75, ax.get_ylim()[1] * 0.9, 'High Return\nHigh Risk', ha='center', fontsize=10,
           color=ORANGE, fontweight='bold', alpha=0.7)
    ax.text(25, hurdle_rate * 0.5, 'Low Return\nLow Risk', ha='center', fontsize=10,
           color=COLORS['neutral'], fontweight='bold', alpha=0.7)
    ax.text(75, hurdle_rate * 0.5, 'Low Return\nHigh Risk', ha='center', fontsize=10,
           color=COLORS['negative'], fontweight='bold', alpha=0.7)

    ax.set_xlabel('Risk Score (0-100)', fontweight='bold')
    ax.set_ylabel('IRR (%)', fontweight='bold')
    ax.set_title(title, fontweight='bold', color=NAVY)
    ax.legend(loc='upper right')

    ax.set_xlim(0, 100)
    ax.set_ylim(0, max(irrs) * 1.2 if irrs else 25)

    fig.tight_layout()
    return fig_to_base64(fig)


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    print("=== Chart Generator Test ===\n")

    # Test NOI waterfall
    years = [1, 2, 3, 4, 5, 6, 7]
    noi_values = [50000, 280000, 520000, 615000, 630000, 645000, 660000]

    noi_chart = generate_noi_waterfall(years, noi_values)
    print(f"NOI Chart generated: {len(noi_chart)} bytes (base64)")

    # Test occupancy curve
    months = list(range(1, 85))
    occupancy = [min(92, i * 2.5) for i in months]  # Simple ramp

    occ_chart = generate_occupancy_curve(months, occupancy)
    print(f"Occupancy Chart generated: {len(occ_chart)} bytes (base64)")

    # Test tornado diagram
    variables = ["Rental Rates", "Construction Cost", "Occupancy", "Exit Cap Rate", "Interest Rate"]
    low_irrs = [4.3, 8.7, 9.0, 10.7, 12.2]
    high_irrs = [20.5, 18.9, 16.0, 16.8, 15.0]

    tornado_chart = generate_sensitivity_tornado(variables, low_irrs, high_irrs, 13.6)
    print(f"Tornado Chart generated: {len(tornado_chart)} bytes (base64)")

    # Test radar chart
    categories = ["Demographics", "Supply/Demand", "Site Quality", "Competition", "Economics"]
    scores = [20, 18, 22, 12, 8]
    max_scores = [25, 25, 25, 15, 10]

    radar_chart = generate_scoring_radar(categories, scores, max_scores)
    print(f"Radar Chart generated: {len(radar_chart)} bytes (base64)")

    # Test scenario comparison
    scenarios = ["Conservative", "Base Case", "Aggressive"]
    irrs = [5.2, 13.6, 21.8]
    npvs = [-500000, 644000, 1800000]

    scenario_chart = generate_scenario_comparison(scenarios, irrs, npvs)
    print(f"Scenario Chart generated: {len(scenario_chart)} bytes (base64)")

    print("\nAll charts generated successfully!")
