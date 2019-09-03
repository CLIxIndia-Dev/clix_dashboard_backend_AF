#####################################################################################
'''
This part of the code fetches data from progress_csv which contain the modules data
'''
'''
This script is to collate all the progress csv data from syncthing data dump.
This is required for adoption study - extent of adoption of CLix platform by students and teachers.

To populate this data set - we do the following:
1. For each school, Fetch all the files available for each date (last timestamp of end of the month date during study period)
   These files represent a snapshot of school's student engagement (with platform modules) for that date.
2. Then actually fetch data and collate at state-level
Added code for extracting district level numbers
'''
import os
import re
import logging
from collections import defaultdict
import json
import itertools
import operator
import pandas
#from pyspark.context import SparkContext
#SparkContext.setSystemProperty('spark.driver.memory', '5g')
#sc = SparkContext(master="spark://10.1.84.40:7077", appName="CsvProcessingEngine")
#sc = SparkContext(master="local[4]", appName="CsvProcessingEngine")
#SparkContext.setSystemProperty('spark.driver.memory', '3g')

from datetime import datetime

def get_file_paths(data_path, schools_list, regex_file, regex_dir, date_range):
    '''
    Fetch all the file names(with full path) following a given filename pattern and in a given folder name pattern.
    :param data_path: parent folder containing all the data
    :param regex_file: filename's regex
    :param regex_dir: immediate parent directory's regex
    :return: List of tuples - (state_code, school_server_code, [-- List of csv files --])
    '''

    FilePath_list = list()

    regObj_file = re.compile(regex_file)
    regObj_dir = re.compile(regex_dir)
    regex_parent_dir = re.compile(r'gstudio')

    for root, dnames, fnames in os.walk(os.path.join(data_path)):
        for dname in dnames:
           if regex_parent_dir.match(dname):
                # Look for if you are in required school directory
                # Check if you are in the school directory given in the list of schools
                current_path = os.path.join(root, dname)
                school_server_code = current_path.split('/')[-2]
                if school_server_code in schools_list:
                 for d1name in os.listdir(os.path.join(root, dname)):
                    #If in gstudio folder do the following:
                    #Go to progress csv folder - to get actual csv filenames
                    if regObj_dir.match(d1name):
                        immediate_parent_path = os.path.join(root, dname, d1name)
                        folder_files = os.listdir(immediate_parent_path)
                        folder_contents = [each for each in folder_files if regObj_file.match(each)]
                        if not folder_contents:
                            logging.debug('No files for this folder: %s', immediate_parent_path)
                        else:
                            for eachfile in folder_contents:
                                eachfile_path = os.path.join(immediate_parent_path, eachfile)
                                school_server_code = '-'.join(eachfile.split('-')[:2])
                                state_code = school_server_code.split('-')[1][:2]
                                date_created = eachfile.split('-')[-2]
                                date_copied = date_created[:4]+ '-' + date_created[4:6] + '-' + date_created[6:8]
                                date_copied_ft = datetime.strptime(date_copied, "%Y-%m-%d")
                                up_bound = datetime.strptime(date_range[1], "%Y-%m-%d")
                                low_bound = datetime.strptime(date_range[0], "%Y-%m-%d")
                                if (low_bound <= date_copied_ft <= up_bound):
                                    FilePath_list.append((state_code, school_server_code, eachfile_path))
    return FilePath_list

def filter_out_latest(list_of_file_paths):

        '''
        Filters out files, to keep only latest time stamp on last available day of any month for a particular unit
        :param list_of_file_paths: list of all the file names of a school
        :return: List of Only filtered file names
        '''
        #To construct the tuple of (timestamp, unit_name and filepath)
        modified_list = defaultdict(list)
        for eachfile in list_of_file_paths:
            filename = eachfile[2].split('/')[-1]
            unit_name = '_'.join(filename.split('-')[2:-2])
            time_stamp = datetime.strptime(' '.join(filename.split('-')[-2:]).split('.')[0], '%Y%m%d %Hh%Mm')
            modified_list[unit_name].append((time_stamp, eachfile[2]))

        final_list_of_paths = list()
        state_code = list_of_file_paths[0][0]
        school_code = list_of_file_paths[0][1]

        for each_unit in modified_list.keys():
            unit_level_files = modified_list[each_unit]
            files_dframe = pandas.DataFrame(unit_level_files, columns=['date', 'file'])
            files_dframe['month'] = files_dframe['date'].apply(lambda x: x.month)
            def month_end(df):
                last_timestamp = df['date'].max()
                return df[df['date'] == last_timestamp][['date', 'file']]
            filter_df = files_dframe.groupby(['month']).apply(month_end).reset_index()
            for each in  filter_df['file'].tolist():
                final_list_of_paths.append((state_code, school_code, each_unit, each))

        return final_list_of_paths

tool_mod_map = {'ice' : ["[u'Proportional Reasoning']"], 'astroamer_element_hunt_activity' : ["[u'Basic Astronomy']"],
                'policesquad' : ["[u'Geometric Reasoning Part I']", "[u'Geometric Reasoning Part II']"],
                'astroamer_moon_track' : ["[u'Basic Astronomy']"],
                'food_sharing_tool' : ["[u'Proportional Reasoning']"],
                'astroamer_planet_trek_activity' : ["[u'Basic Astronomy']"], 'ages_puzzle' : ["[u'Linear Equations']"],
                'coins_puzzle': ["[u'Linear Equations']"], 'factorisation': ["[u'Linear Equations']"],
                'rationpatterns': ["[u'Proportional Reasoning']"]}


