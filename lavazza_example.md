### Example Extraction Pipeline for a product on the Lavazza web-site: 
[¡Tierra! For Planet - Caffè biologico in grani | Lavazza](https://www.lavazza.it/it/coffee-beans/tierra-organic-planet)


```python
from crawl4ai import *
from bs4 import BeautifulSoup
import re



text = ""
images = []
title = ""
url = "https://www.lavazza.it/it/coffee-beans/tierra-organic-planet"
async with AsyncWebCrawler() as crawler:
    result = await crawler.arun(
        url=url,
    )
    images = result.media.get("images", [])
    title = result.metadata["title"]
    soup = BeautifulSoup(result.html, "html.parser")
    div = soup.find(class_=["productDescriptionComponent"])
    
    if div:
        text = div.get_text(separator=" ").strip()
        text = re.sub(r'\s+', ' ', text)
        print(text)
    else:
        print("div not found")

```


<pre style="white-space:pre;overflow-x:auto;line-height:normal;font-family:Menlo,'DejaVu Sans Mono',consolas,'Courier New',monospace"><span style="color: #008080; text-decoration-color: #008080; font-weight: bold">[</span><span style="color: #008080; text-decoration-color: #008080">INIT</span><span style="color: #008080; text-decoration-color: #008080; font-weight: bold">]</span><span style="color: #008080; text-decoration-color: #008080">.... → Crawl4AI </span><span style="color: #008080; text-decoration-color: #008080; font-weight: bold">0.8</span><span style="color: #008080; text-decoration-color: #008080">.</span><span style="color: #008080; text-decoration-color: #008080; font-weight: bold">6</span><span style="color: #008080; text-decoration-color: #008080"> </span>
</pre>




<pre style="white-space:pre;overflow-x:auto;line-height:normal;font-family:Menlo,'DejaVu Sans Mono',consolas,'Courier New',monospace"><span style="color: #008000; text-decoration-color: #008000; font-weight: bold">[</span><span style="color: #008000; text-decoration-color: #008000">FETCH</span><span style="color: #008000; text-decoration-color: #008000; font-weight: bold">]</span><span style="color: #008000; text-decoration-color: #008000">... ↓ </span><span style="color: #008000; text-decoration-color: #008000; text-decoration: underline">https://www.lavazza.it/it/coffee-beans/tierra-organic-planet</span><span style="color: #008000; text-decoration-color: #008000">                                         |</span>
<span style="color: #008000; text-decoration-color: #008000">✓ | ⏱: </span><span style="color: #008000; text-decoration-color: #008000; font-weight: bold">2.</span><span style="color: #008000; text-decoration-color: #008000">49s </span>
</pre>




<pre style="white-space:pre;overflow-x:auto;line-height:normal;font-family:Menlo,'DejaVu Sans Mono',consolas,'Courier New',monospace"><span style="color: #008000; text-decoration-color: #008000; font-weight: bold">[</span><span style="color: #008000; text-decoration-color: #008000">SCRAPE</span><span style="color: #008000; text-decoration-color: #008000; font-weight: bold">]</span><span style="color: #008000; text-decoration-color: #008000">.. ◆ </span><span style="color: #008000; text-decoration-color: #008000; text-decoration: underline">https://www.lavazza.it/it/coffee-beans/tierra-organic-planet</span><span style="color: #008000; text-decoration-color: #008000">                                         |</span>
<span style="color: #008000; text-decoration-color: #008000">✓ | ⏱: </span><span style="color: #008000; text-decoration-color: #008000; font-weight: bold">0.</span><span style="color: #008000; text-decoration-color: #008000">10s </span>
</pre>




<pre style="white-space:pre;overflow-x:auto;line-height:normal;font-family:Menlo,'DejaVu Sans Mono',consolas,'Courier New',monospace"><span style="color: #008000; text-decoration-color: #008000; font-weight: bold">[</span><span style="color: #008000; text-decoration-color: #008000">COMPLETE</span><span style="color: #008000; text-decoration-color: #008000; font-weight: bold">]</span><span style="color: #008000; text-decoration-color: #008000"> ● </span><span style="color: #008000; text-decoration-color: #008000; text-decoration: underline">https://www.lavazza.it/it/coffee-beans/tierra-organic-planet</span><span style="color: #008000; text-decoration-color: #008000">                                         |</span>
<span style="color: #008000; text-decoration-color: #008000">✓ | ⏱: </span><span style="color: #008000; text-decoration-color: #008000; font-weight: bold">2.</span><span style="color: #008000; text-decoration-color: #008000">61s </span>
</pre>



    Profilo e tostatura Miscela Indicazioni tecniche Preparazioni Lavazza Profilo e tostatura Delicato e fruttato Una miscela delicata e scura con note di frutta tropicale e fiori. Note Aromatiche Floreale, Fruttato Tostatura Media Miscela Composizione 100% Arabica Origini Africa, America Centrale, Sud America Indicazioni tecniche Operatore del settore alimentare Luigi Lavazza S.p.A. - Via Bologna 32 - 10152 Torino - Italy Nome prodotto Caffè torrefatto in grani biologico Peso Netto 1 kg Preparazioni Lavazza I nostri consigli Espresso Guarda il video In una postazione caffè professionale, un trainer Lavazzaentra in campo. Rimuove il portafiltro dalla macchina espresso e lo riempie di caffè macinato. Compatta il caffè all’interno con il pressino. Dalla macchina, senza il portafiltro inserito, esce un getto d’acqua per la pulizia del gruppo erogatore. Poi il barista reinserisce il portafiltro nella macchina. I nostri consigli Moka GUARDA IL VIDEO In una cucina, un trainer Lavazza entra in campo. Riempe la moka con l’acqua, poi aggiunge il caffè macinato nel filtro e dà un piccolo colpo sul tavolo per livellarlo. Chiude la moka e la posa sul fornello acceso. Dopo pochi istanti, il caffè sale e riempie la parte superiore. Il barista versa il caffè caldo in una tazzina.


Crawl4AI already took care in colleciting the media from the website. It also has a scoring algorithm that can be configured to put importance on the media, but in the block bellow i just try to find the most important media that contains parts of the title of the page, which would most probably be our product image.


```python

from urllib.parse import urlparse

parsed = urlparse(result.url)
base_url = f"{parsed.scheme}://{parsed.netloc}"

# ["¡Tierra! For Planet Grani", "Lavazza"]
def find_product_image(images, product_name_keywords):
    
    scored = []
    for img in images:
        alt = img.get("alt", "").lower()
        desc = img.get("desc", "").lower()
        score = img.get("score", 0)
        
        keyword_match = any(k.lower() in alt or k.lower() in desc for k in product_name_keywords)
        
        if keyword_match and score > 3:
            scored.append(img)
    
    # sort by score descending
    return sorted(scored, key=lambda x: x["score"], reverse=True)
# drop short/generic words
# extract keywords from title
stop = {"for", "the", "and", "di", "in", "con", "a", "e", "il", "la", "le", "per"}
keywords = [
    w.strip("¡!|,")
    for w in title.split()
    if w.lower().strip("¡!|,") not in stop and len(w) > 2
]

product_images = find_product_image(images, keywords)
selected_image = product_images[0]
src = selected_image["src"]
url = base_url + src if src.startswith("/") else src
print(f"Product image URL: {url}")
# download image
import requests
response = requests.get(url)
if response.status_code == 200:
    with open(f"{title}.jpg", "wb") as f:
        f.write(response.content)
    print("Image downloaded successfully.")

```

    Product image URL: https://www.lavazza.it/content/dam/lavazza-athena/b2c/pdp-pag-prodotto/coffee/hero-product-banner/2-main-asset-coffee/tierra-2023/beans/planet/3363-d-tierra_planet-beans_1000-ita-%402.png
    Image downloaded successfully.


Bellow, I printed out the text I scraped from the product description html.


```python
text
```




    'Profilo e tostatura Miscela Indicazioni tecniche Preparazioni Lavazza Profilo e tostatura Delicato e fruttato Una miscela delicata e scura con note di frutta tropicale e fiori. Note Aromatiche Floreale, Fruttato Tostatura Media Miscela Composizione 100% Arabica Origini Africa, America Centrale, Sud America Indicazioni tecniche Operatore del settore alimentare Luigi Lavazza S.p.A. - Via Bologna 32 - 10152 Torino - Italy Nome prodotto Caffè torrefatto in grani biologico Peso Netto 1 kg Preparazioni Lavazza I nostri consigli Espresso Guarda il video In una postazione caffè professionale, un trainer Lavazzaentra in campo. Rimuove il portafiltro dalla macchina espresso e lo riempie di caffè macinato. Compatta il caffè all’interno con il pressino. Dalla macchina, senza il portafiltro inserito, esce un getto d’acqua per la pulizia del gruppo erogatore. Poi il barista reinserisce il portafiltro nella macchina. I nostri consigli Moka GUARDA IL VIDEO In una cucina, un trainer Lavazza entra in campo. Riempe la moka con l’acqua, poi aggiunge il caffè macinato nel filtro e dà un piccolo colpo sul tavolo per livellarlo. Chiude la moka e la posa sul fornello acceso. Dopo pochi istanti, il caffè sale e riempie la parte superiore. Il barista versa il caffè caldo in una tazzina.'



In this block I am defining a function that calls a locally hosted LLM called llama-3.2. It is an open source llm, that can be used freely on your local machine.
The intention of this function is to call the llm to extract the product claims present in a text.

In the ;ast line I pass the above extracted text and get some claims in a json format


```python
import httpx
import json


def extract_ucpd_claims(text: str) -> dict:
    system_prompt = """You are a regulatory analyst specializing in EU consumer protection law, 
specifically the Unfair Commercial Practices Directive (UCPD 2005/29/EC) and related regulations 
(EU Health Claims Regulation 1924/2006, EU Green Claims Directive).

Return a json object that contains:
- title: the title of the product - the most concise descriptive name you can give it based on the text (e.g. "Yogurt Greco 0% Grassi")
- company: the brand or company name if identifiable else None
- claims: an array of claims that may require regulatory verification under UCPD
For each claim return:
- claim_text: exact text as found
- category: HEALTH_CLAIM / ORIGIN_CLAIM / NATURALNESS_CLAIM / FREE_FROM_CLAIM / ENVIRONMENTAL_CLAIM / COMPARATIVE_CLAIM / ABSOLUTE_CLAIM
- risk_level: HIGH / MEDIUM / LOW
- reason: why it may need verification under UCPD
- regulation: applicable EU regulation

Return only a JSON object with the above structure, no other text."""

    response = httpx.post('http://localhost:11434/api/generate', json={
        'model': 'llama3.2',
        'system': system_prompt,
        'prompt': f'Extract all claims requiring regulatory verification from this product markdown text:\n\n{text} + \n\n And title {title}',
        'stream': False,
        'format': 'json'
    }, timeout=120)
    
    return json.loads(response.json()['response'])



claims = extract_ucpd_claims(text)
claims

```




    {'title': 'Caffè biologico in grani',
     'company': 'Lavazza',
     'claims': [{'claim_text': 'biologico',
       'category': 'NATURALNESS_CLAIM',
       'risk_level': 'LOW',
       'reason': "May require regulatory verification under UCPD as it makes a claim about the product's production method.",
       'regulation': 'EU Organic Regulation 834/2007'},
      {'claim_text': 'in grani',
       'category': 'NATURALNESS_CLAIM',
       'risk_level': 'LOW',
       'reason': "May require regulatory verification under UCPD as it makes a claim about the product's composition.",
       'regulation': 'EU Organic Regulation 834/2007'},
      {'claim_text': 'Africa, America Centrale, Sud America',
       'category': 'ORIGIN_CLAIM',
       'risk_level': 'LOW',
       'reason': "May require regulatory verification under UCPD as it makes a claim about the product's origin.",
       'regulation': 'None'}]}




```python
def print_claims(claims: dict):
    for c in claims['claims']:
        print(f"[{c['risk_level']}] {c['category']}: {c['claim_text']}")
        print(f"Reason: {c['reason']}")
        print(f"Category: {c['category']}\n")

    claims['title']
    claims['company']
    

```


```python
def save_claims_to_file(claims: dict, title: str):
    filename = f"{title}.json"
    
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(claims, f, indent=4)

    print(f"Saved to {filename}")

save_claims_to_file(claims, "website_claims_lavazza")

```

    Saved to website_claims_lavazza.json


I want to also extract some knowledge from the product image, since that is a big contact point for companies with consumers.
I do that by first transcribing all the text in the picture, and after passing it to the claims extractor function



```python
import base64
with open(f'{title}.jpg', 'rb') as f:
        img_b64 = base64.b64encode(f.read()).decode('utf-8')
with httpx.stream('POST', 'http://localhost:11434/api/generate', json={
    'model': 'llama3.2-vision',
    'prompt': '''Transcribe ALL text visible on this product packaging, exactly as written.
        Include every word, number, and phrase you can see, even if they are really small or partially obscured.
        Do not interpret or summarize - just transcribe.
        Return only the raw text, one item per line.''',
    'images': [img_b64],
    'stream': True,
}, timeout=180) as response:
    full_text = ""
    for line in response.iter_lines():
        if line:
            chunk = json.loads(line)
            full_text += chunk.get('response', '')
            if chunk.get('done'):
                break
            
full_text
```




    "**Lavazza Coffee Packaging Transcription**\n\n**Front of the Bag**\n\n* **Lavazza** (in large white letters)\n* **Torino, Italia, 1895** (in smaller white letters)\n* **1000g** (in small black letters)\n* **Organic Coffee Beans** (in small black letters)\n* **Lavazza** (in large white letters)\n\n**Center of the Bag**\n\n* **Tierra** (in large black letters)\n* **Bio-Organic** (in smaller black letters)\n* **For Planet** (in smaller green letters)\n* **100% Arabica** (in small black letters)\n* **Hand-Picked Coffee** (in small black letters)\n\n**Bottom of the Bag**\n\n* **6/10** (in small black letters)\n* **Black Coffee & Caffe Crema** (in small black letters)\n* **Lavazza** (in large white letters)\n* **Torino, Italia, 1895** (in smaller white letters)\n* **1000g** (in small black letters)\n\n**Back of the Bag**\n\n* **Lavazza** (in large white letters)\n* **Torino, Italia, 1895** (in smaller white letters)\n* **1000g** (in small black letters)\n* **Organic Coffee Beans** (in small black letters)\n* **Lavazza** (in large white letters)\n\n**Side of the Bag**\n\n* **Lavazza** (in large white letters)\n* **Torino, Italia, 1895** (in smaller white letters)\n* **1000g** (in small black letters)\n* **Organic Coffee Beans** (in small black letters)\n* **Lavazza** (in large white letters)\n\nNote: The text on the bag is mostly in Italian, so it's not possible to provide a complete and accurate translation. However, based on the context, it appears to be a description of the coffee's origin, ingredients, and certification."




```python
# extract claims from Image
text = full_text
claims = extract_ucpd_claims(text)
print_claims(claims)

```

    [LOW] NATURALNESS_CLAIM: Organic Coffee Beans
    Reason: May be a natural ingredient claim subject to verification under UCPD
    Category: NATURALNESS_CLAIM
    
    [MEDIUM] FREE_FROM_CLAIM: 100% Arabica
    Reason: May indicate the absence of other ingredients, subject to verification under UCPD
    Category: FREE_FROM_CLAIM
    
    [LOW] ORIGIN_CLAIM: Bio-Organic
    Reason: May be an origin claim subject to verification under UCPD
    Category: ORIGIN_CLAIM
    
    [LOW] ENVIRONMENTAL_CLAIM: For Planet
    Reason: May be an environmental claim subject to verification under UCPD
    Category: ENVIRONMENTAL_CLAIM
    

