import requests
from bs4 import BeautifulSoup
import re

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# === Selenium Driver 建立 ===
def get_selenium_driver():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# === 椰殼活性碳價格（Business Analytiq） ===
def fetch_coconut_prices():
    url = "https://businessanalytiq.com/procurementanalytics/index/activated-charcoal-prices/"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code != 200:
            return None
        soup = BeautifulSoup(res.text, "html.parser")
        result = {}
        heading = None
        for h3 in soup.find_all("h3"):
            if "activated carbon price" in h3.text.lower():
                heading = h3
                break
        if heading:
            ul = heading.find_next_sibling("ul")
            if ul:
                for li in ul.find_all("li"):
                    text = li.get_text(strip=True)
                    match = re.match(r"(.+):US\\$(\\d+\\.\\d+)/KG,?\\s*([-+]?\\d+\\.?\\d*)%?\\s*(up|down)?", text)
                    if match:
                        region = match.group(1).strip()
                        price = float(match.group(2))
                        change = float(match.group(3))
                        if match.group(4) == "down":
                            change = -abs(change)
                        date_match = re.search(r'([A-Za-z]+ \\d{4})', text)
                        date = date_match.group(1) if date_match else ""
                        result[region] = {"price": price, "change": change, "date": date}
        return result
    except Exception as e:
        print("Error fetching coconut price:", e)
        return None

# === FRED 替換：YCharts 煤質活性碳指數（用 Selenium） ===
def fetch_fred_from_ycharts():
    url = "https://ycharts.com/indicators/us_producer_price_index_coal_mining"
    driver = get_selenium_driver()
    driver.get(url)
    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table.table tbody tr"))
        )
        rows = driver.find_elements(By.CSS_SELECTOR, "table.table tbody tr")
        data = {}
        for row in rows:
            cells = row.find_elements(By.TAG_NAME, "td")
            if len(cells) == 2:
                label = cells[0].text.strip()
                value = cells[1].text.strip()
                data[label] = value

        latest_val = data.get("Last Value")
        period = data.get("Latest Period")
        change = data.get("Change from Last Month")
        return period, latest_val, change
    except Exception as e:
        print("Error fetching FRED YCharts with Selenium:", e)
        return None, None, None
    finally:
        driver.quit()

# === 溴素價格（改抓 table.tab2 最後一筆） ===
def fetch_bromine_details():
    driver = get_selenium_driver()
    url = "https://pdata.100ppi.com/?f=basket&dir=hghy&id=643#hghy_643"
    driver.get(url)
    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table.tab2 tr"))
        )
        rows = driver.find_elements(By.CSS_SELECTOR, "table.tab2 tr")
        data_rows = [row for row in rows if len(row.find_elements(By.TAG_NAME, "td")) >= 3]
        if not data_rows:
            return "❌ 找不到溴素資料列"

        last_row = data_rows[-1]
        tds = last_row.find_elements(By.TAG_NAME, "td")
        date = tds[0].text.strip()
        price = tds[1].text.strip()
        percent = tds[2].text.strip()
        return f"{date}：{price}（漲跌 {percent}）"
    except Exception as e:
        print("Error fetching bromine price:", e)
        return None
    finally:
        driver.quit()

# === CNYES 煤期貨列表頁擷取收盤價與漲跌幅與日期 ===
def fetch_cnyes_energy2_close_price(name_keywords):
    url = "https://www.cnyes.com/futures/energy2.aspx"
    headers = {"User-Agent": "Mozilla/5.0"}
    driver = get_selenium_driver()
    driver.get(url)
    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table tr"))
        )
        rows = driver.find_elements(By.CSS_SELECTOR, "table tr")
        for row in rows:
            cells = row.find_elements(By.TAG_NAME, "td")
            if len(cells) > 7:
                name = cells[1].text.strip()
                if any(k in name for k in name_keywords):
                    date = cells[0].text.strip()
                    close = cells[4].text.strip()
                    change = cells[5].text.strip()
                    return f"{name}：{date} 收盤價 {close}（漲跌 {change}）"
        return "❌ 未找到指定煤種資料"
    except Exception as e:
        return f"❌ 擷取失敗：{e}"
    finally:
        driver.quit()
