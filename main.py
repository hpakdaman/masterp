from collections import defaultdict
from genericpath import isfile
import requests
import json
import os
from lib import *
from requests.models import Response
from html2text import html2text
from progress import do_progress


# ...........
def get_all_programs(**options):
    """
    Gets all of available programs base on some filters
    - filters :
        disiplines      =>      di-111          [go to diciplines.json]
        countries       =>      ci-111          [go to countries.json]
        degree_type     =>      dg-msc,ma,..    [msc: Master of science , ma: Master of Art]
        attendance      =>      mh-face2face    [facee2face: on campus learning]
        format          =>      de-fulltime
        currency        =>      tc-USD          [EUR,USD]
        duration        =>      dur-[720,720]   [[720,720]: 2 year , [540,540]: 1.5 year ,[360,360]: 1 year]tuituion fee    =>      tr-[1000,5000]  [[from,to]]
        limit           =>      &size=20
    """
    filters = {
        'lv': 'master',
        'en': '1519',
        # 'uc':'', # User Country
        # 'ur':'', # User Region
    }
    params = {'size': '10000'}

    if 'disiplines' in options:
        filters['di'] = options['disiplines']

    if 'countries' in options:
        filters['ci'] = options['countries']

    if 'degree_type' in options:
        filters['dg'] = options['degree_type']

    if 'attendance' in options:
        filters['mh'] = options['attendance']

    if 'format' in options:
        filters['de'] = options['format']

    if 'currency' in options:
        filters['tc'] = options['currency'].upper()
    else:
        filters['tc'] = 'USD'

    if 'duration' in options:
        filters['dur'] = options['duration']

    if 'tuituion' in options:
        filters['tr'] = options['tuituion']

    if 'limit' in options:
        params['size'] = options['limit']

    # format queris like 'key-val1,val2|...'
    query = '?q='
    sep = ''
    for key, val in filters.items():
        query += sep+key+'-'+str(val)
        sep = '|'

    # add queris strings to url
    sep = '&'
    for key, val in params.items():
        query += sep+key+'='+str(val)
        sep = '&'

    response = httpGet('https://search.prtl.co/2018-07-23/'+query, timeout=6)
    if(response.status_code != 200):
        exit("unable to connect master portal!")
    programs = json.loads(response.text)

    def _filter(data):
        country = set()
        for item in data['venues']:
            country.add(item['country'].lower())
        data['country'] = ','.join(country)

        return dictionary_except(data, [
            'id',
            'title',
            # 'tuition_fee',
            # 'fulltime_duration',
            'organisation_id',
            'organisation',
            'country'
        ])

    return list(map(_filter, programs))


# ...........
def get_university_rate(uni_id):
    """
    Get university rate . Returns i.e: {
            "average": 9.375,
            "quantity": 32
    }
    """
    default = {
        'uni_rating_avg': None,
        # 'uni_rating_quantity': None
    }
    response = httpGet(
        'https://reviews.prtl.co/v1/universities/'+str(uni_id), timeout=5)
    uni = json.loads(response.text)
    if(response.status_code == 200 and uni['rating'] != None):
        default = {
            'uni_rating_avg': str(round(uni['rating']['average'], 2)) + '/' + str(uni['rating']['quantity'])
        }

    return default


# ...........
def get_program(id):
    """
    Gets detailed information about specific program
    """
    token = get_token()

    while True:
        response = httpGet('https://reflector.prtl.co/?length=0&include_order=false&token=' +
                           token+'&q=id-'+str(id)+'&path=data%2Fstudies%2Fany%2Fdetails%2F', timeout=5)
        if(response.status_code == 200):
            break  # Data fetched
        if(response.status_code == 401):
            print(response.reason + "(401)")
            token = update_token()

    data = json.loads(response.text)[str(id)]
    program = dictionary_except(data, [
        'title',
        'summery',
        # 'description',
        'ielts',
        'toefl_internet',
        'toefl_paper',
        # 'pte',
        'presence',
        'level',
        'degree',
        # 'degree_formatted',
        # 'virtual_path',
        'ects_credits',
        'gpa_required',
        'gpa_scale',
        'min_gpa',
        'min_gpa_raw',
        # 'application_deadline',
        'accept_gre',
        # 'entry_level',
        # 'requirements',
    ])

    # merge density
    program['density'] = ','.join(data['density'])

    # merge nethod
    program['methods'] = ','.join(data['methods'])

    # tidy requirements
    program['requirements'] = html2text(
        data['requirements']).replace('\n', os.linesep)

    # duration
    program['duration'] = data['fulltime_duration'] + \
        ' ' + data['fulltime_duration_period']

    # language fully or partially
    sep = ''
    if 'fully' in data['languages'] and len(data['languages']['fully']):
        program['languages'] = sep+'full_' + \
            list(data['languages']['fully'].values())[0]['title'].lower()
        sep = ','

    if 'partially' in data['languages'] and len(data['languages']['partially']):
        program['languages'] = sep+'part_' + \
            list(data['languages']['partially'].values())[0]['title'].lower()
        sep = ','

    # link
    program['url'] = list(data['links'].values())[0]['url']

    #  master portal link
    program['masterp_url'] = 'https://www.mastersportal.com/studies/' + \
        str(data['id'])

    # deadline
    sep = ''
    program['start'] = ''
    if data['study_startdates']:
        for item in data['study_startdates'].values():
            if item['study_deadlines']:
                date_deadline = next((ditem for ditem in item['study_deadlines'].values(
                ) if ditem['type'] == 'international'), {'date_deadline': '-'})['date_deadline']
            else:
                date_deadline = '-'
            program['start'] += sep+'start: ' + \
                item['date_start']+'  deadline: '+date_deadline
            sep = os.linesep

    # tuition_fee_types
    program['tuition_fee'] = next((item for item in data['tuition_fee_types']
                                  if item['target'] == 'international'), {'amount': None})['amount']

    return dict(program)

