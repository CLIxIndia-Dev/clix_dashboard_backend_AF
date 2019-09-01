# This file has all the functions required to get different metrics of a schools
# using syncthing data from the school_syncthing_data_live folder
from scripts.clix_platform_data_processing.get_data import get_modules_data, get_tools_data
import pandas

def get_num_stud_daily(schools, state, date_range):

    tools_data = get_tools_data(schools, date_range, state)
    if not tools_data.empty:
        tools_data_temp = tools_data.groupby(['date_created', 'school_server_code'])['num_students_day'].apply(lambda x: x.unique()[0]).reset_index(level=None)
        num_stud_daily_tools = tools_data_temp.rename(columns={'num_students_day': 'num_stud_day_tools'})
    else:
        num_stud_daily_tools = pandas.DataFrame()

    modules_data = get_modules_data(schools, date_range, state)
    if not modules_data.empty:
        module_data_temp = modules_data.groupby(['school_server_code', 'date_created'])['user_id'].apply(lambda x: len(x.unique())).reset_index(level=None)
        num_stud_daily_modules = module_data_temp.rename(columns={'user_id': 'num_stud_day_modules'})
    else:
        num_stud_daily_modules = pandas.DataFrame()

    try:
      return pandas.merge(num_stud_daily_tools, num_stud_daily_modules, how='outer', left_on=['date_created', 'school_server_code'],
      right_on=['date_created', 'school_server_code'])
    except KeyError:
      if num_stud_daily_tools.empty:
          num_stud_daily_modules['num_stud_day_tools'] = 0
          return num_stud_daily_modules
      if num_stud_daily_modules.empty:
          num_stud_daily_tools['num_stud_day_modules'] = 0
          return num_stud_daily_tools
    except Exception as e:
        import pdb 
        pdb.set_trace()


def get_modulevisits(schools, state):
    pass

def get_timespent(schools, state):
    pass
