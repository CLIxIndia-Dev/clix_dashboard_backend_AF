################################################################################
'''
For tools we used -- get_tools_data_v1.py and tools_data_for_adoption_v2.py

This part of the code is for fetching log level tools data from raw json files in
synchting data folders.
Data is fetched for specific set of schools.
Function to be used is: fetch_log_level_data_tools(data_path, schools, state)

The code collates json files (tool section logs) of all the schools,
extracts relevant data from them and puts them all in a dataframe for further
analysis.

In the original codebase from which it has been taken, this is fourth version.
Time spent is captured as start and end time for all tools
except policesquad, which has timespentstage entry.
'''

import os
import re
import json
from collections import defaultdict
import logging
import operator
import itertools
import pandas
import numpy 

def get_state_school_json(json_file_path):
    path_items = json_file_path.split('/')
    #state_code = path_items[path_items.index('gstudio') - 2]
    school_server_code = path_items[path_items.index('gstudio') - 1]
    state_code = school_server_code.split('-')[1][:2]
    if not school_server_code:
        print('Couldnt fetch school_server_code for file - {}'.format(json_file_path))
        logging.debug('Couldnt fetch school_server_code for file - %s', json_file_path)
    return {'state_code': state_code, 'school_server_code': school_server_code}

def get_files_from_a_tool_n_user(path):
    '''
    Gets all the filenames of particular pattern in a given directory name pattern (both given by regex)
    Use of nested tuples is to make it amenable for parallel processing in future if need be
    :param path: root path of data
    :param regex_file: regex to identify files say, .csv, .json etc
    :param regex_dir: regex to identify immediate parent directory of files
    :return: list of tuples - [(filename, file_attributes)]
    '''
    files_list = list()
    user_id = "0"
    regex_tool_n_user = r"^" + re.escape(user_id) + "-Ice-cubes-in-lemonade.json"
    regObj_toolnuser = re.compile(regex_tool_n_user)
    regex_file = r'.+(json)$'
    regex_dir = r'gstudio_tools_logs'
    regObj_file = re.compile(regex_file)
    regObj_dir = re.compile(regex_dir)
    regex_parent_dir = re.compile(r'gstudio')

    for root, dnames, fnames in os.walk(os.path.join(path)):
        for dname in dnames:

           if regex_parent_dir.match(dname):
                for d1name in os.listdir(os.path.join(root, dname)):
                    #If in gstudio folder do the following:
                    #Go to tools folder - to get actual json files for tools data
                    if regObj_dir.match(d1name):
                      gstudio_tools_log_folder_path =  os.path.join(root, dname, d1name)
                      for eachdir in os.listdir(gstudio_tools_log_folder_path):
                         tool_dir_path = os.path.join(root, dname, d1name, eachdir)
                         tool_dir_files = os.listdir(tool_dir_path)
                         if (not tool_dir_files):
                             logging.debug('No Tool log data in folder - %s', tool_dir_path)
                         else:
                             for eachfile in tool_dir_files:

                                 if regObj_toolnuser.match(eachfile):
                                   json_file_path = os.path.join(root, dname, d1name, eachdir, eachfile)
                                   state_code = get_state_school_json(json_file_path)['state_code']
                                   school_server_code = get_state_school_json(json_file_path)['school_server_code']
                                   files_list.append((state_code, (school_server_code, json_file_path)))
    return files_list

def get_all_school_names():
    return None


