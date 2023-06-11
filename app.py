from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
import json
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

STATES = ["GA", "MA"]

state_abbreviations = {
    "AL": "Alabama",
    "AK": "Alaska",
    "AZ": "Arizona",
    "AR": "Arkansas",
    "CA": "California",
    "CO": "Colorado",
    "CT": "Connecticut",
    "DE": "Delaware",
    "FL": "Florida",
    "GA": "Georgia",
    "HI": "Hawaii",
    "ID": "Idaho",
    "IL": "Illinois",
    "IN": "Indiana",
    "IA": "Iowa",
    "KS": "Kansas",
    "KY": "Kentucky",
    "LA": "Louisiana",
    "ME": "Maine",
    "MD": "Maryland",
    "MA": "Massachusetts",
    "MI": "Michigan",
    "MN": "Minnesota",
    "MS": "Mississippi",
    "MO": "Missouri",
    "MT": "Montana",
    "NE": "Nebraska",
    "NV": "Nevada",
    "NH": "New-Hampshire",
    "NJ": "New-Jersey",
    "NM": "New-Mexico",
    "NY": "New-York",
    "NC": "North-Carolina",
    "ND": "North-Dakota",
    "OH": "Ohio",
    "OK": "Oklahoma",
    "OR": "Oregon",
    "PA": "Pennsylvania",
    "RI": "Rhode-Island",
    "SC": "South-Carolina",
    "SD": "South-Dakota",
    "TN": "Tennessee",
    "TX": "Texas",
    "UT": "Utah",
    "VT": "Vermont",
    "VA": "Virginia",
    "WA": "Washington",
    "WV": "West-Virginia",
    "WI": "Wisconsin",
    "WY": "Wyoming",
    "DC": "District-of-Columbia",
}

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
db = SQLAlchemy(app)

class FederalTaxBracket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rate = db.Column(db.Float, nullable=False)
    income_min = db.Column(db.Float, nullable=False)
    income_max = db.Column(db.Float)
    total_tax_prior_brackets = db.Column(db.Float)
    
    def to_dict(self):
        return {
        'id': self.id,
        'rate': self.rate,
        'income_min': self.income_min,
        'income_max': self.income_max,
        'total_tax_prior_brackets': self.total_tax_prior_brackets
    }


class StateTaxBracket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    state = db.Column(db.String, nullable=False)
    rate = db.Column(db.Float, nullable=False)
    income_min = db.Column(db.Float, nullable=False)
    income_max = db.Column(db.Float)
    total_tax_prior_brackets = db.Column(db.Float)
    
    def to_dict(self):
        return {
        'id': self.id,
        'rate': self.rate,
        'income_min': self.income_min,
        'income_max': self.income_max,
        'total_tax_prior_brackets': self.total_tax_prior_brackets
    }
        
class StateStandardDeduction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    state = db.Column(db.String, nullable=False)
    filing_status = db.Column(db.String(20), nullable=False)
    amount = db.Column(db.Float, nullable=False)

class FederalStandardDeduction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filing_status = db.Column(db.String(20), nullable=False)
    amount = db.Column(db.Float, nullable=False)

def import_federal_tax_data(year=2023):
    with open("TaxData/"+str(year)+'/Fed_Tax.json') as file:
        data = json.load(file)

    for bracket in data['tax_brackets']:
        tax = FederalTaxBracket(rate=bracket['rate'], income_min=bracket['income_min'], income_max=bracket['income_max'], total_tax_prior_brackets=bracket['total_tax_prior_brackets'])
        db.session.add(tax)

    for status, amount in data['standard_deduction'].items():
        deduction = FederalStandardDeduction(filing_status=status, amount=amount)
        db.session.add(deduction)

    db.session.commit()
    print("Tax data imported successfully!")

def import_state_tax_data(year=2023, state='GA'):
    with open("TaxData/"+str(year)+'/'+str(state)+'_Tax.json') as file:
        data = json.load(file)

    for bracket in data['tax_brackets']:
        tax = StateTaxBracket(rate=bracket['rate'], income_min=bracket['income_min'], income_max=bracket['income_max'], total_tax_prior_brackets=bracket['total_tax_prior_brackets'], state=state)
        db.session.add(tax)

    for status, amount in data['standard_deduction'].items():
        deduction = StateStandardDeduction(filing_status=status, amount=amount, state=state)
        db.session.add(deduction)

    db.session.commit()
    print("Tax data imported successfully!")

