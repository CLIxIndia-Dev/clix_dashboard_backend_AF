# This file contains collection of functions to fetch tools and modules data from raw syncthing data

import pexpect
import pandas
import re
import config.clix_config as clix_config
from scripts.clix_platform_data_processing.tools_proc import fetch_log_level_data_tools, get_tool_data_metrics
from scripts.clix_platform_data_processing.modules_proc import get_schools_module_data

syncthing_live_data_path = clix_config.local_dst

def get_tools_data(schools_list, date_range, state):
    '''
    To get tools data with metrics calculated per day
    '''
    tools_log_level_data = fetch_log_level_data_tools(syncthing_live_data_path, schools_list, state)
    if tools_log_level_data.empty:
        return pandas.DataFrame()
    return get_tool_data_metrics(tools_log_level_data, date_range)

def get_modules_data(schools_list, date_range, state):
    '''
    To get modules data for the specified schools and given date range
    '''
    modules_school_data = get_schools_module_data(syncthing_live_data_path, schools_list, date_range, state)
    if modules_school_data.empty:
        return pandas.DataFrame()
    return modules_school_data
