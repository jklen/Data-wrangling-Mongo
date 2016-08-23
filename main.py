'''
Created on Sep 2, 2015

@author: Jaroslav Klen
'''

import xml.etree.cElementTree as ET
from collections import defaultdict
import re
import pprint
import json
import codecs
from pymongo import MongoClient

xml_file = ''
json_out_file = ''

r_hnr_in_street = re.compile(r'^(\d+)\s') # regex, which finds number with space after it at the beginning
r_postcode = re.compile(r'^3[07][347]\d{2}$') # regex, which checks if it is a chattanooga postcode
r_housenr_range = re.compile(r'^\d+-\d+$') # regex to check if it is a housenr range
r_phone = re.compile(r'^\+?1?\W{0,2}([1-9]\d{2})\W{0,2}(\d{3})\W{0,2}(\d{4})$') # telepohone number regex
r_tenn = re.compile(r'(\w+\s?\w+)[\s,]\s?([tT][nN])') # Tennessee state regex

excluded_tags = ['HFCS', 'USGS-LULC:CLASS', 'USGS-LULC:CNTYNAME','USGS-LULC:LEVEL_II',
                 'USGS-LULC:STATECTY','import_uuid', 'is_in', 'is_in:continent',
                 'is_in:country', 'ref', 'ref:left', 'ref:right', 'source', 'source:deep_draft',
                 'source:geometry', 'source:hgv:natonal_network', 'source:name',
                 'FIXME', 'fixme'
                 
]

specific_streets = {'St Elmo Avenue':'Saint Elmo Avenue',
                    'St. Elmo Ave':'Saint Elmo Avenue',
                    '5728 Tennessee 58, Harrison, TN':'5728 Highway 58',
                    'East 3 St':'East 3rd Street',
                    'Brown Town Road':'Browntown Road',
                    'Brown town road':'Browntown Road',
                    'TN 153':'Highway 153'
}

mapping = {'blvd':'Boulevard',
           'Blvd':'Boulevard',
           'Blvd.':'Boulevard',
           'Cir':'Circle',
           'cir':'Circle',
           'Ct':'Court',
           'ct':'Court',
           'Dr':'Drive',
           'Dr.':'Drive',
           'dr.':'Drive',
           'HWY':'Highway',
           'Hwy':'Highway',
           'Ln':'Lane',
           'N':'North',
           'N.':'North',
           'W':'West',
           'E':'East',
           'RDG':'Ridge',
           'Rd':'Road',
           'Rd.':'Road',
           'rd':'Road',
           'St':'Street',
           'St.':'Street',
           'st':'Street',
           'TN':'Tennessee',
           'Tn':'Tennessee',
           'tn':'Tennessee',
           'tenessee':'Tennessee',
           'tennesee':'Tennessee',
           'GA':'Georgia',
           'Ave':'Avenue',
           'ave':'Avenue',
           'ave.':'Avenue',
           'terr':'Terrace',
           'Cental':'Central',
           'CentalHigh':'Central High',
           'BrownTown':'Browntown',
           'Brainer':'Brainerd',
           'courtnry':'Courtney',
           'Hixon':'Hixson',
           'vine':'Vine Street',
           'Ooltewah-Ringold':'Ooltewah Ringgold'
}

city_mapping = {'Ch':'Chattanooga',
                'Chattannooga':'Chattanooga',
                'Soddy Daisy':'Soddy-Daisy',
                'soddy daisy':'Soddy-Daisy',
                'chttanooga':'Chattanooga',
                'redbank':'Red Bank'}

only_streets_mapping = {'blvd':'Boulevard',
           'Blvd':'Boulevard',
           'Blvd.':'Boulevard',
           'Cir':'Circle',
           'cir':'Circle',
           'Ct':'Court',
           'ct':'Court',
           'Dr':'Drive',
           'Dr.':'Drive',
           'dr.':'Drive',
           'HWY':'Highway',
           'Hwy':'Highway',
           'Ln':'Lane',
           'Rd':'Road',
           'Rd.':'Road',
           'rd':'Road',
           'St':'Street',
           'St.':'Street',
           'st':'Street',
           'Ave':'Avenue',
           'ave':'Avenue',
           'ave.':'Avenue',
           'terr':'Terrace'         
}

