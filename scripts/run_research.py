"""Run the fixed initial experiment and save compact shareable summary tables."""

import json

from btc_nasdaq.research import run_research

if __name__ == "__main__":
    print(json.dumps(run_research(), indent=2))
