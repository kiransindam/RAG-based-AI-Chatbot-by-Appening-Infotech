import os
import requests

def download_ebook():
    # This is the link to the ebook from the assignment
    ebook_url = "https://konverge.ai/pdf/Ebook-Agentic-AI.pdf"
    output_filename = "ebook.pdf"
    
    print(f"Starting download from: {ebook_url} ...")
    
    # Let's request the file from the URL
    response = requests.get(ebook_url)
    
    # Check if we got it successfully (HTTP status 200)
    if response.status_code == 200:
        # Save the bytes into a local file
        with open(output_filename, "wb") as f:
            f.write(response.content)
        print(f"Success! The Agentic AI has been saved as {output_filename}")
    else:
        print(f"Failed to download the Agentic AI. Server returned status code: {response.status_code}")

if __name__ == "__main__":
    download_ebook()
