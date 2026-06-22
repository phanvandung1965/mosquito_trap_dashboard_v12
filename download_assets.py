import os
import re
import urllib.request
import urllib.parse
from urllib.error import URLError, HTTPError
import shutil

def download_assets():
    html_file = 'dashboard_v9.01.html'
    output_html_file = 'dashboard_v10.html'
    static_dir = 'static'
    
    # Ensure static directory exists
    if not os.path.exists(static_dir):
        os.makedirs(static_dir)

    # Read the original HTML file
    try:
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
    except FileNotFoundError:
        print(f"Error: Could not find {html_file}")
        return

    # Regular expressions to find URLs
    # For <link href="...">
    link_pattern = re.compile(r'<link[^>]+href=["\'](https?://(?:cdn\.jsdelivr\.net|unpkg\.com)[^"\']+)["\'][^>]*>', re.IGNORECASE)
    # For <script src="...">
    script_pattern = re.compile(r'<script[^>]+src=["\'](https?://(?:cdn\.jsdelivr\.net|unpkg\.com)[^"\']+)["\'][^>]*>', re.IGNORECASE)

    # Find all matching URLs
    urls_to_download = []
    
    for match in link_pattern.finditer(html_content):
        urls_to_download.append(match.group(1))
        
    for match in script_pattern.finditer(html_content):
        urls_to_download.append(match.group(1))

    # Download unique URLs
    urls_to_download = list(set(urls_to_download))
    downloaded_files = []
    
    modified_html = html_content

    print(f"Found {len(urls_to_download)} assets to download from CDNs.")

    for url in urls_to_download:
        print(f"Downloading: {url}")
        
        # Parse URL to get a clean filename
        parsed_url = urllib.parse.urlparse(url)
        path = parsed_url.path
        
        # Some CDNs have paths like /npm/library@version/dist/file.js
        # We need to extract a sensible filename, usually the last part
        filename = os.path.basename(path)
        
        # Check if the filename is empty or weird
        if not filename or filename == '/':
            # Use a fallback name based on the path
            filename = path.replace('/', '_').strip('_')
            
        # Ensure it has an extension based on the tag it came from if it doesn't have one
        if not (filename.endswith('.js') or filename.endswith('.css')):
            if 'css' in url.lower():
                filename += '.css'
            elif 'js' in url.lower():
                filename += '.js'

        # Since we might have multiple files with same name from different libraries, 
        # let's add the library name or path part to make it unique if possible
        # For jsdelivr: /npm/library@version/file -> library-file
        if 'cdn.jsdelivr.net/npm/' in url:
             parts = path.split('/')
             if len(parts) > 2:
                 lib_name = parts[2].split('@')[0] # Get library name, ignore version
                 if filename != lib_name and not filename.startswith(lib_name):
                    filename = f"{lib_name}_{filename}"
                    
        if 'unpkg.com/' in url:
             parts = path.split('/')
             if len(parts) > 1:
                 lib_name = parts[1].split('@')[0]
                 if filename != lib_name and not filename.startswith(lib_name):
                    filename = f"{lib_name}_{filename}"

        # Clean up any potential query parameters in the filename
        filename = filename.split('?')[0].split('#')[0]

        local_filepath = os.path.join(static_dir, filename)

        try:
            # Download the file
            req = urllib.request.Request(
                url, 
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            with urllib.request.urlopen(req) as response, open(local_filepath, 'wb') as out_file:
                shutil.copyfileobj(response, out_file)
            
            print(f"  -> Saved as {local_filepath}")
            downloaded_files.append((url, f"{static_dir}/{filename}"))
            
        except (URLError, HTTPError) as e:
            print(f"  -> Failed to download {url}: {e}")

    # Replace URLs in HTML
    for original_url, local_path in downloaded_files:
        # We replace the exact URL string with the local path
        # This is safe because the original_url is exactly what was matched
        modified_html = modified_html.replace(original_url, local_path)

    # Write the new HTML file
    with open(output_html_file, 'w', encoding='utf-8') as f:
        f.write(modified_html)
        
    print(f"\nCreated {output_html_file} with updated references.")
    print("\nSummary of downloaded files:")
    for _, local_path in downloaded_files:
        print(f"- {local_path}")

if __name__ == "__main__":
    download_assets()
