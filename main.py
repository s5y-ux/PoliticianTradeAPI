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


if __name__ == "__main__":
    app.run(debug=True)
