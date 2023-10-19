import requests
import scrapy
from scrapy.selector import Selector
from slugify import slugify
import pandas as pd
import random
from bs4 import BeautifulSoup
import urllib
import os
from amazoncaptcha import AmazonCaptcha
import concurrent
import re
import six


SEARCH_URL = "https://www.amazon.in/gp/aw/s/ref=nb_sb_noss?k=bags&sprefix=bags&page={}"
items = list()
def keyword_search(session,page,url):
    url = url.format(str(page))
    return session.get(url)

def to_unicode(text, encoding=None, errors='strict'):
    """Return the unicode representation of a bytes object `text`. If `text`
    is already an unicode object, return it as-is."""
    if isinstance(text, six.text_type):
        return text
    if not isinstance(text, (bytes, six.text_type)):
        raise TypeError('to_unicode must receive a bytes, str or unicode '
                        'object, got %s' % type(text).__name__)
    if encoding is None:
        encoding = 'utf-8'
    return text.decode(encoding, errors)

def remove_tags(text, which_ones=(), keep=(), encoding=None):
    """ Remove HTML Tags only.

    `which_ones` and `keep` are both tuples, there are four cases:

    ==============  ============= ==========================================
    ``which_ones``  ``keep``      what it does
    ==============  ============= ==========================================
    **not empty**   empty         remove all tags in ``which_ones``
    empty           **not empty** remove all tags except the ones in ``keep``
    empty           empty         remove all tags
    **not empty**   **not empty** not allowed
    ==============  ============= ==========================================


    Remove all tags:

    >>> import w3lib.html
    >>> doc = '<div><p><b>This is a link:</b> <a href="http://www.example.com">example</a></p></div>'
    >>> w3lib.html.remove_tags(doc)
    u'This is a link: example'
    >>>

    Keep only some tags:

    >>> w3lib.html.remove_tags(doc, keep=('div',))
    u'<div>This is a link: example</div>'
    >>>

    Remove only specific tags:

    >>> w3lib.html.remove_tags(doc, which_ones=('a','b'))
    u'<div><p>This is a link: example</p></div>'
    >>>

    You can't remove some and keep some:

    >>> w3lib.html.remove_tags(doc, which_ones=('a',), keep=('p',))
    Traceback (most recent call last):
        ...
    ValueError: Cannot use both which_ones and keep
    >>>

    """
    if which_ones and keep:
        raise ValueError('Cannot use both which_ones and keep')

    which_ones = {tag.lower() for tag in which_ones}
    keep = {tag.lower() for tag in keep}

    def will_remove(tag):
        tag = tag.lower()
        if which_ones:
            return tag in which_ones
        else:
            return tag not in keep

    def remove_tag(m):
        tag = m.group(1)
        return u'' if will_remove(tag) else m.group(0)

    regex = '</?([^ >/]+).*?>'
    retags = re.compile(regex, re.DOTALL | re.IGNORECASE)

    return retags.sub(remove_tag, to_unicode(text, encoding))