@app.route('/state_tax_brackets', methods=['GET'])
def get_state_tax_brackets():
    state = request.args.get('state')
    
    # Retrieve all StateTaxBracket objects for the specified state
    brackets = StateTaxBracket.query.filter_by(state=state).all()
    
    # Convert the objects to dictionaries
    brackets_dict = [bracket.to_dict() for bracket in brackets]
    
    return jsonify(brackets_dict)

@app.route('/api/federaltaxbrackets', methods=['GET'])
def federaltaxbrackets():
    return jsonify([x.to_dict() for x in FederalTaxBracket.query.all()])


@app.route('/calculate_state_tax', methods=['POST'])
def calculate_state_tax():
    income = request.json['income']
    state = request.args.get('state')
    
    # Retrieve all StateTaxBracket objects for the specified state
    brackets = StateTaxBracket.query.filter_by(state=state).all()
    deductions = StateStandardDeduction.query.filter_by(state=state).all()

    applicable_deduction = None
    for deduction in deductions:
        if deduction.filing_status == 'single':
            applicable_deduction = deduction
            break
    print("User has state deduction of amount: " + str(applicable_deduction.amount))

    new_income = income - applicable_deduction.amount
    # Find the applicable tax bracket based on the income
    applicable_bracket = None
    for bracket in brackets:
        if bracket.income_max != None:
            if bracket.income_min <= new_income <= bracket.income_max:
                applicable_bracket = bracket
                break
        else:
            if bracket.income_min <= new_income:
                applicable_bracket = bracket
                break

    print("With a taxable income of " + str(new_income) + ", user is in the " + str(applicable_bracket.rate) + " bracket")
    # Find the applicable standard deduction based on the income
    
    # Calculate the federal tax amount
    print("User owes " + str(applicable_bracket.total_tax_prior_brackets) + " for prior brackets")
    print("User pays " + str(applicable_bracket.rate) + " on " + str(new_income) + " - " + str(applicable_bracket.income_min) + "(" + str(new_income - applicable_bracket.income_min) +")")
    tax_amount = ((new_income - applicable_bracket.income_min) * (applicable_bracket.rate/100)) + applicable_bracket.total_tax_prior_brackets

    # Prepare the response JSON
    response = {
        'income': income,
        'taxable_income': new_income,
        'tax_amount': tax_amount,
        'takehome_pay': income-tax_amount
    }

    return jsonify(response)


# For rental property data: https://app.rentcast.io/app/api
# What I can do is use this https://www.rent.com/massachusetts/cambridge-apartments/rent-trends and scrape it

@app.route('/calculate_federal_tax', methods=['POST'])
def calculate_federal_tax():
    income = request.json['income']
    brackets = FederalTaxBracket.query.all()
    deductions = FederalStandardDeduction.query.all()

    applicable_deduction = None
    for deduction in deductions:
        if deduction.filing_status == 'single':
            applicable_deduction = deduction
            break
    print("User has deduction of amount: " + str(applicable_deduction.amount))

    new_income = income - applicable_deduction.amount
    # Find the applicable tax bracket based on the income
    applicable_bracket = None
    for bracket in brackets:
        if bracket.income_max != None:
            if bracket.income_min <= new_income <= bracket.income_max:
                applicable_bracket = bracket
                break
        else:
            if bracket.income_min <= new_income:
                applicable_bracket = bracket
                break

    print("With a taxable income of " + str(new_income) + ", user is in the " + str(applicable_bracket.rate) + " bracket")
    # Find the applicable standard deduction based on the income
    
    # Calculate the federal tax amount
    print("User owes " + str(applicable_bracket.total_tax_prior_brackets) + " for prior brackets")
    print("User pays " + str(applicable_bracket.rate) + " on " + str(new_income) + " - " + str(applicable_bracket.income_min) + "(" + str(new_income - applicable_bracket.income_min) +")")
    tax_amount = ((new_income - applicable_bracket.income_min) * (applicable_bracket.rate/100)) + applicable_bracket.total_tax_prior_brackets

    # Prepare the response JSON
    response = {
        'income': income,
        'taxable_income': new_income,
        'tax_amount': tax_amount,
        'takehome_pay': income-tax_amount
    }

    return jsonify(response)

