import requests
from bs4 import BeautifulSoup
import json

def get_ollama_models():
    url = "https://ollama.com/search"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    models = []
    
    # Find all model entries
    for model_div in soup.find_all('li', {'x-test-model': True}):
        # Extract model name
        name_tag = model_div.find('span', {'x-test-search-response-title': True})
        if not name_tag:
            continue
        model_name = name_tag.text.strip()
        
        # Extract model sizes
        sizes = []
        for size_tag in model_div.find_all('span', {'x-test-size': True}):
            size = size_tag.text.strip().lower()
            sizes.append(f"{model_name}:{size}")
        
        models.extend(sizes)
    
        with open('data/models.json', 'w') as f:
            json.dump(models, f, indent=2)