def fix_address(address):
    
    replaced_street = ''
    checked = {}
    to_change = {}
    
    # FIXING STREET
    
    if address.has_key('street'):
        
        # replacing words based on mapping dict, or whole streets names based on specific_streets dict.
        
        if specific_streets.has_key(address['street']) == False:
            
            for word in address['street'].split():
                
                if word in mapping.keys():
                    word = mapping[word]
                
                if replaced_street == '':
                    
                    if word[-2:] in ('st', 'nd', 'rd', 'th') or word == 'and':
                        replaced_street = word
                    else:
                        replaced_street = word.title()
                else:
                    replaced_street = replaced_street + ' ' + word.title()
        else:
            replaced_street = specific_streets[address['street']]
    
        # checking if street contains housenumber at the beginning, and moving it if yes
        
        address['street'] = replaced_street
        house_number_match = re.search(r_hnr_in_street, address['street']) # housenr regex for search in street   
        
        if house_number_match:
            housenr_to_move = house_number_match.group(1)
            
            # checking housenumber
            
            if address.has_key('housenumber'): 
                postcode_match = re.match(r_postcode, address['housenumber'])
                phone_match = re.match(r_phone, address['housenumber'])
                housenr_range_match = re.match(r_housenr_range, address['housenumber'])
                
                if postcode_match or phone_match:
                            
                    if postcode_match:
                        address['postcode'] = postcode_match.group()
                    
                    if phone_match:
                        to_change['phone'] = phone_match.group(1) + '-' + \
                                            phone_match.group(2) + '-' + phone_match.group(3)
                    
                    address['housenumber'] = housenr_to_move
                                                
                else:
                    
                    try:
                        int(address['housenumber'].strip())
                        address['housenumber_other'] = housenr_to_move
                                            
                    except ValueError:
                        
                        if not housenr_range_match:
                            address['housenumber'] = housenr_to_move
                            
                        else:
                            address['housenumber_other'] = housenr_to_move
                       
            else:
                address['housenumber'] = housenr_to_move
            
            address['street'] = address['street'].replace(housenr_to_move, '')
            address['street'] = address['street'].strip()
            checked['housenumber'] = 'Yes'

    # FIXING CITY
    
    if address.has_key('city'):
        address['city'] = address['city'].strip(' '',')
        
        if address['city'] in city_mapping.keys():
            address['city'] = city_mapping[address['city']]
        
        tenn_match = re.search(r_tenn, address['city'])
        
        if tenn_match:
            address['city'] = tenn_match.group(1) + ', Tennessee'
        
    # FIXING HOUSENAME
    
    replaced_housename = ''
    
    if address.has_key('housename'):
        
        # checking if housename contains housenumber at the beginning
        
        house_number_match = re.match(r_hnr_in_street, address['housename'])
        
        if house_number_match:
            
            if address.has_key('housenumber'):
                if address['housenumber'] <> house_number_match.group(1):
                    address['housenumber_other'] = house_number_match.group(1)
            else:
                address['housenumber'] = house_number_match.group(1)
            
            address['housename'] = address['housename'].replace(house_number_match.group(1),'')
            
        # checking housename by word, and checking if they are shortcuts or mispelings based
        # on mapping dict, specific_streets dict, or are postcodes
        
        if address['housename'] not in specific_streets.keys():
        
            for word in address['housename'].split():
                
                if word in mapping.keys():
                    word = mapping[word]
                
                if re.match(r_postcode, word):
                    address['postcode'] = word
                    word = ''
            
                if replaced_housename == '':
                    replaced_housename = word.title()
                else:
                    replaced_housename = replaced_housename + ' ' + word
            
            address['housename'] = replaced_housename
        
        else:
            address['housename'] = specific_streets[address['housename']]
        
        address['housename'] = address['housename'].strip()
                
        # if housename is a street, put it to street
        
        if address['housename'].find('Street') >= 0 or address['housename'].find('Avenue') >= 0:
            
            if address.has_key('street') == False:
                address['street'] = address['housename']
                del address['housename']
    
        # deleting empty housenames, or when its equal to street, or 'house' only
        
        if address.has_key('housename'):
        
            if address['housename'] == '' or address['housename'].lower() == 'house':
                del address['housename']
            elif address.has_key('street') and address['street'] == address['housename']:
                del address['housename']
    
    # FIXING HOUSENUMBER - which was not already fixed when fixing street
    
    if address.has_key('housenumber') and checked.has_key('housenumber') == False:
        house_number_match = re.search(r_hnr_in_street, address['housenumber'])
        housenr_range_match = re.match(r_housenr_range, address['housenumber'])
                       
        if housenr_range_match:
            pass
        elif house_number_match:
            address['housenumber'] = house_number_match.group(1)
        else:
            del address['housenumber']
    
    # FIXING POSTCODE
    
    if address.has_key('postcode'):
        postcode_match = re.match(r_postcode, address['postcode'])
        
        if postcode_match:
            pass
        else:
            for word in address['postcode'].split():
                postcode_match = re.match(r_postcode, word)
                
                if postcode_match:
                    address['postcode'] = postcode_match.group()
                    break
                else:
                    del address['postcode']
    
    # FIXING STATE
    
    if address.has_key('state'):
        postcode_match = re.match(r_postcode, address['state'])
        
        if postcode_match:
            address['postcode'] = postcode_match.group()
            del address['state']
        else:
            if address['state'] in mapping.keys():
                address['state'] = mapping[address['state']]
            else:
                address['state'] = address['state'].title()

    return address, to_change