def unit_level_progress(list_of_file_paths, school_code, state_code):

        #school_code = list_of_file_paths[0][1]
        #state_code = list_of_file_paths[0][0]

        print('#################################')
        print('Working on school: {0}', school_code)
        print('###################################')
        modified_list = defaultdict(list)
        dates_server_on = defaultdict(list)
        for eachfile in list_of_file_paths:
            filename = eachfile[2].split('/')[-1]
            unit_name = '_'.join(filename.split('-')[2:-2])
            time_stamp = datetime.strptime(' '.join(filename.split('-')[-2:]).split('.')[0], '%Y%m%d %Hh%Mm')
            date_stamp = time_stamp.date()
            dates_server_on[school_code].append(date_stamp)
            modified_list[unit_name].append((time_stamp, eachfile[2], date_stamp))

        cols_required = ['server_id', 'school_name', 'school_code', 'module_name',
                         'unit_name', 'username', 'user_id', 'grade', 'enrollment_status',
                         'buddy_userids', 'total_lessons', 'lessons_visited',
                         'percentage_lessons_visited', 'total_activities',
                         'activities_visited', 'percentage_activities_visited']

        def pick_first_instance(df):
            return df[df['timestamp'] == min(df['timestamp'])]

        school_collated_files = []
        for each_unit in modified_list.keys():

            collated_list = []
            unit_level_files = modified_list[each_unit]
            for eachfile in unit_level_files:
                try:
                    file_dframe = pandas.read_csv(eachfile[1])
                    file_dframe = file_dframe[cols_required]
                    file_dframe['timestamp'] = eachfile[0]
                    file_dframe['date_created'] = eachfile[2]
                    collated_list.append(file_dframe)
                except Exception as e:
                    print("File empty - {0}", eachfile[1])
            try:
                if not collated_list:
                   unit_collated_files = pandas.DataFrame()
                   unit_dframe = pandas.DataFrame()
                   print("Collated list of unit level files is empty for school - {0}", school_code)
                else:
                   unit_collated_files = pandas.concat(collated_list, ignore_index=True)
                   unit_dframe = unit_collated_files.groupby(['user_id', 'unit_name',
                       'lessons_visited', 'activities_visited']).apply(lambda x: pick_first_instance(x)).reset_index(level=None, drop=True)
            except Exception as e:
                print(e)
                print(collated_list)
                print('problem in concatenation of dataframes')
                print('Assigning empty dataframe')
                #unit_dframe = pandas.DataFrame()
                raise Exception(e)

            school_collated_files.append(unit_dframe)
        school_dframe = pandas.concat(school_collated_files)
        school_dframe['state_code'] = state_code
        print('#######################')
        print(school_dframe.head())
        print('#######################')
        return (school_dframe, dates_server_on)

def get_server_logs(list_of_file_paths):

    school_code = list_of_file_paths[0][1]
    state_code = list_of_file_paths[0][0]
    print('#################################')
    print('Working on school: {0}', school_code)
    print('###################################')
    modified_list = defaultdict(list)
    dates_server_on = defaultdict(list)
    for eachfile in list_of_file_paths:
        filename = eachfile[2].split('/')[-1]
        time_stamp = datetime.strptime(' '.join(filename.split('-')[-2:]).split('.')[0], '%Y%m%d %Hh%Mm')
        date_stamp = time_stamp.date()
        dates_server_on[school_code].append(date_stamp)
    return dates_server_on

def get_schools_module_data(parent_directory, schools_list, date_range, state):

 working_dir = os.getcwd()
 logging.basicConfig(filename=working_dir + '/progrss_csv_session_outputs.log', level=logging.DEBUG)

 print('This script parses through the top directory provided by user to fetch progress csv files '
       '(hopefully saved in gstudio folder) and \n extract information from each '
       'of them at module level.\n')
 print('---------------------------------------------------------------------------------')
 regex_file = r'.+(csv)$'
 regex_dir = r'gstudio-exported-users-analytics-csvs'

# All progress csv files  - indexed by state and school server code
#schools_list = ['2031011-mz11', '2031020-mz20', '2031022-mz22']

 csv_files = get_file_paths(parent_directory, schools_list, regex_file, regex_dir, date_range)

 if not csv_files:
     print('No files for the given school list are found: {}'.format(schools_list))
     return pandas.DataFrame()

 school_prog_csv = {}
 def accumulate(l_tuples):
    iter_by_school = itertools.groupby(l_tuples, operator.itemgetter(1))
    for school, school_data in iter_by_school:
       yield school, unit_level_progress(school_data, school, state)

 school_prog_csv = accumulate(csv_files)

 schools_module_dframe = pandas.concat([data[0] for each, data  in school_prog_csv], ignore_index=True)
 schools_module_dframe = schools_module_dframe[schools_module_dframe['user_id'] > 100]

 schools_server_logs = get_server_logs(csv_files)
 #schools_server_dframe = pandas.concat([pandas.DataFrame({'school_server_code': school,
 #'dates_server_on': dates}) for school, dates in server_logs.items()])

 def clean_code(x):
      if x.split('-')[0] == 'nan':
          return '-' + x.split('-')[1]
      else:
          return x

 def get_school_server_code(df_row):
     school_code = str(df_row['school_code']).split('.')[0]
     server_id = str(df_row['server_id'])
     return clean_code(school_code + '-' + server_id)

 schools_module_dframe['school_server_code'] = schools_module_dframe.apply(lambda x: get_school_server_code(x), axis=1)
 return (schools_module_dframe, schools_server_logs)
