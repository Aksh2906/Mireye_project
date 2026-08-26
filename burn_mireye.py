import asyncio
import sys
import random
import time
from pathlib import Path

# Add apps/api to path so app can be imported
sys.path.insert(0, str(Path(__file__).parent / "apps" / "api"))

from app.config import get_settings
from app.connectors.mireye import MireyeRESTAdapter

async def main():
    settings = get_settings()
    token = settings.mireye_api_token
    url = settings.mireye_api_url
    
    print("Mireye API Key Burner Starting...")
    print(f"Target API URL: {url}")
    if token:
        clean_token = token.strip()
        print(f"API Token (prefix): {clean_token[:15]}...")
    else:
        print("API Token: None")
    
    if not token:
        print("ERROR: MIREYE_API_TOKEN is not set in environment or .env file.")
        sys.exit(1)
        
    adapter = MireyeRESTAdapter()
    
    # We want around 10 rpm, so 1 request every 6 seconds.
    delay = 6.0
    
    print(f"Configured rate: ~10 RPM (delay of {delay} seconds between requests)")
    print("Starting key burn process. Press Ctrl+C to stop.\n")
    
    count = 0
    # Coordinates in Iowa (corn belt, major agricultural land region)
    # Latitude: 40.5 to 43.5
    # Longitude: -96.5 to -90.5
    try:
        while True:
            count += 1
            lat = round(random.uniform(40.5, 43.5), 6)
            lng = round(random.uniform(-96.5, -90.5), 6)
            
            print(f"[{count}] Requesting context for coordinate: lat={lat}, lng={lng}")
            start_time = time.monotonic()
            
            # Call fetch_context
            result = await adapter.fetch_context(lat, lng)
            
            elapsed = time.monotonic() - start_time
            if result.success:
                num_observations = len(result.observations)
                print(f"    Status: SUCCESS | Observations: {num_observations} | Elapsed: {elapsed:.2f}s")
            else:
                print(f"    Status: FAILED | Error/Limitations: {result.limitations} | Elapsed: {elapsed:.2f}s")
                
            print(f"    Waiting {delay} seconds for next request to respect RPM limit...")
            await asyncio.sleep(delay)
            
    except KeyboardInterrupt:
        print("\nProcess interrupted by user.")
    except Exception as e:
        print(f"\nAn error occurred: {e}")
    finally:
        print(f"\nBurn session complete. Total requests made: {count}")

if __name__ == "__main__":
    asyncio.run(main())