def get_files(path, schools_list):
    '''
    Gets all the filenames of particular pattern in a given directory name pattern (both given by regex)
    Use of nested tuples is to make it amenable for parallel processing in future if need be
    :param path: root path of data
    :param schools_list: list of schools to be considered for extraction
    #:param regex_file: regex to identify files say, .csv, .json etc
    #:param regex_dir: regex to identify immediate parent directory of files
    :return: list of nested tuples - [(state_code, (school_server_code, file_path)]
    '''
    files_list = list()
    regex_file = r'.+(json)$'
    regex_dir = r'gstudio_tools_logs'
    regObj_file = re.compile(regex_file)
    regObj_dir = re.compile(regex_dir)
    regex_parent_dir = re.compile(r'gstudio')

    for root, dnames, fnames in os.walk(os.path.join(path)):
        for dname in dnames:
            if regex_parent_dir.match(dname):
                #Check if you are in the school directory given in the list of schools
                current_path = os.path.join(root, dname)
                school_server_code = current_path.split('/')[-2]
                if school_server_code in schools_list:
                  for d1name in os.listdir(os.path.join(root, dname)):
                    #If in gstudio folder do the following:
                    #Go to tools folder - to get actual json files for tools data
                    if regObj_dir.match(d1name):
                      gstudio_tools_log_folder_path =  os.path.join(root, dname, d1name)
                      for eachdir in os.listdir(gstudio_tools_log_folder_path):
                         tool_dir_path = os.path.join(root, dname, d1name, eachdir)
                         if os.path.isdir(tool_dir_path):
                             tool_dir_files = os.listdir(tool_dir_path)
                         else:
                             continue
                         if (not tool_dir_files):
                             logging.debug('No Tool log data in folder - %s', tool_dir_path)
                         else:
                             for eachfile in tool_dir_files:
                                 if regObj_file.match(eachfile):
                                   json_file_path = os.path.join(root, dname, d1name, eachdir, eachfile)
                                   state_code = get_state_school_json(json_file_path)['state_code']
                                   school_server_code = get_state_school_json(json_file_path)['school_server_code']
                                   files_list.append((state_code, (school_server_code, json_file_path)))
    return files_list

def parse_nested_dict(dict_nes, item_key):
    '''
    parses through a nested dictionary to tech value corresponding to 'item_key' key.
    :param dict_nes: nested dictionary
    :param item_key: item key we want value for
    :return:
    '''
    try:
        if item_key == 'sessionID':
           reg_Obj = re.compile(re.escape(item_key))
        else:
           reg_Obj = re.compile('(' + re.escape(item_key) + ')', re.IGNORECASE)

        key_match_list = [key for key in dict_nes.keys() if reg_Obj.match(key)]
        if key_match_list:
          return dict_nes[key_match_list[0]]
        else:
          for k, v in dict_nes.items():
           if isinstance(v, dict):
             return parse_nested_dict(v, item_key)
           elif isinstance(v, list):
             for each in v:
                 parse_nested_dict(each, item_key)
    except Exception as e:
        if item_key == 'sessionId':
            print("{0}: {1}".format(e, dict_nes))
            #logging.debug("{0}: {1}".format(e, dict_nes))
            raise Exception("{0}: {1}".format(e, dict_nes))
            return None
        else:
            raise Exception("{0}: {1}".format(e, dict_nes))


tools_domain_map = {
        'e': [],
        'm': ['ice', 'factorisation', 'coins_puzzle','rationpatterns', 'food_sharing_tool', 'ages_puzzle', 'policesquad'],
        's': ['astroamer_element_hunt_activity', 'astroamer_moon_track', 'astroamer_planet_trek_activity']
    }

