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

def get_politician_ids():
    total_list = {}
    for i in range(1, 4):
        total_list.update(scrape_politicians(gen_url(i)))
    return total_list

def gen_url_response(politician_list, politician_name):
    return f"https://www.capitoltrades.com/trades?politician={politician_list[politician_name]}&pageSize=100"

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

if __name__ == "__main__":
    app.run(debug=True)
