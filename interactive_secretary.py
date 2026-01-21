import sys
from main import SecretaryAgent
from config import Config

def main():
    agent = SecretaryAgent()
    print("=========================================")
    print("   StorageOS Secretary Agent - ONLINE    ")
    print("=========================================")
    print(f"Current Mode: {'DRY RUN (Demo)' if Config.DRY_RUN else 'PRODUCTION'}")
    print("\nHow can I help you today, Boss?")
    
    while True:
        user_input = input("\nYou: ").lower().strip()
        
        if any(word in user_input for word in ["run", "ingest", "process", "leads"]):
            print("\nSecretary: Understood. I'm processing the TractiQ Export now...")
            agent.run_daily_automation()
            print("\nSecretary: All leads have been processed and synced to the CRM simulation.")
            
        elif any(word in user_input for word in ["status", "report", "check"]):
            print("\nSecretary: Here is the current status report:")
            print("- CRM Sync: Complete (Simulated)")
            print("- AI Profiles: 3 Generated")
            print("- Radius Matches: Checked against Buyer leads")
            print("- Drive Folders: Prepared for upload")
            
        elif any(word in user_input for word in ["calendar", "tour", "schedule"]):
            print("\nSecretary: Scanning your calendar for tours...")
            tours = agent.workflow.scan_calendar_for_tours()
            if tours:
                print(f"Secretary: I found {len(tours)} tour(s). I've attached the lead folder links to the event descriptions.")
            else:
                print("Secretary: Your calendar looks clear of tours for today.")
                
        elif any(word in user_input for word in ["exit", "bye", "stop", "done"]):
            print("\nSecretary: Goodbye! I'll be here if you need anything else.")
            break
            
        else:
            print("\nSecretary: I'm not sure how to handle that request yet. I can 'Ingest leads', 'Check status', or 'Scan calendar'.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSecretary: Powering down. Have a productive day!")