def accumulator(files):
        '''
        Function to accumulate all the json file logs for a all states and school_ids in them
        If a user has logged into tools, it will reflect as a row in this data with a timestamp
        Also state level data are saved as csvs in current working directory
        Only following fields are extracted related to json files:
         1. created_at
         2. user_id
         3. tool_name
         4. school_server_code
         5. state_code
        :param files: nested list of tuples - (state_code, (school_code, tool_json_file))
        :return: dictionary of dictionaries - {'state': {'user_id': user_id, 'created_at': time, 'tool_name': tool_name}}
        '''
        final_data = dict()
        for state_code, all_state_files in itertools.groupby(files, operator.itemgetter(0)):
            schools_tool_dict = defaultdict(list)
            for school in [all_schools[1] for all_schools in all_state_files]:
                school_json_file = school[1]
                input_file = open(school_json_file, 'r')
                try:
                   json_input = json.load(input_file)
                except Exception as e:
                   logging.debug(e)
                   logging.debug('Some issue with loading file : %s', school_json_file)
                for items in json_input:
                   try:
                       schools_tool_dict['school_server_code'].append(school[0])
                       tool_name = school_json_file.split('/')[-1:][0].split('.')[0].split('-')[1]
                       tool_name = ''.join(c.lower() for c in tool_name if not c.isspace())
                       schools_tool_dict['tool_name'].append(tool_name)
                       normal_tools = ["food_sharing_tool", "ages_puzzle", "astroamer_element_hunt_activity", "coins_puzzle", "factorisation"]

                       if pandas.Series([tool_name]).isin(normal_tools)[0]:
                           schools_tool_dict['createdat_start'].append(None)
                           schools_tool_dict['createdat_end'].append(parse_nested_dict(items, 'create'))
                           schools_tool_dict['time_spent'].append(None)

                       elif tool_name == "ice":
                           schools_tool_dict['createdat_start'].append(parse_nested_dict(items, 'tool_startTime'))
                           schools_tool_dict['createdat_end'].append(parse_nested_dict(items, 'tool_endTime'))
                           schools_tool_dict['time_spent'].append(None)

                       elif tool_name == "policesquad":

                           schools_tool_dict['createdat_start'].append(None)
                           schools_tool_dict['createdat_end'].append(parse_nested_dict(items, 'create'))
                           schools_tool_dict['time_spent'].append(parse_nested_dict(items, 'TimeSpentStage'))

                       elif tool_name == "astroamer_planet_trek_activity":
                           schools_tool_dict['createdat_start'].append(parse_nested_dict(items, 'tool_startTime'))
                           schools_tool_dict['createdat_end'].append(parse_nested_dict(items, 'tool_endTime'))
                           schools_tool_dict['time_spent'].append(None)

                       elif tool_name == "astroamer_moon_track":
                           schools_tool_dict['createdat_start'].append(parse_nested_dict(items, 'tool_startTime'))
                           schools_tool_dict['createdat_end'].append(parse_nested_dict(items, 'tool_endTime'))
                           schools_tool_dict['time_spent'].append(None)

                       elif tool_name == "rationpatterns":
                           start_time = parse_nested_dict(items, 'gameOverallStartTime')
                           mod_starttime = ' '.join([start_time.split(':')[0], ':'.join(start_time.split(':')[1:])])
                           end_time = parse_nested_dict(items, 'gameOverallEndTime')
                           mod_endtime = ' '.join([end_time.split(':')[0], ':'.join(end_time.split(':')[1:])])
                           schools_tool_dict['createdat_start'].append(mod_starttime)
                           schools_tool_dict['createdat_end'].append(mod_endtime)

                           schools_tool_dict['time_spent'].append(None)

                       schools_tool_dict['session_id'].append(parse_nested_dict(items, 'sessionId'))
                       #schools_tool_dict['session_id'].append(parse_nested_dict(items, 'user'))
                       schools_tool_dict['user_id'].append(school_json_file.split('/')[-1:][0].split('-')[0])
                   except Exception as e:
                       import pdb
                       pdb.set_trace()
                       logging.debug(e)
                       print(e)
                       print('There was some error fetching items from json. Have to debug in (accumulator) function')
                input_file.close()

            dframe = pandas.DataFrame.from_dict(schools_tool_dict, orient = 'index').transpose()
            dframe['createdat_start'] = pandas.to_datetime(dframe['createdat_start'], errors='ignore', format="%Y%m%d %H:%M:%S")
            dframe['createdat_end'] = pandas.to_datetime(dframe['createdat_end'], errors='ignore', format="%Y%m%d %H:%M:%S")

            tools_map = dict()
            for k, v in tools_domain_map.items():
                for each_v in v:
                    tools_map[each_v] = k

            dframe['tool_new'] = dframe['tool_name'].apply(lambda x: ''.join(c.lower() for c in x if not c.isspace()))
            dframe['tool_new'].replace(tools_map, inplace=True)
            dframe = dframe.rename(columns={'tool_new': 'domain'})

           # dframe_final = dframe.groupby(['tool_name',
           #                                'user_id']).apply(get_time_spent).reset_index().drop(['index'], axis =1)
            final_data[state_code] = dframe.to_dict()
        return final_data