def parse_list_page(response):
        
        selector = Selector(text=response.text)
        products = selector.xpath("//div[re:test(@class, 's-result-item\s*s-asin\s*[^$]+$') and @data-component-type='s-search-result']").extract()
        if len(products) < 0:
            products = selector.xpath("//span[contains(@cel_widget_id,'MAIN-SEARCH_RESULTS')]").extract()
        rank = 1        
        sponsored_brand = selector.xpath("//div[re:test(@cel_widget_id, 'multi-card-creative-desktop_loom-desktop-top-slot_\d+')]").re_first(r'script>\s*<a\s*aria-hidden=\s*"false"\s*aria-label\s*=\s*"Sponsored\s*ad\s*from\s*([^&]+)&')
        if sponsored_brand == None:
            sponsored_brand = ""
        else:
            sponsored_brand = sponsored_brand.strip()
        for product in products:
            
            item = dict()
            sel = Selector(text=product)

            try:
                pdp_page_url = sel.xpath("//span[@data-component-type='s-product-image']/a/@href").get()
            except (TypeError, AttributeError, ValueError) as te:
                pdp_page_url = ""
    
            
            try:
                web_pid = sel.xpath("//div[re:test(@class, 's-result-item\s*s-asin\s*[^$]+$') and @data-component-type='s-search-result']/@data-asin").get()
            except (TypeError, AttributeError, ValueError) as te:
                web_pid = ""

            name = ""
            try:
                name = sel.css('.a-color-base.a-text-normal::text').get()
            except Exception as e:
                print('Name Test not found')

            if not name:
                try:
                    name = sel.xpath("//h2/a/span[@class='a-size-base-plus a-color-base a-text-normal']/text()").get()
                    if name is None:
                        name=sel.xpath("//h2/a/span[@class='a-size-base-plus a-color-base a-text-normal']/text()").get()
                    if name is None:
                        name=sel.xpath("//h2/a/span[@class='a-size-medium a-color-base a-text-normal']/text()").get()
                except (TypeError, AttributeError, ValueError) as te:
                    name = ""



            try:
                price = sel.xpath("//span[@class='a-price-whole']/text()").get()
                if price is None:
                    price = 0
                else:
                    price = str(price).strip().replace(",", "").replace("₹", "")
            except (TypeError, AttributeError, ValueError) as te:
                price = 0
            

            try:
                rating = sel.xpath("//div[@class='a-row a-size-small']/span[1]/@aria-label").get()
                if rating is None:
                    rating = 0
                else:
                    rating = rating.strip().replace("out of 5 stars", "").strip()
            except (TypeError, AttributeError, ValueError) as te:
                rating = 0.0

            try:
                review = sel.xpath("//div[@class='a-row a-size-small']/span[2]/@aria-label").get()
                if review is None:
                    review = 0
                else:
                    review = review.strip().replace(",", "")
            except (TypeError, AttributeError, ValueError) as te:
                review = 0.0


            item["web_pid"] = web_pid if web_pid else ""
            item["pdp_title_value"] = name if name else ""
            item["price_sp"] = price if price else 0
            item["pdp_rating_value"] = rating if rating else 0
            item["pdp_rating_count"] = review if review else 0
            item["pdp_page_url"] = "https://www.amazon.in/"+slugify(name)+"/dp/"+web_pid          

            items.append(item)


for page in range(1, 21):
    # keyword_res = keyword_search(session,page=page, url=SEARCH_URL)
    # print(keyword_res)
    session=requests.Session()

    ua_list = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:94.0) Gecko/20100101 Firefox/94.0'
    ]

    session.headers.update({
                'user-agent': random.choice(ua_list)
            })
    n=20
    for i in range(0,n):
        keyword_res = keyword_search(session,page=page, url=SEARCH_URL)
        if(keyword_res.status_code==200):
            break
    print(keyword_res)
    if keyword_res and keyword_res.status_code < 400:
        all_items = parse_list_page(keyword_res)
        print(page,"Page Done with",len(items),"products")



phase_1_data=pd.DataFrame(items)

phase_1_data.to_csv('Part_1.csv', index=False)

def captcha_resolve(session,soup,n,i):
    image_tags = soup.find_all("img", src=lambda src: src and ".jpg" in src)
    i=str(image_tags)
    img_link=i[11:-4]
    file_cap_path="C:/var/logs/amz_pdp/Captcha"

    if os.path.exists(file_cap_path):
        print(f"The directory '{file_cap_path}' exists.")
    else:
        os.makedirs(file_cap_path)
    file_img = "C:/var/logs/amz_pdp/Captcha/test_"+str(i)+str(n)+".jpg"
    if os.path.exists(file_img):
        print(f"The file '{file_img}' exists.")
    else:
        # Create the file test2.png
        with open(file_img, "w"):
            pass
    urllib.request.urlretrieve(img_link, file_img)
    captcha = AmazonCaptcha(file_img)
    cap_text = captcha.solve()
    print(cap_text)
    amzn = soup.find('input', {'name': 'amzn'}).get('value')
    amzn_r = soup.find('input', {'name': 'amzn-r'}).get('value')
    url="https://www.amazon.in/errors/validateCaptcha?amzn="+str(urllib.parse.quote(amzn))+"&amzn-r="+str(urllib.parse.quote(amzn_r))+"&field-keywords="+str(cap_text)
    response = session.get(url=url)
    if(response==None):
        response = session.get(url=url)
    return response

