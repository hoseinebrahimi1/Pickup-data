import requests
import pandas as pd
import re
import time
import random
from bs4 import BeautifulSoup
import gspread
from gspread_dataframe import set_with_dataframe
from oauth2client.service_account import ServiceAccountCredentials

# ------------------- Step 1: جمع‌آوری slugها ----------------------

def fetch_all_slugs():
    slugs = []
    for page in range(1, 5):
        url = f'https://www.khanoumi.com/api/ntl/v1/products?cat_id=149&analytics_tag=CategoryPLP&page_number={page}&ut=bb264df4-e30f-441c-85f1-45f9c1f0a9e7&page_size=24'
        print(f" در حال پردازش صفحه {page}...")

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            items = data.get('data', {}).get('products', {}).get('items', [])

            if not items:
                print(f" صفحه {page} هیچ آیتمی نداشت!")
            else:
                page_slugs = [
                    item.get('slug') for item in items
                    if item.get('slug') and item.get('slug') != item.get('brand', {}).get('slug')
                ]
                slugs.extend(page_slugs)
                print(f" صفحه {page} | تعداد: {len(page_slugs)}")

        except requests.exceptions.Timeout:
            print(f" تایم‌اوت در صفحه {page}  سرور پاسخ نداد.")
        except Exception as e:
            print(f"خطای غیرمنتظره در صفحه {page}: {e}")

    print(f"جمع کل اسلاگ‌ها: {len(slugs)}")
    return slugs

# ------------------- Step 2: دریافت اطلاعات محصولات ----------------------

def fetch_product_details(slugs):
    all_products = []
    for slug in slugs:
        api_url = f"https://www.khanoumi.com/api/ntl/v1/products/slug/{slug}"
        try:
            response = requests.get(api_url, timeout=10)
            response.raise_for_status()
            product_data = response.json().get('data', None)
            if product_data:
                all_products.append(product_data)
            time.sleep(random.uniform(1, 2))
        except:
            continue
    return all_products

# ------------------- Step 3: استخراج SPF دقیق ----------------------

def extract_spf(namefa, description_htmlfa):
    # جستجو در namefa
    match_name = re.search(r'(اس\s?پی\s?اف|spf)\s?(\d+)', namefa, re.IGNORECASE)
    if match_name:
        return match_name.group(2)

    # جستجو در متن توضیحات HTML
    soup = BeautifulSoup(description_htmlfa or "", "html.parser")
    text = soup.get_text()
    match_desc = re.search(r'(SPF|spf|اس\s?پی\s?اف)\s?:?\s?(\+?\d+)', text)
    if match_desc:
        return match_desc.group(2)

    return "مقدار SPF یافت نشد"

# ------------------- Step 4: پردازش اطلاعات محصول ----------------------

def process_product_data(product):
    namefa = product.get('nameFa', '')
    sales_price = product.get('salesPrice', '')
    main_image_url = product.get('mainImageUrl', '')
    brand_namefa = product.get('brand', {}).get('nameFa', '')
    # اطمینان از اینکه weight دیکشنری است
    weight = product.get('weight') or {}
    weight_value = weight.get('value', '')
    weight_unit = weight.get('unit', '')
    description_htmlfa = product.get('descriptionHtmlFa', '')

    spf_value = extract_spf(namefa, description_htmlfa)
    description_clean = BeautifulSoup(description_htmlfa or "", "html.parser").get_text()

    return {
        "name": namefa,
        "picture": main_image_url,
        "price": sales_price,
        "brand name": brand_namefa,
        "capacity": f"{weight_value} {weight_unit}",
        "meta": description_clean,
        "spf": spf_value,
        "seller": "خانومی"
    }

# ------------------- Step 5: ذخیره در گوگل شیت ----------------------

def upload_to_google_sheets(df, spreadsheet_name, sheet_name, creds_path):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
    client = gspread.authorize(creds)
    sheet = client.open(spreadsheet_name).worksheet(sheet_name)

    # **اضافه کردن داده‌های جدید بدون حذف قبلی‌ها**
    sheet.append_rows(df.values.tolist(), value_input_option="RAW")

    print(f" داده‌ها به Google Sheets اضافه شدند! اکنون تعداد ردیف‌های موجود در شیت: {len(sheet.get_all_values())}")

# ------------------- اجرای کلی ----------------------

if __name__ == '__main__':
    print(" شروع عملیات دریافت و بارگذاری اطلاعات...")

    creds_path = r"C:\Users\artin\Desktop\Final project article\khanomi-product-1dc381b0a610.json"
    spreadsheet_name = "Data-sunscreen-products"
    sheet_name = "Data"

    slugs = fetch_all_slugs()
    raw_products = fetch_product_details(slugs)
    processed = [process_product_data(p) for p in raw_products]
    df = pd.DataFrame(processed)
    # رفع خطای JSON با جایگزینی NaN
    df = df.fillna('')

    print(f" تعداد محصول پردازش‌شده: {len(df)}")
    upload_to_google_sheets(df, spreadsheet_name, sheet_name, creds_path)

    print(" عملیات با موفقیت انجام شد.")
