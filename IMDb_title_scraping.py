#!/usr/bin/env python
# coding: utf-8

import time
import streamlit as st
import pandas as pd
from PIL import Image
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup

# Set the path to the ChromeDriver (if not added to PATH)
chrome_driver_path = "chromedriver"
chrome_binary_path = "./chrome-linux64/chrome"

# Create a Service object
service = Service(chrome_driver_path)

# Set up Chrome options for headless mode
chrome_options = Options()
chrome_options.binary_location = chrome_binary_path  # Specify the path to Chrome binary
chrome_options.add_argument("--headless")  # Run Chrome in headless mode
chrome_options.add_argument("--no-sandbox")  # Bypass OS security model
chrome_options.add_argument("--disable-dev-shm-usage")  # Overcome limited resource problems
chrome_options.add_argument("--window-size=1920,1080")  # Set window size
chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36")

# Initialize the WebDriver instance using the Service object and Chrome options
driver = webdriver.Chrome(service=service, options=chrome_options)

class Generator:
    def __init__(self, gen):
        self.gen = gen
        self.value = None

    def __iter__(self):
        self.value = yield from self.gen

# Helper function to load an image for the sidebar
def load_image(image_path):
    with open(image_path, 'rb') as file:
        img = Image.open(file)
        return img

def scrape_imdb(url):
    # Load the IMDb page
    driver.get(url)  # Replace with your IMDb URL

    # Initialize WebDriverWait
    wait = WebDriverWait(driver, 5)

    # Wait for the initial page to load
    time.sleep(4)

    # Extract the total number of results using the updated method
    try:
        total_results_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '.sc-54d06b29-3')))
        total_results_str = total_results_element.text
        # Extracting the number from the first line
        first_line = total_results_str.split('\n')[0]
        total_results_number_str = first_line.split()[-1].replace('.', '').replace(',', '')
    except NoSuchElementException:
        print("Total number of results not found.")
        exit()
    except TimeoutException:
        print("Timeout reached extracting the total number of results.")
        exit()

    if total_results_number_str.isdigit():
        total_results = int(total_results_number_str)
    else:
        raise ValueError("Unable to extract total number of results as an integer")


    loaded_results = 0
    # Click the "50 more" button until all results are loaded
    while loaded_results < total_results:
        try:
            load_more_button = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '.ipc-see-more__text')))
            driver.execute_script("arguments[0].scrollIntoView(true);", load_more_button)

            # Use JavaScript to click the button
            driver.execute_script("arguments[0].click();", load_more_button)

            time.sleep(3)  # Wait for the page to load more results
            results_text = driver.find_element(By.CSS_SELECTOR, '.sc-54d06b29-3').text
            first_line = results_text.split('\n')[0]
            loaded_results_str = first_line.split('-')[-1].split()[0].replace('.', '').replace(',', '')
            if loaded_results_str.isdigit():
                loaded_results = int(loaded_results_str)
                # Calculate progress percentage
                progress_fraction = (loaded_results / total_results)
                yield progress_fraction
            else:
                raise ValueError("Unable to extract loaded results number as an integer")
        except Exception as e:
            print("Error:", e)
            break


    # Extract the HTML content
    html_content = driver.page_source
    # Create a BeautifulSoup object for parsing the HTML
    soup = BeautifulSoup(html_content, 'html.parser')

    # Use a set to store IMDB codes and ensure uniqueness
    imdb_codes_set = set()
    for tag in soup.find_all('a', href=True):
        if 'title/tt' in tag.get('href'):
            code = tag.get('href').split('/')[2].split('?')[0]
            imdb_codes_set.add(code)

    # Convert the set to a list for the DataFrame
    imdb_codes_list = list(imdb_codes_set)

    # Close the Selenium browser
    driver.quit()
    return imdb_codes_list

def main():
    # Sidebar with logo and instructions
    st.sidebar.image(load_image('logo_IMDb_scraper.webp'), use_column_width=True)
    st.sidebar.info("""
            Welcome to the IMDb scraping tool. To extract titles and related data from IMDb using an advanced search URL, follow these steps:

            1. Perform an advanced search on IMDb (IMDb Advanced Search) with desired criteria like genre, year, rating, etc.
            2. Copy the URL from the browser's address bar after viewing the results.
            3. Paste the copied URL into the designated field in the web app.
            4. Click the "Start Scraping" button to initiate data extraction from the listed titles.
            5. Upon completion, the results can be downloaded in CSV.

            Note: The search URL can be directly manipulated by using '!' to exclude parameters (e.g., 'genres=!drama') and including categories like 'country_of_origin' or 'primary_language' to personalize search parameters not available in IMDb's standard interface. Respect IMDb's terms of service and legal restrictions on web scraping.
        """)

    # Main app interface
    st.title("IMDb Web Scraper")

    # Text input for URL
    url = st.text_input("Enter the IMDb URL to scrape:")

    # Container for messages and progress bar
    status_container = st.empty()


    # Button to start scraping
    if st.button("Start Scraping") and url:
        progress_bar = st.progress(0)
        gen_wrapper = Generator(scrape_imdb(url))

        for progress in gen_wrapper:
            progress_bar.progress(progress)

        scraped_data = gen_wrapper.value

        if scraped_data:
            status_container.success("Scraping Completed!")
            results_df = pd.DataFrame({'IMDB_Code': scraped_data})
            csv_data = results_df.to_csv(index=False).encode('utf-8')
            st.download_button(label="Download Data as CSV", data=csv_data, file_name="scraped_data.csv",
                                   mime="text/csv")
        else:
            status_container.error("No data scraped.")

if __name__ == "__main__":
    main()
