from flask import Flask, request, jsonify
import requests
import re
from bs4 import BeautifulSoup
from datetime import datetime

app = Flask(__name__)

def gen_url(number):
    response = requests.get(f"https://www.capitoltrades.com/politicians?sortBy=-volume&pageSize=96&page={number}")
    return response.text

def scrape_politicians(html):
    soup = BeautifulSoup(html, 'html.parser')
    politician = {}
    
    for card in soup.find_all('a', class_='index-card-link'):
        name_tag = card.find('h2', class_='font-medium leading-snug')
        politician_id = card['href'].split('/')[-1]
        
        if name_tag.text.strip() not in politician.keys():
            politician[name_tag.text.strip()] = politician_id
    
    return politician

def get_politician_names():
    total_list = {}

    for i in range(1, 4):
        html = gen_url(i)
        soup = BeautifulSoup(html, 'html.parser')

        for card in soup.find_all('a', class_='index-card-link'):
            name_tag = card.find('h2', class_='font-medium leading-snug')
            state_tag = card.find('h3')

            if not name_tag or not state_tag:  # Ensure elements exist
                continue

            response = state_tag.text.strip()
            party_match = re.search(r"(Democrat|Republican|Other)", response)

            if party_match:
                party = party_match.group()
                state = response[party_match.end():].strip()  # Extract state before the party
            else:
                party = "Unknown"
                state = response  # Keep the full response as state if no party is found

            total_list[name_tag.text.strip()] = [state, party]

    return total_list

def get_politician_ids():
    total_list = {}
    for i in range(1, 4):
        total_list.update(scrape_politicians(gen_url(i)))
    return total_list

def gen_url_response(politician_list, politician_name):
    return f"https://www.capitoltrades.com/trades?politician={politician_list[politician_name]}&pageSize=100"

def get_latest_trade_data():
    response = requests.get("https://www.capitoltrades.com/trades?pageSize=400")
    soup = BeautifulSoup(response.text, "html.parser")
    tbody = soup.find("tbody")
    
    if tbody:
        rows = tbody.find_all("tr")
        latest_trade_data = []
        
        for row in rows:
            cells = row.find_all("td")
            row_data = [cell.text.strip() for cell in cells]

            # Parse name + party + chamber + state
            header_info = re.match(r"^(.*?)(Democrat|Republican)(Senate|House)([A-Z]{2})$", row_data[0])
            if header_info:
                name = header_info.group(1).strip()
                party = header_info.group(2)
                chamber = header_info.group(3)
                state = header_info.group(4)
            else:
                name = row_data[0]
                party = chamber = state = "N/A"

            # Parse company + ticker
            company_ticker_match = re.match(r"^(.*?)([A-Z]+:US)$", row_data[1])
            if company_ticker_match:
                company = company_ticker_match.group(1).strip()
                ticker = company_ticker_match.group(2)
            else:
                company = row_data[1]
                ticker = "N/A"

            date_str = row_data[3].replace("Sept", "Sep")
            date_obj = datetime.strptime(date_str, "%d %b%Y")
            formatted_date = date_obj.strftime("%B %d, %Y")
            
            trade_data = [
                name,
                party,
                chamber,
                state,
                company,
                ticker,
                row_data[2],  # e.g., time
                formatted_date,
                row_data[4][4:] + " " + row_data[4][:4],  # e.g., reordered days
                row_data[6],  # buy/sell
                row_data[7].replace("\u2013", "-"),  # amount
                row_data[8]   # price
            ]
            latest_trade_data.append(trade_data)
        
        return latest_trade_data
    return []


def get_trade_data(politician_name):
    politician_list = get_politician_ids()
    if politician_name not in politician_list:
        return {"error": "Politician not found"}
    
    response = requests.get(gen_url_response(politician_list, politician_name))
    return_value = {"Politician": None, "Party": None, "TradesData": []}
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        tbody = soup.find("tbody")
        
        if tbody:
            rows = tbody.find_all("tr")
            
            for row in rows:
                cells = row.find_all("td")
                row_data = [cell.text.strip() for cell in cells]
                
                ticker_match = re.search(r"[A-Z]*:US", row_data[1])
                date_str = row_data[3].replace("Sept", "Sep")
                date_obj = datetime.strptime(date_str, "%d %b%Y")
                formatted_date = date_obj.strftime("%B %d, %Y")
                
                party_match = re.search(r"(Democrat|Republican)", row_data[0])
                
                if return_value["Politician"] is None:
                    return_value["Politician"] = row_data[0][:party_match.start()]
                
                if return_value["Party"] is None:
                    return_value["Party"] = party_match.group()
                
                try:
                    trade_data = [
                        ticker_match.group(), 
                        formatted_date, 
                        row_data[4][4:] + " " + row_data[4][:4], 
                        row_data[6], 
                        row_data[7].replace("\u2013", "-")
                    ]
                    return_value["TradesData"].append(trade_data)
                except:
                    continue
    
    return return_value