@app.route('/calculate_federal_and_state_tax', methods=['POST'])
def calculate_federal_and_state_tax():
    json1 = json.loads(calculate_federal_tax().data)
    json2 = json.loads(calculate_state_tax().data)
    income = request.json['income']
    response = {
        'income': income,
        'federal_taxable_income': json1['taxable_income'],
        'state_taxable_income': json2['taxable_income'],
        'federal_tax': json1['tax_amount'],
        'state_tax': json2['tax_amount'],
        'takehome_pay': income-json1['tax_amount']-json2['tax_amount']
    }
    return jsonify(response)

def find_value_by_key(json_obj, key):
    if isinstance(json_obj, dict):
        for k, v in json_obj.items():
            if k == key:
                return v
            elif isinstance(v, (dict, list)):
                result = find_value_by_key(v, key)
                if result is not None:
                    return result
    elif isinstance(json_obj, list):
        for item in json_obj:
            result = find_value_by_key(item, key)
            if result is not None:
                return result

    return None



@app.route('/rent_prices', methods=['GET'])
def calculate_rent_prices():
    state = state_abbreviations[request.args.get('state')]
    city = request.args.get('city')
    
    url = "https://www.rent.com/"+state+"/"+city+"-apartments/rent-trends"
    headers = {
    "user-agent": "PostmanRuntime/7.32.2",
      'Cookie': '__cf_bm=P8msNOUKBvpzUBNl3gDF3B8r6Om4m57CAE43xjCWXEU-1686440470-0-Abmv46MYDoD/0Xu+M1X//9/es8PFdUjx+q6CDBjCA0crGhsNhQyVrmZMNtQ51+tcd9xrpKO1y2wLQNRSkjvqIs8=; __cflb=02DiuG4xuwtx5qQZ5STyBoZtPDzUX7cshuM2EvQ3miAAG; rp_session=1686439515229939; ui=next'
    }

    # print("Sending Requst")
    session = requests.Session()
    resp = session.get(url, headers=headers)

    html_content = resp.content
    
    soup = BeautifulSoup(html_content, 'html.parser')

    # Find the script tag that contains the '__NEXT_DATA__' id
    script_tag = soup.find('script', id='__NEXT_DATA__')

    # Extract the contents of the script tag
    script_content = script_tag.string

    # Parse the script content as JSON
    data = json.loads(script_content)

    # print(data)
    # Extract the 'linkInfo' section from the parsed JSON data
    # link_info = data['props']['pageProps']['linkInfo']
    
    resp = {
        "avgRentForBedrooms":{
        "1": find_value_by_key(data, "avgOneBedroomRent"),
        "S": find_value_by_key(data, "avgStudioRent"),
        "2": find_value_by_key(data, "avgTwoBedroomRent"),
        "3": find_value_by_key(data, "avgThreeBedroomRent")
        },
        "location": find_value_by_key(data, "displayName")
    }

    return jsonify(resp)

@app.route('/monthly_takehome', methods=['POST'])
def calculate_monthly_takehome():
    numBedrooms = request.args.get('numBedrooms')
    numOccupants = request.args.get('numOccupants')
    json1 = json.loads(calculate_federal_and_state_tax().data)
    rent = json.loads(calculate_rent_prices().data)["avgRentForBedrooms"][str(numBedrooms)] / int(numOccupants)
    print(json1)
    print(rent)
    response = {
        "monthly_salary": round(json1["takehome_pay"]/12, 2),
        "monthly_rent_per_person": rent,
        "monthly_takehome": round(json1["takehome_pay"]/12, 2) - rent
    }
    return jsonify(response)

if __name__ == '__main__':
    # 0.34*(578125-231250)+0.32*(231250-182100)+0.24*(182100-95375)+0.22*(95375-44725)+0.12*(44725-11000)+0.1*11000
    # https://www.mortgagecalculator.org/calcs/marginal-tax-rate-calculator.php #This calculator is wrong!
    # https://levelup.gitconnected.com/how-to-get-rental-data-from-the-census-api-using-python-3058c914cb55
    with app.app_context():
        db.drop_all()
        db.create_all()
        import_federal_tax_data(year=2023)
        for state in state_abbreviations.keys():
            try:
                import_state_tax_data(year=2023, state=state)
            except:
                continue
    app.run(debug=True)