def fetch_log_level_data_tools(data_path, schools, state):

    working_dir = os.getcwd()
    logging.basicConfig(filename=working_dir + '/clix_data_processing_session_outputs.log', level=logging.DEBUG)

    print('This script parses through the top directory provided by user to fetch json files '
          '(hopefully saved in gstudio_tools_logs folder) and \n extract information from each '
          'of them at tool level.\n')
    print('---------------------------------------------------------------------------------')
    print('fetching tools data from this directory:{}\n'.format(data_path))
    parent_directory = data_path

    # Tools related json files - indexed by state and school ids
    tools_json_files = get_files(parent_directory, schools)

    if not tools_json_files:
        print('No Tools data for the school list:{}'.format(schools))
        return pandas.DataFrame()

    print('Done fetching all the relevant json files indexed by state_code and school_server_id')
    print('------------------------------------------------------------------------------------')
    # Extracted data from tools json files - for all states and schools
    tools_all_schools_data = accumulator(tools_json_files)
    print('Done with extracting relevant information from all the json files.\n')

    return pandas.DataFrame(tools_all_schools_data[state])

##############################################################################################
###############################################################################
'''
This part of the code is to extract important metrics from raw log level tools data.
Input is the dataframe with tools - log level - data for a set of schools and date range
'''
#over which metrics need to be calculated.
import math
import pandas

