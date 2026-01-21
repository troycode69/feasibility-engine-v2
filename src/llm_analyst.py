import os
import json
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

class LLMAnalyst:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.client = None
        if self.api_key:
            self.client = OpenAI(api_key=self.api_key)
        else:
            print("Warning: OPENAI_API_KEY not found.")

    def write_report(self, address, demographics, competitors):
        """
        Generates a professional Feasibility Memorandum using GPT-4o.
        Inputs:
        - address (str)
        - demographics (dict)
        - competitors (list of dicts)
        """
        if not self.client:
            return "Error: AI Analyst not configured (Missing API Key)."

        # Format competitor data for context
        # Handle cases where competitors might correspond to DataManager structure
        if isinstance(competitors, str):
            # If passed as JSON string
            import json
            competitors = json.loads(competitors)
            
        comp_summary = ""
        for c in competitors[:10]: # Limit to top 10
            # Handle varied keys if mock vs scraped
            c_name = c.get('name', 'Unknown Storage')
            c_dist = c.get('distance', 'N/A')
            c_occ = c.get('occupancy_pct', c.get('occupancy', 'N/A'))
            c_rate = c.get('rate_10x10', c.get('rate', 'N/A'))
            comp_summary += f"- {c_name} ({c_dist} mi): {c_occ}% Occ, ${c_rate} Rate\n"

        prompt = f"""
        **Subject Site:** {address}
        
        **Demographic Data (3-Mile Radius):**
        - Population: {demographics.get('population', 'N/A')}
        - Median Household Income: ${demographics.get('median_income', 'N/A')}
        - Household Growth: {demographics.get('household_growth', 'N/A')}%
        
        **Competitive Set (Survey Data):**
        {comp_summary}
        
        **Instructions:**
        Write a robust "Market Feasibility Memorandum" strictly adhering to the following structure:
        
        1. **Executive Summary**: A high-level overview of the opportunity. Use professional, hedging language (e.g., "The data suggests...", "Market indicators point to...").
        2. **Demographic Analysis**: Evaluate the density and income levels relative to self-storage demand.
        3. **Competitive Landscape**: This is CRITICAL. You MUST explicitly analyze at least 3 specific competitors from the list above by name. Discuss their occupancy levels to infer market health (e.g., "The stabilized occupancy at [Competitor Name] indicates...").
        4. **Supply & Feasibility Verdict**: Conclude on the supply gap logic (SFPP) and provide a final recommendation (Go/No-Go).
        
        **Tone:** Senior Investment Officer. Formal, objective, authoritative, but prudent.
        """

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a Senior Investment Officer. Write a Feasibility Memorandum. Use professional, hedging language ('suggests', 'indicates')."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error generating report: {e}"