def fix_name(name):
    
    # name could be a nickname of street
        
    to_change = {}
    
    
    try:
        int(name)
        name = ''
    
    except ValueError:
        
        if name.lower() in ('home', 'house', 'office'):
            name = ''
            
        else:
            last_word = name.split(' ')[len(name.split(' ')) - 1]
            last_word = last_word.strip(';' '#'',')
            
            for item in only_streets_mapping.items():
                
                if last_word in item and name.count(';') == 0 and len(name.split(' ')) >= 2:
                    to_change['street'] = name
                    break
    
    return name.title(), to_change

def fix_alt_name(altname):
    
    to_change = {}
    replaced_street = ''
    street_intersect = []
    
    if len(altname.split('&')) == 2:
        
        for street in altname.split('&'):
            street = street.strip()
            
            for word in street.split():
                
                if word in mapping.keys():
                    word = mapping[word]
                
                if replaced_street == '':
                    replaced_street = word
                else:
                    replaced_street = replaced_street + ' ' + word
                
            street_intersect.append(replaced_street)
            
    else:
        
        last_word = altname.split(' ')[len(altname.split(' ')) - 1]
        last_word = last_word.strip(';' '#'',')
            
        for item in only_streets_mapping.items():
            
            if last_word in item and altname.count(';') == 0 and len(altname.split(' ')) >= 2:
                to_change['street'] = altname
                break
    
    return street_intersect, to_change

def fix_contact(key, value):
    
    phone_match = re.match(r_phone, value)
    
    if phone_match:
        value = phone_match.group(1) + '-' + phone_match.group(2) + '-' + phone_match.group(3)
    
    else:
        
        if 'email' in key:
            
            return value
        
        else:
            
            return None
        
def to_json(entries):
    
    with codecs.open(json_out_file, encoding = 'utf-8', mode = 'w') as of:
                of.write(json.dumps(entries, indent = 2))

def to_mongo(entries):
    
    client = MongoClient('localhost:27017')
    db = client.test
    db.osm.insert(entries)

def query_mongo():
    
    client = MongoClient('localhost:27017')
    db = client.test
    
    # top 5 most contributing users
    
    q1 = [{'$group':{'_id':'$created.user',
                     'count':{'$sum':1}}},
          {'$sort':{'count':-1}},
          {'$limit':5}
                   
          ]
    
    # how many users contributed
    
    q2 = [{'$group':{'_id':'$created.user_id'}},
          {'$group':{'_id':'distinct_users',
                     'count':{'$sum':1}}}
          
          ]
    
    # average elevation of grave yards
    
    q3 = [{'$match':{'ele':{'$exists':1},
                     'amenity':'grave_yard'}},
          {'$group':{'_id':'grave yards average elevation',
                     'value':{'$avg':'$ele'}}}
          
          ]
    
    # top 3 most common streets, where is possible to drink or eat something
    
    q4 = [{'$match':{'address.street':{'$exists':1},
                     '$or':[{'amenity':'pub'},
                            {'amenity':'bar'},
                            {'amenity':'restaurant'},
                            {'amenity':'cafe'},
                            {'amenity':'nightclub'},
                            {'amenity':'fast_food'}]}},
          {'$group':{'_id':'$address.street',
                     'count':{'$sum':1}}},
          {'$sort':{'count':-1}},
          {'$limit':3}
          
          ]
    
    # positions, where is possible to rent a bicycle + operators name
    
    q5 = {'amenity':'bicycle_rental', 'operator':{'$exists':1}}
    q5_proj = {'operator':1, 'position':1}
    
    # top 5 amenities
    
    q6 = [{'$match':{'amenity':{'$exists':1}}},
          {'$group':{'_id':'$amenity',
                     'count':{'$sum':1}}},
          {'$sort':{'count':-1}},
          {'$limit':5}
                   
          ]
    
    print 'top 5 most contributing users:\n'
    pprint.pprint(list(db.osm.aggregate(q1)))
    print '\nhow many users contributed:\n'
    pprint.pprint(list(db.osm.aggregate(q2)))
    print '\naverage elevation of grave yards:\n'
    pprint.pprint(list(db.osm.aggregate(q3)))
    print '\ntop 3 most common streets, where is possible to drink or eat something:\n'
    pprint.pprint(list(db.osm.aggregate(q4)))
    print '\npositions, where is possible to rent a bicycle + operators name:\n'
    pprint.pprint(list(db.osm.find(q5,q5_proj)))
    print '\ntop 5 amenities:\n'
    pprint.pprint(list(db.osm.aggregate(q6)))

