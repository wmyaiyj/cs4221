import json
import xml.etree.ElementTree as ET

'''
TODO:
- clean up constants
- handle relationship cardinality (prompt user when merge option is available)
- add ER diagram validation logic
- use class so we can use entities, relationships, processed_tables as global variables

Integration TODO:
- replace error with UI
- replace console input with UI
'''

TABLE_NAME = 'name'
TABLE_ATTRIBUTES = 'attributes'
TABLE_PRIMARY_KEY = 'primary_key'
TABLE_FOREIGN_KEYS = 'foreign_keys'
TABLE_UNIQUE = 'unique'
TABLE_ENTITY = "entity"
TABLE_REFERENCES = "references"

XML_KEY = 'key'
XML_ID = 'id'
XML_ATTRIBUTE = 'attribute'
XML_ATTRIBUTES = 'attributes'
XML_ENTITY_ID = 'entity_id'
XML_RELATION_ID = 'relation_id'
XML_NAME = 'name'

# START INTERFACE TO VIEW
def ConvertXmlToJson(tree):
    # Prep Data Structures
    root = tree.getroot()
    relationships = convert_from_xml_nodes(tree.findall('relationship'))
    entities = convert_from_xml_nodes(tree.findall('entity'))
    sorted_entities = sort_entities_into_weak_and_strong(entities)
    weak_entities = sorted_entities['weak']
    strong_entities = sorted_entities['strong']

    # Start Processing
    processed_tables = process_strong_entities(strong_entities, {})
    processed_tables = process_weak_entities(weak_entities, entities, relationships, processed_tables)
    processed_tables = process_relationships(relationships, entities, processed_tables)

    for table in processed_tables.values():
        table.pop(TABLE_NAME) # Remove the table name we stored for convenience during processing

    output_json = json.dumps(processed_tables, indent=4)
    print output_json
    return output_json

def prompt_user_for_input(prompt):
    user_input = raw_input(prompt)
    return user_input
# END INTERFACE TO VIEW



# START DATA PREP HELPER FUNCTIONS
def convert_from_xml_nodes(nodes):
    result = {}
    for node in nodes:
        id = node.attrib[XML_ID]
        attributes = {}
        keys = []
        for attribute in node.findall(XML_ATTRIBUTE):
            attributes[attribute.attrib[XML_ID]] = attribute.attrib
        for key in node.findall(XML_KEY):
            keys.append(key.text)
        result[id] = {
            "id":         id,
            "name":       node.attrib[XML_NAME],
            "attributes": attributes,
            "keys":       keys
        }
    return result

def sort_entities_into_weak_and_strong(entities):
    result = {'weak':[], 'strong':[]}
    for entity_id in entities:
        entity = entities[entity_id]
        found_relation_id = False
        for attribute in entity[TABLE_ATTRIBUTES].values():
            if XML_RELATION_ID in attribute:
                found_relation_id = True
                break
        if not found_relation_id:
            result['strong'].append(entity)
        else:
            result['weak'].append(entity)
    return result
# END DATA PREP HELPER FUNCTIONS




# START PROCESSING FUNCTIONS
def process_strong_entities(strong_entities, processed_tables):
    for strong_entity in strong_entities:
        processed_tables = process_strong_entity_into_table(strong_entity, processed_tables)
    return processed_tables

def process_weak_entities(weak_entities, entities, relationships, processed_tables):
    for weak_entity in weak_entities:
        if not is_processed(weak_entity, processed_tables):
            stack = [weak_entity]
            while len(stack) > 0:
                temp_weak_entity = stack.pop()

                dominant_entity = get_dominant_entity(temp_weak_entity, entities, relationships)
                if is_processed(dominant_entity, processed_tables):
                    # Once we have a dominant entity that's been processed, we have what we need to process the weak entity
                    dominant_entity_table = processed_tables[dominant_entity[TABLE_NAME]]
                    #print "processing " + temp_weak_entity[XML_NAME]
                    processed_tables = process_weak_entity_into_table(temp_weak_entity, dominant_entity_table, processed_tables)
                else:
                    if dominant_entity in stack:
                        # TODO: show circular reference error message
                        return
                    else:
                        stack.append(temp_weak_entity)
                        stack.append(dominant_entity)
    return processed_tables

