import requests
import sys
import os

DEPLOY_URL = os.getenv(
    "DEPLOY_URL",
    "https://shadow-sentinel-1092599030143.europe-west2.run.app"
)
THRESHOLD = float(os.getenv("AGREEMENT_THRESHOLD", "80.0"))

def run_check():
    print(f"Checking shadow deployment at {DEPLOY_URL}")
    
    try:
        response = requests.get(f"{DEPLOY_URL}/stats", timeout=60)
        response.raise_for_status()
    except Exception as e:
        print(f"ERROR: Could not reach deployment — {e}")
        sys.exit(1)

    data = response.json()
    rate = data.get("agreement_rate", 0)
    total = data.get("total", 0)
    critical = data.get("diagnosis", {}).get("high_conf_conflicts", 0)

    print(f"Agreement rate:     {rate}%")
    print(f"Total predictions:  {total}")
    print(f"Critical conflicts: {critical}")
    print(f"Threshold:          {THRESHOLD}%")

    if total < 5:
        print("WARNING: Not enough predictions to make a reliable decision.")
        print("RESULT: SKIP — insufficient data")
        sys.exit(0)

    if rate >= THRESHOLD and critical == 0:
        print("RESULT: PROMOTE — Model B meets all criteria")
        sys.exit(0)
    elif rate >= THRESHOLD and critical > 0:
        print("RESULT: HOLD — Agreement rate acceptable but critical conflicts detected")
        sys.exit(1)
    else:
        print(f"RESULT: ROLLBACK — Agreement rate {rate}% below threshold {THRESHOLD}%")
        sys.exit(1)

if __name__ == "__main__":
    run_check()