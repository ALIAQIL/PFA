import requests
import concurrent.futures
import time
from typing import List
import random

def test_proxy(proxy: str) -> tuple[str, bool]:
    """Test if a proxy is working by trying to connect to a test URL"""
    urls = [
        'https://www.google.com',
        'https://www.amazon.com',
        'https://www.httpbin.org/ip'
    ]
    
    # Format the proxy for requests
    proxy_dict = {
        'http': f'http://{proxy}',
        'https': f'http://{proxy}',
        'socks4':f'socks4://{proxy}',
        'socks5':f'socks5://{proxy}'
    }
    
    try:
        # Try with a random URL from our list
        url = random.choice(urls)
        response = requests.get(
            url,
            proxies=proxy_dict,
            timeout=10,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
        )
        if response.status_code == 200:
            print(f"[SUCCESS] {proxy} is working")
            return proxy, True
    except Exception as e:
        print(f"[FAILED] {proxy} - {str(e)}")
    return proxy, False

def load_proxies(filename: str) -> List[str]:
    """Load proxies from file"""
    try:
        with open(filename, 'r') as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"Error: {filename} not found")
        return []

def save_valid_proxies(valid_proxies: List[str], filename: str):
    """Save working proxies to file"""
    with open(filename, 'w') as f:
        for proxy in valid_proxies:
            f.write(f"{proxy}\n")

def validate_proxies(input_file: str, output_file: str, max_workers: int = 10):
    """Main function to validate proxies"""
    # Load proxies
    proxies = load_proxies(input_file)
    if not proxies:
        return
    
    print(f"Loaded {len(proxies)} proxies from {input_file}")
    valid_proxies = []
    
    # Test proxies concurrently
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_proxy = {executor.submit(test_proxy, proxy): proxy for proxy in proxies}
        
        for future in concurrent.futures.as_completed(future_to_proxy):
            proxy = future_to_proxy[future]
            try:
                proxy, is_valid = future.result()
                if is_valid:
                    valid_proxies.append(proxy)
            except Exception as e:
                print(f"Error testing {proxy}: {str(e)}")
    
    # Save valid proxies
    if valid_proxies:
        save_valid_proxies(valid_proxies, output_file)
        print(f"\nValidation complete!")
        print(f"Found {len(valid_proxies)} working proxies out of {len(proxies)}")
        print(f"Valid proxies saved to {output_file}")
    else:
        print("\nNo working proxies found!")

def main():
    input_file = "proxy_list.txt"
    output_file = "valid_proxies.txt"
    
    print("Starting proxy validation...")
    print("This may take a few minutes...")
    
    start_time = time.time()
    validate_proxies(input_file, output_file)
    end_time = time.time()
    
    print(f"\nTotal time taken: {end_time - start_time:.2f} seconds")

if __name__ == "__main__":
    main() 