def get_dominant_entity(weak_entity, entities, relationships):
    relationship_id = None
    for attribute in weak_entity[XML_ATTRIBUTES].values():
        if XML_RELATION_ID in attribute:
            relationship_id = attribute[XML_RELATION_ID]
            break
    assert relationship_id != None
    relationship = relationships[relationship_id]

    dominant_entity_id = None
    for attribute in relationship[TABLE_ATTRIBUTES].values():
        if attribute[XML_ID] != weak_entity[XML_ID]:
            dominant_entity_id = attribute[XML_ID]
            break

    assert dominant_entity_id != None
    dominant_entity = entities[dominant_entity_id]
    assert dominant_entity != None
    return dominant_entity

def process_relationships(relationships, entities, processed_tables):
    for relationship in relationships.values():
        if is_processed(relationship, processed_tables):
            continue

        # TODO: replace all asserts to proper error prompt
        assert is_valid_relationship(relationship, relationships, entities)

        stack = [relationship]
        while len(stack) > 0:
            current = stack.pop()
            
            dependent_relationship = get_dependent_relationship(current, relationships)
            if dependent_relationship is None or is_processed(dependent_relationship, processed_tables):
                process_relationship_into_table(current, dependent_relationship, processed_tables, entities, relationships)
            else:
                if dependent_relationship in stack:
                    # TODO: show circular reference error
                    return
                else:
                    stack.append(current)
                    stack.append(dependent_relationship)
    return processed_tables

def is_valid_relationship(relationship, relationships, entities):
    dependency_count = 0
    for attribute in relationship[XML_ATTRIBUTES].values():
        if XML_RELATION_ID in attribute:
            if attribute[XML_RELATION_ID] not in relationships.keys():
                return False
            dependency_count += 1
        if XML_ENTITY_ID in attribute:
            if attribute[XML_ENTITY_ID] not in entities.keys():
                return False
            dependency_count += 1
    # relationship should connect to only two foreign tables
    return dependency_count == 2

def get_dependent_relationship(relationship, relationships):
    for attribute in relationship[XML_ATTRIBUTES].values():
        if XML_RELATION_ID in attribute:
            relationship_id = attribute[XML_RELATION_ID]
            return relationships[relationship_id]
    return None

def is_processed(entity, processed_tables):
    return entity[XML_NAME] in processed_tables.keys()

def process_strong_entity_into_table(strong_entity, processed_tables):
    table_name = strong_entity[XML_NAME]
    primary_key_options = get_primary_key_options(strong_entity)
    processed_table = process_table(table_name, strong_entity, primary_key_options, False)
    processed_tables[table_name] = processed_table
    return processed_tables

def process_weak_entity_into_table(weak_entity, dominant_entity_table, processed_tables):
    table_name = weak_entity[XML_NAME]
    primary_key_options = get_primary_key_options(weak_entity, dominant_entity_table)
    processed_table = process_table(table_name, weak_entity, primary_key_options, True)
    processed_tables[table_name] = processed_table
    return processed_tables

def process_relationship_into_table(relationship, dependent_relationship, processed_tables, entities, relationships):
    table_name = relationship[XML_NAME]
    primary_key = []
    foreign_keys = []
    attributes = []
    for attribute in relationship[XML_ATTRIBUTES].values():
        if XML_ENTITY_ID in attribute:
            entity_table = processed_tables[entities[attribute[XML_ENTITY_ID]][XML_NAME]]
            entity_name = entity_table[TABLE_NAME]
            foreign_key = {
                TABLE_ENTITY: entity_name, 
                TABLE_REFERENCES: {}
            }
            for key in entity_table[TABLE_PRIMARY_KEY]:
                new_key_name = format_foreign_key(entity_table[TABLE_NAME], key)
                primary_key.append(new_key_name)
                foreign_key[TABLE_REFERENCES][new_key_name] = key
            foreign_keys.append(foreign_key)

        if XML_RELATION_ID in attribute:
            relationship_table = processed_tables[relationships[attribute[XML_RELATION_ID]][XML_NAME]]
            relationship_name = relationship_table[TABLE_NAME]
            foreign_key = {
                TABLE_ENTITY: relationship_name, 
                TABLE_REFERENCES: {}
            }
            for key in relationship_table[TABLE_PRIMARY_KEY]:
                new_key_name = format_foreign_key(relationship_table[TABLE_NAME], key)
                primary_key.append(new_key_name)
                foreign_key[TABLE_REFERENCES][new_key_name] = key
            foreign_keys.append(foreign_key)

        if XML_NAME in attribute:
            attributes.append(attribute[XML_NAME])

    attributes += primary_key

    processed_table = {
        TABLE_NAME:         table_name,
        TABLE_ATTRIBUTES:   attributes,
        TABLE_PRIMARY_KEY:  primary_key,
        TABLE_FOREIGN_KEYS: foreign_keys,
        # TABLE_UNIQUE:       unique
    }
    processed_tables[table_name] = processed_table
    return processed_tables