# ...........


config = {
    'disiplines': '24',  # computer science 24 , humanity : 11
    # germany : 11 ,   multi : 82,202,56,1,6,4,10,14,19,11,20,24,9,7,3,26,8,21
    'countries': '82,202,56,1,6,4,10,14,19,11,20,24,9,7,3,26,8,21',
    'tuituion': '[0,7000]',
    'duration': '[720,720],[540,540],[360,360]',
    'attendance': 'face2face',
    'degree_type': 'msc',
    'limit': 10000,  # should be less than or equal to 10000
    'project_name': 'hamed-uni-tuition-0-7000-2'
}


# project name
#project_name = 'my-uni-list'
# if name:=input("enter a name for the project (myuni-list): "):
#    project_name = name

project_name = re.sub('[\s]', '-', config['project_name'])
project_name = re.sub('[^\w\d\-]', '', project_name)
output_json_path = 'output/json/'+project_name+'.json'
output_xlsx_path = 'output/xlsx/'+project_name+'.xlsx'


programs = get_all_programs(**config)
# A List of Items
length = len(programs)
if(length == 0):
    exit("noting found!")
print("All matched diciplines : "+str(length))

# Initial call to print 0% progress
i = 0
do_progress(i, length)

output = []
available_keys = []
# load last inserted data to output
try:
    fp = open(output_json_path, 'r')
    data = json.load(fp)
    fp.close()
    for program in data:
        key = program['id']
        if(key not in available_keys):
            available_keys.append(key)
            output.append(program)
except:
    pass


for program in programs:
    if(program['id'] not in available_keys):
        # merge some data from masterp
        program = program | get_program(program['id'])
        # merge some data from masterp
        program = program | get_university_rate(program['organisation_id'])
        del program['organisation_id']
        # merge some data from edurank
        program = program | get_edurank(
            program['organisation'], program['url'])

        output.append(program)

        fp = open(output_json_path, 'w')
        json.dump(output, fp)
        fp.close()

    # Update Progress Bar
    i += 1
    do_progress(i, length)


cols = {
    # "id": {'title': "ID", 'width': 6},
    "title": {'title': "Program", 'width': 35},
    "organisation": {'title': "Uni", 'width': 25},
    "country": {'title': "Country", 'width': 8},
    "ielts": {'title': "Ielts", 'width': 4},
    "toefl_internet": {'title': "IBT", 'width': 4},
    "presence": {'title': "Presence", 'width': 7},
    # "level":{ 'title': "master",'width':None},
    "degree": {'title': "Degree", 'width': 7},
    "ects_credits": {'title': "ECTs", 'width': 6},
    # "gpa_required":{ 'title': "GPA Need",'width':None},
    "gpa_scale": {'title': "GPA SC", 'width': 11},
    "min_gpa": {'title': "GPA Min", 'width': 11},
    "min_gpa_raw": {'title': "GPA MinRaw", 'width': 11},

    # "accept_gre":{ 'title': "-1",'width':None},
    "density": {'title': "Density", 'width': 9},
    "methods": {'title': "Method", 'width': 9},
    "requirements": {'title': "Requirements", 'width': 13},
    "duration": {'title': "Duration", 'width': 9},
    "languages": {'title': "Langs", 'width': 10},
    "url": {'title': "Uni Link", 'width': None},
    "masterp_url": {'title': "MP Link", 'width': None},
    "start": {'title': "Starts and Deadlines", 'width': 35},
    "tuition_fee": {'title': "Tuition", 'width': None},
    "uni_rating_avg": {'title': "Uni Rate", 'width': 10},
    "world_rank": {'title': "World Rank", 'width': 10},
    "acceptance_rate": {'title': "Acceptance", 'width': 11},
}


groups = defaultdict(list)
for obj in output:
    for country in obj['country'].split(','):
        groups[country].append(obj)


generate_excel_file(data=groups, path=output_xlsx_path, columns=cols)
