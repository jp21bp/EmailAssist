##### Utilities file
    # Contains the following 2 utility classes:
        # Metrics = used to calculate the token usage of model invocations
        # Storage = used to save/retrieve data to a local DB


#### General libraries
from langchain_core.messages import AnyMessage, BaseMessage
from copy import deepcopy
import pickle, sqlite3, json



















#### Metrics class
    # Keeps tracks of token usage
class Metrics():
    def __init__(self):
        self.history: dict[str,dict[str,int]] = {
            "sum":{
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
            }
        }
            #Syntax:
            # {
            #     "first_chain":{
            #         "prompt_tokens": x,
            #         "completion_tokens": y,
            #         "total_tokens": z,
            #     },
            #     "second_chain":{
            #         "prompts_tokens": a,
            #         "completions_tokens": b,
            #         "total_tokens": c,
            #     },
            #     "sum":{
            #         "prompts_tokens": a+x,
            #         "compeltions_tokens": b+y,
            #         "total_tokens": c+z,
            #     }
            # }
    
    def extract_tokens_used(self, message: AnyMessage, name: str) -> dict:
        # Will extract that tokens that were used in a given model executioon
        
        #First, turn the "AnyMessage" into a dict
        message = dict(message)

        # Second, extract the needed component from the dictionary
        metadata = message['usage_metadata']

        # Third, format the extraction dictionary
        if metadata:
            extraction = {
                f"{name}":{
                    "input_tokens": metadata['input_tokens'],
                    "output_tokens": metadata['output_tokens'],
                    "total_tokens": metadata['total_tokens'],
                }
            }
        elif not metadata:
            print(f"Error extracting '{name}' - creating negative values")
            extraction = {
                f"{name}":{
                    "input_tokens": -1,
                    "output_tokens": -1,
                    "total_tokens": -1,
                }
            }
        return extraction

    def aggregate(self, tokens_dict: dict) -> dict:
        # Will aggregate the tokens from a given "tokens_dict" into 
                # "self.history" dict
        # Will also sum up the tokens into the "sum" section of the
                # "self.history" dictionary

        #First, create a copy of the 'tokens_dict'
        copy = deepcopy(tokens_dict)
            #This is done bc of the following case study:
                # Consider the following:
                    # p1 = Metrics(); p1.history['sum']['prompt_tokens'] = 99
                    # p2 = Metrics(); p3 = deepcopy(p1)
                #Thus
                    #p3.aggregate(p2.history) = {'sum': {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}}
                            # = p3.history = p2.history
                    # This makes sense, since p3 | p2 => p2 overrules
                # BUT
                    # p3.aggregate(p1.history) = {'sum': {'prompt_tokens': 99, 'completion_tokens': 0, 'total_tokens': 0}}
                            # = p3.history = p1.history
                            # AND ALSO = p2.history
                    # The p2.history changing does NOT make sense
                        # Why does p2 change when it wasn't invoked in the function?
                            # There must be some lingering connection from the first fcn
                # Using "deepcopy" resolves this issue

        # Second, extract the inner dictionary
        inner_dict = list(copy.values())[0]

        # Third, sum up the used tokens
        for category, amount in inner_dict.items():
            self.history['sum'][category] += amount

        # Fourth, insert the "tokens_dict" into the history
        self.history = self.history | copy

        # Fifth, delete the deepcopy
        del copy
        return self
























##### Storage class
    # Save and retrieve data to a local db
class Storage():
    def __init__(self, db_name: str, table_name: str):
        self.db_name = db_name
        self.table_name = table_name

    #### Saving data to sqlite
    def save_data(self, data, data_id: int, data_name: str = "NoneGiven"):
        pickled_data = pickle.dumps(data)
        with sqlite3.connect(self.db_name) as conn:
            conn.execute(
                f'CREATE TABLE IF NOT EXISTS {self.table_name} (data_id INTEGER, data_name VARCHAR(255), content BLOB)'
            )
            conn.execute(
                f'INSERT INTO {self.table_name} (data_id, data_name, content) VALUES (?,?,?)',
                (data_id, data_name, sqlite3.Binary(pickled_data))
            )
            conn.commit()
            return data_id + 1

    #### Retrieving data from sqlite
    def retrieve_data(self, data_id: int):
        with sqlite3.connect(self.db_name) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                f'SELECT content FROM {self.table_name} WHERE data_id = ?',
                (data_id,)
            )
            row = cursor.fetchone()
            if row:
                unpickled_data = pickle.loads(row['content'])
                return unpickled_data
            else:
                print('Error: content not found')
                return




