def product_detail(response):
    response_selector = Selector(text=response)
    soup = BeautifulSoup(response, 'html.parser')

    center_col = response_selector.xpath("//div[@id='centerCol']").get()        
    if center_col != None:            
        # center_col_sel = Selector(text=center_col)
        product_details=""
        extracted_web_pid=""
        manufacturer=""
        product_description=""

        if "<h2>Product details</h2>" in response:
            
            product_dtls_sel = Selector(text=response_selector.xpath("//div[@id='detailBulletsWrapper_feature_div']").get())
            technical_details = product_dtls_sel.xpath("//div[@id='detailBulletsWrapper_feature_div']")
            #additional_information = product_dtls_sel.xpath("//div[@id='productDetails_db_sections']")
            product_details = product_dtls_sel.xpath("//div[@id='detailBullets_feature_div']/text()").get()
            extracted_web_pid = technical_details.re_first(r'<span class="a-text-bold">\s*ASIN\s*[^:]+:\s*[^<]+</span>\s*<span>([^<]*)<')

            
        elif '<div id="prodDetails" class="a-section">' in response:
            product_dtls_sel = Selector(text=response_selector.xpath("//div[@id='prodDetails']").get())
            product_details = product_dtls_sel.xpath("//table[@id='productDetails_techSpec_section_1']/text()").get()
            additional_information = product_dtls_sel.xpath("//div[@id='productDetails_db_sections']")
            technical_details = product_dtls_sel.xpath("//table[@id='productDetails_techSpec_section_1']")
            extracted_web_pid = additional_information.re_first(r'prodDetSectionEntry">\s*ASIN\s*</th>\s*<td[^>]+>\s*([^<]+)<')

            manufacturer = technical_details.re_first(r'prodDetSectionEntry">\s*Manufacturer\s*</th>\s*<[^>]+>\s*([^<]+)<')
        else:
            product_details = ""


        try:
            product_desc_sel = Selector(text=response_selector.xpath("//div[@id='descriptionAndDetails']").get())
            product_description = product_desc_sel.xpath("//div[@id='productDescription']").get()
        except ValueError as ve:
            try:
                product_desc_sel = Selector(text=response_selector.xpath("//div[@id='productDescription_feature_div']").get())
                product_description = product_desc_sel.xpath("//div[@id='productDescription']").get()
            except:
                product_description = ""
        

        item = dict()            
        item["product_details"] = product_details and remove_tags(product_details.replace("\n","")) or ""
        item["manufacturer"] = manufacturer if manufacturer else ""
        item["ASIN"] = extracted_web_pid if extracted_web_pid else ""
        item["pdp_desc_value"] = product_description and remove_tags(product_description.replace("\n","")) or "" 
        
        return item

part2_data=[]
def start(item):
    url=item["pdp_page_url"]
    headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "text/html,*/*",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": url
            }
    cookies={
                "amzn-app-id": "Amazon.in/20.04.0.350/20.04.0.350",
                "i18n-prefs":"INR",
                "lc-acbin":"en_IN",                                         
                "visitCount": "1"
                }
    session=requests.Session()
    pdp_response=session.get(url=url,headers=headers,cookies=cookies)

    soup = BeautifulSoup(pdp_response.text, 'html.parser')
    print("Sent request for",url)
    captcha_text = "we just need to make sure you're not a robot"
    n=5
    for i in range(0,n):
        if(pdp_response.status_code==200 and pdp_response.text!=None):
            soup = BeautifulSoup(pdp_response.text, 'html.parser')
        if captcha_text in soup.get_text():
            pdp_response=captcha_resolve(soup,i,n)
        else:
            break
    print("Got response for",url)
    data=product_detail(pdp_response.text)
    if data is not None:
        item["Description"] = data.get("product_details", "")
        item["ASIN"] = data.get("ASIN", "")
        item["Product Description"] = data.get("pdp_desc_value", "")
        item["Manufacturer"] = data.get("manufacturer", "")
        part2_data.append(item)
        print("item size",len(part2_data))

def runner():
    threads = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        for input in items:
            task = executor.submit(start, input)
            threads.append(task)
           
        for task in concurrent.futures.as_completed(threads):
            print(task.result()) 

runner()

phase_2_data=pd.DataFrame(part2_data)

phase_2_data.to_csv('Part_2.csv', index=False)


