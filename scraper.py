import requests
import re
from bs4 import BeautifulSoup
from datetime import datetime

# URL of the website containing the table

politicanList = {"Michael McCaul": "M001157", "Ro Khanna": "K000389", "Darrell Issa": "I000056", "Josh Gottheimer": "G000583"}

def genUrl(politicanName):
    return f"https://www.capitoltrades.com/trades?politician={politicanList[politicanName]}&pageSize=96"


# Fetch the HTML content
response = requests.get(genUrl("Michael McCaul"))

tradesData = list()

returnValue = {"Politician": None, "Party": None, "TradesData": list()}

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

            date_str = row_data[3]
            date_str = date_str.replace("Sept", "Sep")
            date_obj = datetime.strptime(date_str, "%d %b%Y")
            formatted_date = date_obj.strftime("%B %d, %Y")

            partyPattern = r"(Democrat|Republican)"
            searchPattern = re.search(partyPattern, row_data[0])
            
            #print(row_data[0][0:searchPattern.start() - 1])
            #print(row_data[0][searchPattern.start():searchPattern.end()])

            if(returnValue["Politician"] == None):
                returnValue["Politician"] = row_data[0][0:searchPattern.start() - 1]
            
            if(returnValue["Party"] == None):
                returnValue["Party"] = row_data[0][searchPattern.start():searchPattern.end()]

            #row_data[0][0:12], row_data[0][12:20],

            try:
                modifiedData = [ticker.group(), formatted_date, row_data[4][4:] + " " + row_data[4][:4], row_data[6], row_data[7]]
                #print(modifiedData)  # Print the row data as a list
                returnValue["TradesData"].append(modifiedData)
            except:
                continue
    else:
        print("No <tbody> found.")
else:
    print(f"Failed to retrieve the page. Status code: {response.status_code}")

print(returnValue)
