import re
from time import sleep
import spacy
from os import path
import json
from pyquery import PyQuery as pQuery
import requests
from urllib.parse import urlparse

# ...........


def update_token():
    token = input("Enter a fresh token : ")
    with open("token.json", 'w') as f:
        f.write(json.dumps({'token': token}))
        return token

# ...........


def get_token():
    if not path.isfile('token.json'):
        return ""
    with open("token.json", 'r') as f:
        data = json.loads(f.readline())
        return data['token']

# ...........
def check_similarity(text1, text2):
    nlp = spacy.load("en_core_web_lg")
    doc1 = nlp(u""+text1+"")
    doc2 = nlp(u""+text2+"")
    return doc1.similarity(doc2)

# ...........
def domains_is_equal(url1, url2):
    return urlparse(url1).netloc == urlparse(url2).netloc

# ...........


def httpGet(url, **options): 
    attempts=10 
    
    if 'attempts' in options: 
        attempts=options['attempts']
        del options['attempts'] 
    
    wait=5
    if 'wait' in options: 
        wait=options['wait'] 
        del options['wait']

    timeoutMessage="tries in "+str(wait)+" seconds later..." 
    if 'timeoutMessage' in options: 
        timeoutMessage=options['timeoutMessage']
        del options['timeoutMessage'] 
    

    if 'timeout' not in options: timeout=options['timeout']=5

    tries = 0
    while tries < attempts:
        try:
            return requests.get(url, **options)
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
            tries += 1
            #print('call url:' + url)
            print(timeoutMessage)
            sleep(wait)

# ...........
def generate_excel_file(**options):
    import xlsxwriter
    # Create an new Excel file and add a worksheet.
    with xlsxwriter.Workbook(options['path']) as workbook:

        header_format = workbook.add_format()
        header_format.set_text_wrap()
        for country, data in options['data'].items():
            create_work_sheet(country, data, workbook, options)

# ...........

def create_work_sheet(name,data, workbook, options):
        worksheet = workbook.add_worksheet(name)
        worksheet.set_default_row(20)
        header_format = workbook.add_format()
        header_format.set_text_wrap()
        header_format.set_bold()
        header_format.set_align('center')
        header_format.set_text_v_align('vcenter')
        header_format.set_font_color('#FFFFFF')
        header_format.set_bg_color('#000000')
        worksheet.freeze_panes(1, 0)

        row = 0
        col = 0

        # create first row for titles
        for key,format in options['columns'].items():
            worksheet.write(row, col, format['title'],header_format)
            if(format['width'])!= None:
                worksheet.set_column(col, col, format['width'])   # Column  A   width set to 20.
            col+=1
        
        row=1
        col=0
        for atributes in data:
            for key in options['columns'].keys():
                worksheet.write(row, col, atributes[key])
                col+=1
            col=0
            row+=1


def get_edurank(uni_name, uni_url):
    default = {
        'world_rank': None,
        'acceptance_rate': None,
        #'edubank_url': None
    }
    org_name = re.sub(r'[\s]', '+', uni_name)
    org_name = re.sub(r'[^\w\d\+]', '', org_name).lower()

    response = httpGet('https://edurank.org/uni-search?s='+org_name, timeout=5,timeoutMessage='Faild fetching edurank,use vpn.')
 
    if(not response or response.status_code != 200):
        raise Exception("unable to access to edurank")
    s = pQuery(response.text)
    e = s(".content table").find("tbody tr:first th a")
    edubank_url = e.attr('href')
    #uni_text = e.text()
    # (similarity:=check_similarity(organisation, uni_text)) > 0.70:
    if e.length:
        #print("similarity : " + str(similarity))
        response = httpGet(edubank_url,timeout=5)
        if(response and response.status_code == 200):
            s = pQuery(response.text)

            # university website
            e = s("dt:contains('Website')").siblings('dd').find('a')
            edurank_uni_url = None
            if(e.length):
                edurank_uni_url = e.attr('href')

            if not domains_is_equal(uni_url, edurank_uni_url):
                return default

            # world rank
            e = s("a:contains('the World')").closest(
                '.ranks__type').siblings('.ranks__rank').find('.ranks__place')
            if(e.length):
                default['world_rank'] = e.text()

            # acceptance rate
            e = s("dt:contains('Acceptance rate')").siblings('dd')
            if(e.length):
                default['acceptance_rate'] = re.sub(r"[^\d\.]", "", e.text())
    # else:
        #print("similarity : " + str(similarity))
    return default

# ...........


def dictionary_except(d, keys):
    """
    Excludes keys from dictionary
    """
    return {x: d[x] for x in d if x in keys}

# ...........


def flatten_json(y):
    """
    Gets a nesteed dictionary and convert it to a flatten dictionary
    """
    out = {}

    def flatten(x, name=''):
        if type(x) is dict:
            for a in x:
                flatten(x[a], name + a + '_')
        elif type(x) is list:
            i = 0
            for a in x:
                flatten(a, name + str(i) + '_')
                i += 1
        else:
            out[name[:-1]] = x

    flatten(y)
    return out

# ...........


def printj(parsed):
    """
    Print dictionary with indention
    """
    print(json.dumps(parsed, indent=4, sort_keys=True))