def main_function(xml_file):
    
    entries = []
            
    for event, element in ET.iterparse(xml_file, events=('start',)):
        entry = {}
        created = {}
        address = {}
        tiger = {}
        NHD = {}
        gnis = {}
        references = []
        
        structures = [created, tiger, NHD, gnis, references]
        tag = element.tag
        
        if tag in ('node', 'way'):
            entry['id'] = element.attrib['id']
            entry['type'] = tag
            created['version'] = element.attrib['version']
            created['timestamp'] = element.attrib['timestamp']
            created['changeset'] = element.attrib['changeset']
            created['user'] = element.attrib['user']
            created['user_id'] = element.attrib['uid']
            entry['created'] = created
            
            if tag == 'node':
                lat = float(element.attrib['lat'])
                lon = float(element.attrib['lon'])
                entry['position'] = [lat, lon]
            
            for refer in element.findall('nd'):
                references.append(refer.get('ref'))
            
            if references <> []:
                entry['references'] = references
            
            for t_tag in element.findall('tag'):
                tag_key = t_tag.get('k')
                tag_value = t_tag.get('v')
                
                if tag_key.startswith('addr:'):
                    address[tag_key[5:]] = tag_value
                
                elif tag_key.startswith('tiger'):
                    tiger[tag_key[6:]] = tag_value
                
                elif tag_key.startswith('NHD'):
                    NHD[tag_key[4:]] = tag_value
                
                elif tag_key.startswith('gnis'):
                    gnis[tag_key[5:]] = tag_value
                
                elif tag_key == 'census:population':
                    entry['census:population'] = {tag_value.split(';')[1]:int(tag_value.split(';')[0])}
                
                elif tag_key == 'destination':
                    entry['destination'] = tag_value.split(';')
                
                elif tag_key == 'ele':
                    entry['ele'] = float(tag_value)
                
                elif tag_key == 'exit_to':
                    entry['exit_to'] = tag_value.split(';')
               
                elif tag_key == 'length':
                    entry['length'] = float(tag_value)
                
                elif tag_key == 'population':
                    entry['population'] = int(tag_value)
                
                elif tag_key in ('phone', 'fax', 'email'):
                    contact_fixed = fix_contact(tag_key, tag_value)
                    
                    if contact_fixed <> None:
                        entry['contact:' + tag_key] = contact_fixed
                
                elif tag_key in ('contact:phone', 'contact:email'):
                    contact_fixed = fix_contact(tag_key, tag_value)
                    
                    if contact_fixed <> None:
                        entry[tag_key] = contact_fixed
                
                else:
                    
                    if tag_key not in excluded_tags:
                        entry[tag_key] = tag_value
                
                            
            # checking name tag, if it is a street, put it to addres['street'], if it doesnt exists
            # otherwise leave it in entry['name']
                
            if entry.has_key('name'):
                name, to_change = fix_name(entry['name'])
                
                if name == '':
                    del entry['name']
                
                if to_change <> {}:
                    
                    if address.has_key('street') == False:
                        address['street'] = to_change['street']
                        del entry['name']
                        
            # for name tag, which was street and moved to street, check name_1 tag and move it to name tag
            
            if entry.has_key('name_1'):
                
                if entry.has_key('name') == False:
                    entry['name'] = entry['name_1']
                    del entry['name_1']
                    
            # for name_1 tag, which was moved to name tag, check name_2 tag and move it to name_1 tag
            
            if entry.has_key('name_2'):
                
                if entry.has_key('name_1') == False:
                    entry['name_1'] = entry['name_2']
                    del entry['name_2']
            
            # checking alt_name tag, if it is a street intersect, put it to entry['street_intersect']
            # otherwise leave it in entry['alt_name']
            
            if entry.has_key('alt_name'):
                street_intersect, to_change = fix_alt_name(entry['alt_name'])
                
                if street_intersect <> []:
                    entry['street_intersect'] = street_intersect
                    del entry['alt_name']
                
                if to_change <> {}:
                    
                    if address.has_key('street') == False:
                        address['street'] = to_change['street']
                        del entry['alt_name']
                        
            # check and fix address and if the output of the function contains phone nr.,
            # put it to entry['contact:phone']
     
            if address <> {}:
                entry['address'], to_change = fix_address(address)
                
                
                if to_change <> {}:
                    entry['contact:phone'] = to_change['phone']
            
            else:
                del address
        
        # delete empty structures
        
        for structure in structures:
            
            if len(structure) == 0:
                
                del structure
        
        if entry <> {}:
            
            entries.append(entry)

    
    return entries    

#entries = main_function(xml_file)
#to_json(entries)
#to_mongo(entries)
query_mongo()
