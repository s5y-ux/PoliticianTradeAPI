#driver.get("https://www.capitoltrades.com/politicians/P000197")
import requests
import re
from bs4 import BeautifulSoup
from datetime import datetime

# URL of the website containing the table
url = "https://www.capitoltrades.com/trades?politician=P000197&pageSize=96"
#url = "https://www.capitoltrades.com/trades?politician=P000608&pageSize=96"

# Fetch the HTML content
response = requests.get(url)

tradesData = list()

# Check if the request was successful
if response.status_code == 200:
    html_content = response.text

    # Parse the HTML content with BeautifulSoup
    soup = BeautifulSoup(html_content, "html.parser")

    # Find the tbody element (by class or ID if necessary)
    tbody = soup.find("tbody")  # Add class_="..." or id="..." if needed



    if tbody:
        # Find all rows within the tbody
        rows = tbody.find_all("tr")

        # Extract data from each row
        for row in rows:
            # Find all cells (td elements) in the row
            cells = row.find_all("td")
            
            # Extract text from each cell
            row_data = [cell.text.strip() for cell in cells]
            #print(row_data)

            pattern = r"[A-Z]*:US"
            ticker = re.search(pattern, row_data[1])

            date_str = row_data[2]
            date_str = date_str.replace("Sept", "Sep")
            date_obj = datetime.strptime(date_str, "%d %b%Y")
            formatted_date = date_obj.strftime("%B %d, %Y")

            try:
                modifiedData = [row_data[0][0:12], row_data[0][12:20], ticker.group(), formatted_date, row_data[4][4:] + " " + row_data[4][:4], row_data[6], row_data[7]]
                print(modifiedData)  # Print the row data as a list
            except:
                continue
    else:
        print("No <tbody> found.")
else:
    print(f"Failed to retrieve the page. Status code: {response.status_code}")