import os
from functools import reduce
import datetime
def get_time_spent(df):
    '''
    This function estimates the time spent in minutes by a student in a day in a
    particular session.

    :param df:
    :return:
    '''
    df['date_created'] = df['createdat_end'].apply(lambda x: x.date())

    def timespent(x):

        normal_tools = ["food_sharing_tool", "ages_puzzle", "astroamer_element_hunt_activity",
                        "coins_puzzle", "factorisation"]
        rationpatt = x['tool_name'] == 'rationpatterns'
        ice = x['tool_name'] == 'ice'
        ast_moon = x['tool_name'] == 'astroamer_moon_track'
        ast_trek = x['tool_name'] == 'astroamer_planet_trek_activity'
        polic = x['tool_name'] == 'policesquad'
        normal = x['tool_name'].isin(normal_tools)

        if not x[normal].empty:
           x.loc[normal, ['time_spent']] = ((max(x[normal]['createdat_end']) - min(x[normal]['createdat_end'])).seconds//60)%60

        if not x[ast_trek].empty:
           ts_asttrek =  reduce(lambda x,y: x + y + datetime.timedelta(0), x[ast_trek]['createdat_end'] - x[ast_trek]['createdat_start'])
           x.loc[ast_trek, ['time_spent']] = (ts_asttrek.seconds//60)%60

        if not x[ast_moon].empty:
           ts_moon = reduce(lambda x,y: x + y + datetime.timedelta(0), x[ast_moon]['createdat_end'] - x[ast_moon]['createdat_start'])
           x.loc[ast_moon, ['time_spent']] =  (ts_moon.seconds//60)%60

        if not x[ice].empty:
           ts_ice =  reduce(lambda x,y: x + y + datetime.timedelta(0), x[ice]['createdat_end'] - x[ice]['createdat_start'])
           x.loc[ice, ['time_spent']] = (ts_ice.seconds//60)%60

        if not x[rationpatt].empty:
           ts_ratio = reduce(lambda x,y: x+y+datetime.timedelta(0), x[rationpatt]['createdat_end'] - x[rationpatt]['createdat_start'])
           x.loc[rationpatt, ['time_spent']] = (ts_ratio.seconds//60)%60

        if not x[polic].empty:
            def get_minute(x):
                try:
                    ts = x['time_spent']
                    if (isinstance(ts, int) or isinstance(ts, numpy.int64)):
                       hh_minut = int(ts) * 60
                       minut_minut = 0
                       sec_minut = 0
                    elif (len(ts.split(':')) > 1):
                       hh_minut = int(ts.split(':')[0]) * 60
                       minut_minut = int(ts.split(':')[1])
                       sec_minut = float(ts.split(':')[2]) / 60
                    else:
                       print('New type for timespent in policesquad')
                       import pdb
                       pdb.set_trace()
                       hh_minut = int(ts) * 60
                       minut_minut = 0
                       sec_minut = 0
                except Exception as e:
                    import pdb
                    pdb.set_trace()

                return hh_minut + minut_minut + sec_minut

            """
            def splittime(x):
               ts = x['time_spent']
               hh_minut = int(ts.split(':')[0]) * 60
               minut_minut = int(ts.split(':')[1])
               sec_minut = float(ts.split(':')[2])/60
               return hh_minut + minut_minut + sec_minut
            """


            x.loc[polic, ['time_spent']] = x.loc[polic, ['time_spent']].apply(lambda x: get_minute(x), axis=1)
        return x

    df = df.groupby(['user_id', 'date_created', 'session_id']).apply(lambda x: timespent(x)).reset_index(level=None, drop=True)
    return df

def get_num_users(df):
    '''
    To get the num of users per day, we count the unique user_ids
    in any day. To get an approximate estimate of anonymous user - userid ==0,
    we count the number of unique sessions by anonymous users.

    As we are trying to capture usage of a tool in any day, it makes sense to
    count sessions, when there is no user_id entry (user_id == 0)

    :param df:
    :return:
    '''
    def get_reg_users(df):
        df['num_users_reg'] = len(df['user_id'].unique())
        return df

    def get_anon_users(df):
        df['num_users_nonreg'] = len(df['session_id'].unique())
        return df

    df = df.groupby(['date_created']).apply(lambda x: get_reg_users(x)).reset_index(level=None, drop=True)
    df = df.groupby(['date_created']).apply(lambda x: get_anon_users(x)).reset_index(level=None, drop=True)
    anon_users_mask = df["user_id"] == 0

    df['num_students_day'] = anon_users_mask*df['num_users_nonreg'] + ~anon_users_mask * df["num_users_reg"]
    return df

def get_total_users(df):
    '''
    As we are considering only user_ids, number of students in
    anonymous user entries is missing. It is counted as only one user.

    Here we are trying to capture actual number of students registered. That is it.

    :param df:
    :return:
    '''

    df['total_students'] = len(df['user_id'].unique())
    return df

def get_total_days(df):
    df['total_days'] = len(df["date_created"].unique())
    return df

def daily_attendence(df):

    total_students_reg = len(df["user_id"].unique())
    def attendence(x):
       x["daily_attendence"] = len(x["user_id"].unique())/total_students_reg
       return x
    df = df.groupby(["date_created"]).apply(lambda x: attendence(x)).reset_index(level=None, drop=True)

    return df

def consistent_stud(df):

    total_days = len(df["date_created"].unique())
    def get_consis_stud(x):
        x["individ_attendence"] = len(x["date_created"].unique())/total_days
        return x
    df = df.groupby(["user_id"]).apply(lambda x: get_consis_stud(x)).reset_index(level=None, drop=True)

    return df

def consist_num_of_stud(df):
    df['num_of_consistent_stud'] = len(df[df["individ_attendence"] >= 0.4]["user_id"].unique())
    return df

def get_indicators_tools_data(schools_dframe, state_code):

   time_spent_dframe = schools_dframe.groupby(['school_server_code']).apply(lambda x: get_time_spent(x)).reset_index(level=None, drop=True)
   users_perday_dframe = time_spent_dframe.groupby(['school_server_code']).apply(lambda x: get_num_users(x)).reset_index(level=None, drop=True)
   total_users_dframe = users_perday_dframe.groupby(['school_server_code']).apply(lambda x: get_total_users(x)).reset_index(level=None, drop=True)
   total_days_dframe = total_users_dframe.groupby(['school_server_code']).apply(lambda x: get_total_days(x)).reset_index(level=None, drop=True)
   attendence_dframe = total_days_dframe.groupby(['school_server_code']).apply(lambda x: daily_attendence(x)).reset_index(level=None, drop=True)
   consistent_stud_dframe = attendence_dframe.groupby(["school_server_code"]).apply(lambda x: consistent_stud(x)).reset_index(level=None, drop=True)
   final_dframe = consistent_stud_dframe.groupby(["school_server_code"]).apply(lambda x: consist_num_of_stud(x)).reset_index(level=None, drop=True)
   final_dframe = final_dframe.drop(["num_users_reg", "num_users_nonreg"], axis=1)
   #final_dframe.to_csv(state_code + "_metrics_tools_March31st2019.csv")
   return (final_dframe, state_code)

# Proportion of Anonymous user logs in the total logs
# state_anon_percent_logs = {}
def get_percent_of_anon(schools_df):
    state_code = schools_df['school_server_code'].apply(lambda x: x.split('-')[1][:2]).unique()[0]
    school_server_code = ';'.join(schools_df['school_server_code'].unique())
    anon_percent = len(schools_df[schools_df["user_id"] == 0])/ len(schools_df) * 100
    state_anon_percent_logs[school_server_code] =  anon_percent
    return None

# To get metrics in a given date range
def get_metrics_in_daterange(schools_df, date_range):

    start_date = date_range[0]
    end_date = date_range[1]
    try:
      schools_df['state_code'] = schools_df['school_server_code'].apply(lambda x: x.split('-')[1][:2])
      schools_df['createdat_start'] = pandas.to_datetime(schools_df['createdat_start'], format="%Y-%m-%d %H:%M:%S")
      schools_df['createdat_end'] = pandas.to_datetime(schools_df['createdat_end'], format="%Y-%m-%d %H:%M:%S")
      #spurious_date_json_files = cumul_data[cumul_data['date_created'] > "2019-01-31"]
      schools_df = schools_df[schools_df['createdat_end'] >= pandas.to_datetime(start_date, format="%Y-%m-%d")]
      schools_df = schools_df[schools_df['createdat_end'] <= pandas.to_datetime(end_date, format="%Y-%m-%d")]
      state_code = schools_df['school_server_code'].apply(lambda x: x.split('-')[1][:2]).unique()[0]
    except Exception as e:
      print(e)
      import pdb
      pdb.set_trace()

    return get_indicators_tools_data(schools_df, state_code)

def get_clean_data(schools_df):

    def get_rid_of_spurious_dates(date_entry):
        # Modifying '2019-0-12' kind of dates to '2019-01-12'
        if not pandas.isnull(date_entry):
            if '2019-0-' in str(date_entry):
                dstring = date_entry.split('-')
                dstring[1] = '01'
                return '-'.join(dstring)
            else:
                return date_entry
        else:
            return date_entry

    schools_df['createdat_start'] = schools_df['createdat_start'].apply(lambda x: get_rid_of_spurious_dates(x))
    schools_df['createdat_end'] = schools_df['createdat_end'].apply(lambda x: get_rid_of_spurious_dates(x))
    return schools_df

#date_range = ["2018-07-01", "2018-12-31"]
# Manually removed spurious dates from rj (rj_json_tools_March31st2019.csv)
# These were date recorded as '2019-0-1' etc. There were around 10 logs of them
def get_tool_data_metrics(schools_tool_logs, date_range):
    schools_tool_logs = schools_tool_logs.dropna(subset=['session_id'])
    schools_tool_logs = get_clean_data(schools_tool_logs)
    schools_metrics_output = get_metrics_in_daterange(schools_tool_logs, date_range)
    return schools_metrics_output[0]