@app.route("/get_trades", methods=["GET"])
def get_trades():
    politician_name = request.args.get("name")
    if not politician_name:
        return jsonify({"error": "Please provide a politician's name"}), 400
    
    data = get_trade_data(politician_name)
    return jsonify(data)

@app.route("/get_politicians", methods=["GET"])
def get_politicians():
    return jsonify(get_politician_names())

@app.route("/get_latest_trades", methods=["GET"])
def get_latest_trades():
    data = get_latest_trade_data()
    return jsonify(data)

@app.route("/get_profile", methods=["GET"])
def get_profile():
    politician_name = request.args.get("name")
    if not politician_name:
        return jsonify({"error": "Please provide a politician's name"}), 400
    
    politician_list = get_politician_ids()
    
    if politician_name not in politician_list:
        return jsonify({"error": "Politician not found"}), 404

    # Get the politician's CapitolTrades profile URL
    politician_id = politician_list[politician_name]
    profile_url = f"https://www.capitoltrades.com/politicians/{politician_id}"

    # Send a request to the politician's profile page
    response = requests.get(profile_url)
    soup = BeautifulSoup(response.text, "html.parser")

    # Extract the required data from the profile page
    profile_data = {}

    # Number of Trades
    trades = soup.find("span", text="Trades")
    if trades:
        profile_data["Trades"] = trades.find_previous("span").text.strip()

    # Number of Issuers
    issuers = soup.find("span", text="Issuers")
    if issuers:
        profile_data["Issuers"] = issuers.find_previous("span").text.strip()

    # Volume
    volume = soup.find("span", text="Volume")
    if volume:
        profile_data["Volume"] = volume.find_previous("span").text.strip()

    # Last Traded Date
    last_traded = soup.find("span", text="Last Traded")
    if last_traded:
        profile_data["Last Traded"] = last_traded.find_previous("span").text.strip()

    # District
    district = soup.find("span", text="District")
    if district:
        profile_data["District"] = district.find_previous("span").text.strip()

    # Years Active (Fixing the en-dash to a regular dash)
    years_active = soup.find("span", text="Years Active")
    if years_active:
        years_active_text = years_active.find_previous("span").text.strip()
        profile_data["Years Active"] = years_active_text.replace("\u2013", "-")

    # Date of Birth
    date_of_birth = soup.find("span", text="Date of Birth")
    if date_of_birth:
        profile_data["Date of Birth"] = date_of_birth.find_previous("span").text.strip()

    # Age
    age = soup.find("span", text="Age")
    if age:
        profile_data["Age"] = age.find_previous("span").text.strip()

    # Extract data for Most Traded Issuers
    most_traded_issuers = {}
    issuers_section = soup.find("h2", string="Most Traded Issuers")
    if issuers_section:
        legend_items = issuers_section.find_next("ul", class_="chart-legend").find_all("li")
        for item in legend_items:
            label = item.find("span", class_="label").text.strip()
            value = item.find("span", class_="value").text.strip()
            most_traded_issuers[label] = value
    profile_data["Most Traded Issuers"] = most_traded_issuers

    # Extract data for Most Traded Sectors
    most_traded_sectors = {}
    sectors_section = soup.find("h2", string="Most Traded Sectors")
    if sectors_section:
        legend_items = sectors_section.find_next("ul", class_="chart-legend").find_all("li")
        for item in legend_items:
            label = item.find("span", class_="label").text.strip()
            value = item.find("span", class_="value").text.strip()
            most_traded_sectors[label] = value
    profile_data["Most Traded Sectors"] = most_traded_sectors

    # Call get_trade_data to include trade data
    trade_data = get_trade_data(politician_name)
    
    # Combine profile data and trade data
    profile_data["Trade Data"] = trade_data["TradesData"]

    return jsonify(profile_data)





if __name__ == "__main__":
    app.run(debug=True)