##### General Utilities
    # This class will contain all the fcns necessary for general usage
class Analyzer():
    def __init__(self):
        self.finializer = '\n' + '=' * 50 + '\n'
            #For fomatting purposes
    def analyze_message(self, message: AnyMessage, indent: int = 2, finish: bool = True):
        # Will printout "message" in a nice JSON format
        # First: turn the AIMEsage into a dicationary
        msg_dict = dict(message)
        # Second: turn the dict into json
        json_str = json.dumps(msg_dict, indent=indent)
        # Third: print json string with desired indentation
        output = f'Message type: {type(message)}\n' + json_str + '\n'
        print(output)
        if finish: print(self.finializer)

    def unpack_nests(
        self, 
        variable, 
        separator: str = '\t',
        indent: int = 0
    ):
        if isinstance(variable,BaseMessage):
            self.analyze_message(variable, finish=False)
        elif isinstance(variable, dict):        
            for key, value in variable.items():
                print(f"{separator * indent}{key} - {type(value)}:\n")
                self.unpack_nests(value, separator, indent + 1)
        elif isinstance(variable, list):
            for item in variable:
                self.unpack_nests(item, separator, indent + 1)
        elif isinstance(variable, tuple):
            print("this is TUPLE")
        else:
            print(f"{separator * (indent)}{variable}\n")

        # for key, value in variable.items():
        #     print(f"{separator * indent}{key}:\n")
        #     # print(f"{separator * (indent + 1)}{value}\n")
        #     if isinstance(value, dict):
        #         self.nested_dicts(value, separator, indent + 1)
        #     elif isinstance(value, list):
        #         for mini_value in value:
        #             if isinstance(mini_value, BaseMessage): self.analyze_message(mini_value, finish=False)
        #             else: print(f"{separator * (indent + 1)}{mini_value}\n")

        #     else:
        #         print(f"{separator * (indent + 1)}{value}\n")

    def analyze_snapshot(
        self, 
        variable, 
        display_fields: set,
        separator: str = '\t', 
        indentation: int = 1,
        finish: bool = True,
    ):
        
        for field in dir(variable):
            if field.startswith("_"): continue
            if display_fields:
                if field not in display_fields: continue
            if field == 'values':
                print(field + '\n' * 2)
                field_dict = variable.__getattribute__(field)
                # Use the recursive "nested_dicts" instead
                # for key, value in field_dict.items():
                #     print(key)
                #     print(f'{separator * indentation}{value}')
                #     print('\n' + '+' * 15 + '\n')
                print(self.unpack_nests(field_dict))
            else: 
                print(field)
                print(f'{separator * indentation}{variable.__getattribute__(field)}')
                print('\n' + '~' * 40 + '\n')
        if finish: print(self.finializer)

    def analyze_history(
        self,
        variable : list, 
        display_fields: set,
        separator: str = '\t', 
        indentation: int = 1,
    ):
        # I am only going to take into consideration the following attrs:
            #"config", "paretn_config", and "values['messages']"
        for i, snapshot in enumerate(variable):
            print(f"SnapshotCheck {i}")
            self.analyze_snapshot(
                snapshot, 
                display_fields, 
                separator,
                indentation,
                finish=False
            )
            print('\n' + '=' * 30 + '\n')
        return

    def analyze_attributes(
        self, 
        variable, 
        num_spaces : int = 1, 
        finish: bool = True
    ):
        print(f'Analyzing attributes of {variable}' + '\n\n')
        for attr in dir(variable):
            if attr.startswith("_"): continue
                # These are dunder methods
            print(f"Data Type: {type(attr)}")
            print(f"Name of attr: {attr}")
            print(f"Attribute details: {variable.__getattribute__(attr)}")
            print('\n'* num_spaces)
        if finish: print(self.finializer)

    def analyze_mro(
        self, 
        variable, 
        num_spaces: int = 1, 
        finish: bool = True
    ):
        print(f'Analyzing MRO of {variable}' + '\n\n')
        print(f"Data Type: {type(variable)}")
        for clase in type(variable).mro():
            print(f"Class:{clase.__module__}")
            print(f"Name: {clase.__name__}")
            print('\n'*num_spaces)
        if finish: print(self.finializer)

    def multi_analysis(
        self, 
        variable, 
        num_spaces: int = 1
    ):
        print(f'Full analysis on {variable}')
        self.analyze_attributes(variable, num_spaces, False)
        self.analyze_mro(variable, num_spaces, False)
        print(self.finializer)





