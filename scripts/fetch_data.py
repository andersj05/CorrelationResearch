"""Download and align the research sample; resumable and deliberately explicit."""

import json

from btc_nasdaq.data import fetch_all

if __name__ == "__main__":
    print(json.dumps(fetch_all(), indent=2))