def process_table(table_name, entity, primary_key_options, is_weak = False, is_relationship = False):
    primary_key_index = get_primary_key_index(primary_key_options, table_name) # prompt user if necessary
    primary_key = primary_key_options[primary_key_index]
    assert len(primary_key) > 0

    attribute_names = []
    if not is_relationship:
        attribute_names = get_attribute_names(entity)
    
    unique = get_unique_non_primary_attributes(attribute_names, primary_key, primary_key_options)

    foreign_keys = [] # strong entities should not have any foreign keys
    if is_weak or is_relationship:
        foreign_keys = get_foreign_attributes(attribute_names, primary_key)
        # If user chose to use the dominant entity's primary key as part of the weak entity's primary key,
        # we need to include those foreign keys as attributes and include them in the "foreign_keys" section.
        # Else, we shouldn't???
        if len(foreign_keys) > 0:
            for foreign_key in foreign_keys:
                attribute_names.append(foreign_key)

    processed_table = {
        TABLE_NAME:         table_name,
        TABLE_ATTRIBUTES:   attribute_names,
        TABLE_PRIMARY_KEY:  primary_key,
        TABLE_FOREIGN_KEYS: foreign_keys,
        TABLE_UNIQUE:       unique
    }
    #print processed_table
    return processed_table

def get_attribute_names(entity):
    entity_attribute_names = []
    for attribute in entity[TABLE_ATTRIBUTES].values():
        if XML_NAME in attribute:
            entity_attribute_names.append(attribute[XML_NAME])
    # assert len(entity_attribute_names) > 0
    return entity_attribute_names

def get_foreign_attributes(entity_attribute_names, primary_key): # Could be empty
    result = filter(lambda x: x not in entity_attribute_names, primary_key) # get the attributes in primary key which are not in the entity's attributes
    return result

def get_unique_non_primary_attributes(entity_attribute_names, primary_key, primary_key_options): # Could be empty
    # Construct a flat array of attribute names appearing in the primary key options
    primary_key_options_attributes = []
    for option in primary_key_options:
        for key in option:
            primary_key_options_attributes.append(key)

    result = filter(lambda x: x not in primary_key and x in primary_key_options_attributes, entity_attribute_names)
    return result

# We use this function for both weak and strong entities. If weak entity, we MUST provide a dominant_entity_table
def get_primary_key_options(entity, dominant_entity_table = None):
    attributes = entity[XML_ATTRIBUTES]
    options = []
    for key in entity["keys"]:
        option = []
        ids = key.split(",") # [1] or [2, 3]
        for id in ids:
            if "name" in attributes[id]:
                option.append(attributes[id]["name"])
            else: # if there's no "name" inside the attribute, it MUST have a relation_id
                assert (dominant_entity_table is not None)
                assert (XML_RELATION_ID in attributes[id])
                dominant_entity_table_name = dominant_entity_table[TABLE_NAME]
                for key in dominant_entity_table[TABLE_PRIMARY_KEY]:
                    option.append(format_foreign_key(dominant_entity_table_name, key))
        options.append(option)
    return options

def get_primary_key_index(primary_key_options, table_name):
    primary_key_index = 0
    num_options = len(primary_key_options)
    if num_options > 1:
        prompt = "Which key do you want to use as primary key for " + table_name + ":\n"
        current_index = 0 # For convenience sake, we just use zero-based indexing here for the options
        for primary_key in primary_key_options:
            prompt += str(current_index) + ". " + get_primary_key_as_string(primary_key) + "\n"
            current_index = current_index + 1
        prompt += "Your choice(0 or 1): " # TODO remove when there is GUI
        primary_key_index = int(prompt_user_for_input(prompt))
        assert ((primary_key_index >= 0) and (primary_key_index <= num_options)) # Make sure user input a valid index
        print "\n\nSelected " + get_primary_key_as_string(primary_key_options[primary_key_index]) + " as primary key for " + table_name + "\n\n"

    return primary_key_index

def get_primary_key_as_string(primary_key): #e.g.[StaffNumber, Office_Name]
    result = "("
    for key in primary_key:
        result += key + ","
    result = result[:-1] # Remove the extra comma after the last key
    result += ")"
    return result

def format_foreign_key(foreign_table_name, key):
    return foreign_table_name + "_" + key

# END PROCESSING FUNCTIONS

# START OF MAIN CODE
tree = ET.parse('full_sample.xml')
ConvertXmlToJson(tree)