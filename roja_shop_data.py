import time
import re
import pandas as pd
import gspread
from gspread_dataframe import set_with_dataframe
from oauth2client.service_account import ServiceAccountCredentials
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.firefox import GeckoDriverManager

# -------- تنظیمات --------
PLP_URL = "https://rojashop.com/shop/behdashti/skin-care-sub-sun-care"
GOOGLE_SHEET_NAME = "Data-sunscreen-products"
SHEET_TAB_NAME = "Data"
SELLER_NAME = "روژا شاپ"
CREDENTIALS_PATH = "C:/Users/artin/Desktop/Final project article/khanomi-product-1dc381b0a610.json"

# -------- راه‌اندازی مرورگر --------
options = Options()
options.add_argument("--headless")
driver = webdriver.Firefox(service=Service(GeckoDriverManager().install()), options=options)
driver.set_window_size(400, 800)  # تنظیم ابعاد موبایل
wait = WebDriverWait(driver, 10)

# -------- استخراج لینک‌های PDP از صفحه PLP --------
def get_product_links():
    driver.get(PLP_URL)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)
    
    products = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a.productLink")))
    links = []
    for p in products:  # بررسی همه کارت‌های PLP بدون محدودیت
        try:
            url = p.get_attribute("href")
            links.append({"url": url})
        except Exception as e:
            print(f"⚠️ خطا در استخراج لینک PDP: {e}")
    print(f"🔗 تعداد لینک‌های PDP استخراج‌شده: {len(links)}")
    return links

# -------- استخراج نام، تصویر، قیمت، متا، ویژگی حجم، نام برند و SPF از PDP --------
def extract_product_details(link_obj, idx):
    print(f"\n--- پردازش محصول #{idx+1} ---")
    driver.get(link_obj["url"])
    
    data = {
        "name": None,
        "picture": None,
        "price": None,
        "meta": None,
        "capacity": None,
        "brand_name": None,
        "spf": None,
        "seller": SELLER_NAME
    }
    
    # 1️⃣ استخراج نام محصول
    try:
        name_el = wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, "body > main > section.w-100.h-auto.my-2.my-lg-4.product-detail-breadcrumbs > div > div.row > div.col-12.col-lg-5 > div > div > div.flex-column.w-75 > h1")
        ))
        data["name"] = name_el.text.strip()
        print(f"✅ نام محصول: {data['name']}")
    except Exception as e:
        print(f"⚠️ خطا در استخراج نام محصول: {e}")
    
        # 3️⃣ استخراج قیمت
    try:
        price_el = wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, "body > main > section.w-100.h-auto.my-2.my-lg-4.product-detail-breadcrumbs > div > div.row > div.product-price > div > div > div.col-8 > div > strong")
        ))
        price_text = price_el.text.strip()
        print(f"DEBUG: متن دریافت‌شده از المنت قیمت: '{price_text}'")
        match = re.search(r"(\d[\d,]*)", price_text)
        data["price"] = match.group(1).replace(",", "") if match else None
        print(f"✅ قیمت: {data['price']}")
    except Exception as e:
        print(f"⚠️ خطا در استخراج قیمت: {e}")
    
    # 2️⃣ استخراج تصویر محصول
    try:
        img_el = wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, "body > main > section.w-100.h-auto.my-2.my-lg-4.product-detail-breadcrumbs > div > div.row > div.col-12.col-lg-4.d-flex > div > a > img")
        ))
        data["picture"] = img_el.get_attribute("src")
        print(f"✅ تصویر محصول: {data['picture']}")
    except Exception as e:
        print(f"⚠️ خطا در استخراج تصویر محصول: {e}")
    
    # 4️⃣ استخراج متا
    try:
        meta_container = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#product-discription-tab-pane > div")))
        try:
            more_button = meta_container.find_element(By.CSS_SELECTOR, "button")
            driver.execute_script("arguments[0].click();", more_button)
            time.sleep(1)
        except Exception:
            pass
        full_meta = driver.execute_script("return arguments[0].innerText;", meta_container)
        data["meta"] = full_meta.strip()
        print(f"✅ متا (کامل): {data['meta']}")
    except Exception as e:
        print(f"⚠️ خطا در استخراج متا: {e}")
      # 5️⃣ استخراج ویژگی حجم محصول
    try:
        properties_tab_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#product-properties-tab")))
        driver.execute_script("arguments[0].click();", properties_tab_btn)
        time.sleep(1)
        properties_container = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#product-properties-tab-pane")))
        rows = properties_container.find_elements(By.TAG_NAME, "tr")
        capacity_value = None
        for row in rows:
            try:
                header_text = row.find_element(By.TAG_NAME, "th").text.strip()
                if "حجم محصول" in header_text:
                    cell_text = row.find_element(By.TAG_NAME, "td").text.strip()
                    match_capacity = re.search(r"(\d+)", cell_text)
                    if match_capacity:
                        capacity_value = match_capacity.group(1)
                        break
            except Exception:
                continue
        data["capacity"] = capacity_value
        print(f"✅ حجم محصول: {data['capacity']}")
    except Exception as e:
        print(f"⚠️ خطا در استخراج حجم محصول: {e}")

    # 6️⃣ استخراج نام برند از آخرین کلمه‌ی نام محصول
    try:
        if data["name"]:
            brand_name = data["name"].split()[-1]  # آخرین کلمه از نام محصول
            data["brand_name"] = brand_name
            print(f"✅ نام برند (آخرین کلمه از نام محصول): {data['brand_name']}")
        else:
            print("❌ نام محصول وجود ندارد، بنابراین برند قابل استخراج نیست.")
    except Exception as e:
        print(f"⚠️ خطا در استخراج نام برند از نام محصول: {e}")



    # 5️⃣ استخراج SPF (فقط عدد)
    try:
        spf_value = None
        if data["name"]:
            match_spf = re.search(r"SPF(\d+)", data["name"], re.IGNORECASE)
            if match_spf:
                spf_value = match_spf.group(1)

        if not spf_value and data["meta"]:
            match_spf_meta = re.search(r"SPF(\d+)", data["meta"], re.IGNORECASE)
            if match_spf_meta:
                spf_value = match_spf_meta.group(1)

        data["spf"] = spf_value
        print(f"✅ مقدار SPF (فقط عدد): {data['spf']}")
    except Exception as e:
        print(f"⚠️ خطا در استخراج SPF: {e}")
        data["spf"] = None

    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(1)
    
    return data

# -------- پردازش و آپلود به Google Sheets --------
links = get_product_links()
products = [extract_product_details(link, i) for i, link in enumerate(links)]
df = pd.DataFrame(products)

# احراز هویت با Google Sheets
creds = ServiceAccountCredentials.from_json_keyfile_name(
    CREDENTIALS_PATH,
    ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
)
client = gspread.authorize(creds)
sheet = client.open(GOOGLE_SHEET_NAME).worksheet(SHEET_TAB_NAME)

# **اضافه کردن داده‌های جدید بدون حذف قبلی‌ها**
sheet.append_rows(df.values.tolist(), value_input_option="RAW")
print(f"✅ داده‌ها اضافه شدند! اکنون تعداد ردیف‌های موجود در Google Sheets: {len(sheet.get_all_values())}")

driver.quit()
