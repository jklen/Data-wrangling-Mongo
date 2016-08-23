'''
Created on Sep 8, 2015

@author: Jaroslav Klen
'''

import xml.etree.cElementTree as ET
from collections import defaultdict
import re
import pprint

xml_file = ''
r_special_chars = re.compile(r'.*([!@#\$%\^&\*\(\)\-\+=\?\.<>\|]).*')
r_postcode = re.compile(r'.*(3[07][347]\d{2}).*')
r_phone = re.compile(r'(\+1\W{0,2}|.*[^\d]|^)([1-9]\d{2})\W{0,2}(\d{3})\W{0,2}(\d{4})($|[^\d].*)')

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

def key_valid(key):
    
    # check if tag key does not include forbidden characters for mongodb
    
    if key.startswith('$') or key.find('.') <> -1:
        
        return 'count_key_invalid'
    
    else:
        
        return 'count_key_valid'

def tag_type(value):
    
    # check the type of tag:
    
    # 1. only number
    # 2. only text
    # 3. alphanumberic
    # 4. street sentence (tag value splitted with space and some word contains street type or shortcut)
    # 5. not street sentence (tag value splitted with space and contains any type of words)
    
    if value.isdigit():
        
        return 'only_integer'
    
    elif value.isalpha():
        
        return 'only_text'
    
    elif value.isalnum():
        
        return 'only_alphanumeric'
    
    else:
        
        try:
            float(value)
            
            return 'only_float'
        
        except ValueError:
            
            if len(value.split()) > 1:
                
                for word in value.split():
                    word = word.strip(' '';'',''-')
                    
                    if word in only_streets_mapping.keys() or word in only_streets_mapping.values():
                        
                        return 'street_sentence'
                                        
                return 'not_street_sentence'
            
            return None
            
def check_number(value):
    
    # check if tag value contains:
    
    # 1. possible phone or fax number
    # 2. postcode
    # 3. number at the beginning of sentence
    # 4. number somewhere in the middle of sentence
    # 5. number at the end of sentence
    
    r_phone_match = re.search(r_phone, value)
    r_postcode_match = re.search(r_postcode, value)
    
    if r_phone_match:
           
        return 'has_phone'
    
    if r_postcode_match:
        
        return 'has_postcode'
            
    if len(value.split()) > 1:
        num_position = []
                
        for word in value.split():
            word = word.strip(' '';'',''-')
            
            try:
                float(word)
                
                num_position.append(1)
                
            
            except ValueError:
                
                num_position.append(0)
                
        return num_position
    
    else:
        
        return None
            
def has_special_chars(value):
    
    # check if tag value contains some of the special characters
            
    r_special_chars_match = re.search(r_special_chars,value)
    
    if r_special_chars_match:
        return 'with_special_chars'
    else:
        return 'without_special_chars'

def tag_words(key, value, words):
    
    # all words used in tag values for tags specified in tags_for_words list
    
    for word in value.split():
        word = word.strip(' '';'',''-''#')
        words[key][word].add(value)
    
def element_has_children(element, elements_children):
    
    # check if element has children tags
    
    if list(element) <> []:
        elements_children[element.tag]['with_children'] += 1
    else:
        elements_children[element.tag]['without_children'] += 1

def element_has_reference(element, elements_reference):
    
    # check if element contains reference to another elements
    
    if element.find('nd') <> None and 'ref' in (element.find('nd')).keys():
        elements_reference[element.tag]['with_ref'] += 1
    else:
        elements_reference[element.tag]['without_ref'] += 1
        

def audit_tags(xml_file):
    
    xml_file = open(xml_file, 'r')
    
    audit = defaultdict(lambda: defaultdict(int))
    words = defaultdict(lambda: defaultdict(set))
    tags_for_words = ['addr:housename', 'addr:street', 'name_1']
    
    tags_distinct_values = defaultdict(set)
    elements_count = defaultdict(int)
    elements_children = defaultdict(lambda: defaultdict(int))
    elements_reference = defaultdict(lambda: defaultdict(int))
    
    basic_info = {'tag_keys_and_distinct_values':tags_distinct_values,
                  'all_elements_count':elements_count,
                  'element_has_children':elements_children,
                  'element_has_reference':elements_reference}
    
    for event, element in ET.iterparse(xml_file, events=('start',)):
        
        tag = element.tag
        elements_count[tag] += 1
        element_has_children(element, elements_children)
        element_has_reference(element, elements_reference)
        
        if tag in ('node', 'way'):
            
            for t_tag in element.findall('tag'):
                tag_key = t_tag.get('k')
                tag_value = t_tag.get('v')
                
                valid_key = key_valid(tag_key)
                audit[tag_key][valid_key] += 1
                
                type_tag = tag_type(tag_value)
                
                if type_tag <> None:
                    audit[tag_key][type_tag] += 1
                
                number_check = check_number(tag_value)
                
                if number_check <> None:
                
                    if type([]) == type(number_check):
                        
                        if number_check[0] == 1:
                            audit[tag_key]['number_start_in_sentence'] += 1
                        
                        if number_check[len(number_check) - 1] == 1:
                            audit[tag_key]['number_end_in_sentence'] += 1
                            
                        if 1 in number_check[1:len(number_check) - 1]:
                            audit[tag_key]['number_middle_in_sentence'] += 1
                    
                    else:
                        
                        audit[tag_key][number_check] += 1
                
                spec_char = has_special_chars(tag_value)
                audit[tag_key][spec_char] += 1
                
                tags_distinct_values[tag_key].add(tag_value)
                
                if tag_key in tags_for_words:
                    tag_words(tag_key, tag_value, words)
                
    
    return audit, basic_info, words

audit_result = audit_tags(xml_file)