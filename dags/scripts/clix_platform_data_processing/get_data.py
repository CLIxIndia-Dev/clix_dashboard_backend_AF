# This file contains collection of functions to fetch tools and modules data from raw syncthing data

import pexpect
import pandas
import re
import config.clix_config as clix_config
from scripts.clix_platform_data_processing.tools_proc import fetch_log_level_data_tools, get_tool_data_metrics
from scripts.clix_platform_data_processing.modules_proc import get_schools_module_data

import os
import re
import logging
from collections import defaultdict
import json
import itertools
import operator
import pandas

syncthing_live_data_path = clix_config.local_dst

tool_mod_map = {'ice' : ["[u'Proportional Reasoning']"], 'astroamer_element_hunt_activity' : ["[u'Basic Astronomy']"],
                'policesquad' : ["[u'Geometric Reasoning Part I']", "[u'Geometric Reasoning Part II']"],
                'astroamer_moon_track' : ["[u'Basic Astronomy']"],
                'food_sharing_tool' : ["[u'Proportional Reasoning']"],
                'astroamer_planet_trek_activity' : ["[u'Basic Astronomy']"], 'ages_puzzle' : ["[u'Linear Equations']"],
                'coins_puzzle': ["[u'Linear Equations']"], 'factorisation': ["[u'Linear Equations']"],
                'rationpatterns': ["[u'Proportional Reasoning']"]}

def get_tools_data(schools_list, date_range, state):
    '''
    To get tools data with metrics calculated per day.
    To get tools attendance on each day for all the schools for the dates in the daterange.
    '''
    tools_log_level_data = fetch_log_level_data_tools(syncthing_live_data_path, schools_list, state)
    if tools_log_level_data.empty:
        return pandas.DataFrame()
    return get_tool_data_metrics(tools_log_level_data, date_range)

def get_modules_data(schools_list, date_range, state):
    '''
    To get modules data for the specified schools and given date range
    '''
    modules_school_data, server_log_data = get_schools_module_data(syncthing_live_data_path, schools_list, date_range, state)
    if modules_school_data.empty:
        return pandas.DataFrame(), defaultdict(list)
    return modules_school_data, server_log_data

def get_lab_usage(school_dframe, school_tool_data, school_server_logs):

        '''
        #Here we are trying to find users who have tools logs but no progress csv logs
        #But whenever there is tool log, progress csv has to be generated due to the server being
        # on when the tool was being used. SO we just add them up to the total number of days
        tools_only_users = set(school_tool_data['user_id'].tolist()) - set(school_dframe['user_id'].tolist())
        if not (bool(tools_only_users)):
            num_school_tool_only_logs = 0
        else:
            num_school_tool_only_logs = len(school_tool_data[school_tool_data['user_id'].isin(tools_only_users)]['date_created'].unique())
        '''

        tools_only = defaultdict(list)
        modules_only = defaultdict(list)
        modules_n_tools = defaultdict(list)

        #To capture users who did only tool logs and didnt appear in module usage logs
        if not school_tool_data.empty:
            tool_users = set(school_tool_data['user_id'].unique())
        else:
            tool_users = set()

        module_users = set(school_dframe['user_id'].unique())
        tool_only_users = list(tool_users - module_users)

        # server up logs of school
        # Code to pause if the days on which tools were used but there were no server logs registered
        server_on_dates = set(school_server_logs)
        adtnl_days = 0
        if tool_only_users and not(all([elem == 0 for elem in tool_only_users])):
           adtnl_tool_logs = school_tool_data.loc[school_tool_data['user_id'].isin(tool_only_users)]['createdat_end'].unique()
           adtnl_tool_logs_new = pandas.Series(pandas.to_datetime(adtnl_tool_logs, format="%Y-%m-%d %H:%M:%S")).apply(lambda x: str(x.date()))
           adtnl_days = len(set(adtnl_tool_logs_new) - server_on_dates)
           if not(adtnl_days == 0 or adtnl_days == 1):
               pass

        for each_user in school_dframe['user_id'].unique():
            '''
            This code tries to find the non-overlapping access of tools and modules section of the platform
            using tools and course modules date.
            Objective: for a given user, find the module only logs, module and tools logs (these are tool logs, which
            were generated while using module and tool only logs)  and finally server up with no activity.

            '''
            df = school_dframe[school_dframe['user_id'] == each_user]
            user = each_user

            #Tool logs of user from tools data
            if not school_tool_data.empty:
                tool_logs = school_tool_data[school_tool_data["user_id"] == user]
                tool_logs['createdat_end'] = pandas.to_datetime(tool_logs["createdat_end"], format="%Y-%m-%d %H:%M:%S")
            else:
                tool_logs = pandas.DataFrame()

            # Module activity logs of user
            module_dates = df['timestamp'].tolist()
            if tool_logs.empty:
                # If tool_logs is empty, there was no tool activity for user, only module activity was there
                tools_only[user].append(None)
                modules_n_tools[user].append(None)
                modul_tool_capture = list()
            else:
                modul_tool_capture = list()
                # Tool activity was there for this user
                for each_row in tool_logs.iterrows():

                    tool_module = tool_mod_map[each_row[1]['tool_name']]
                    each_tool_ts = each_row[1]['createdat_end']

                    # Get all the module activities after the tool log happened
                    # which correspond to the same module as tool
                    module_dates_df = df[df['module_name'].isin(tool_module)]

                    if not(module_dates_df.empty):
                        module_dates_tools = module_dates_df['timestamp']
                        user_modul_activity = [each for each in module_dates_tools if each_tool_ts <= each]
                    else:
                        user_modul_activity = []

                    if not user_modul_activity:
                        # If there is no module activity for user after tool log, then tool and
                        # module activity together didnt happen
                        tools_only[user].append(each_tool_ts)
                    else:
                        # If there was module activity after tool log, we assume that tool activity happened
                        # through module. And also only if both correspond to the same module.
                        mod_activ_capture = min(user_modul_activity)
                        modules_n_tools[user].append(mod_activ_capture)
                        #Picking module logs which are overlapping with tools
                        modul_tool_capture.append(mod_activ_capture)

            if modul_tool_capture:
                modul_only_dates = [each for each in module_dates if not(pandas.Series([each]).isin(modul_tool_capture)[0])]
                for each in modul_only_dates:
                    modules_only[user].append(each)
            else:
                modul_only_dates = module_dates
                for each in modul_only_dates:
                    modules_only[user].append(each)


        logs_tools_only = set([log.date() for tool_logs in tools_only.values() for log in tool_logs if log])

        #num_tool_only = len(logs_tools_only)
        try:
            logs_module_only = set([log.date() for mod_logs in modules_only.values() for log in mod_logs if log])
        except Exception as e:
            print(e)
            import pdb
            pdb.set_trace()

        logs_modul_tools = set([log.date() for tool_logs in modules_n_tools.values() for log in tool_logs if log])
        # As the module only log of one user may be the modul-tool log of another user, we are removing mod-tool logs
        # from modul-only logs at school level, while counting the number.
        num_of_common_logs = len(logs_module_only.intersection(logs_modul_tools))
        num_module_only = len(logs_module_only) - num_of_common_logs

        num_of_common_tool_logs = len(logs_tools_only.intersection(logs_modul_tools))
        num_tool_only = len(logs_tools_only) - num_of_common_tool_logs

        num_tool_modul_logs = len(logs_modul_tools)

        '''
        This was an experiment to
        find if there were any tool activities and no server logs generated.
        Which is not remotely possible as server has to be on for tools to
        work and whenever server is on progress csv is generated.
        So this could be case of inconsistent treatment of buddy logins in tools
        and modules sectio of code.
        So we consider that these logs are already counted in either tools only logs or
        server up logs or module only logs.
        Incident of these cases is also very low. Though the exact number is not
        estimated.

        # Here we are trying to find users who have tools logs but no progress csv logs
        # But whenever there is tool log, progress csv has to be generated due to the server being
        # on when the tool was being used. SO we just add them up to the total number of days
        tools_only_users = set(school_tool_data['user_id'].tolist()) - set(school_dframe['user_id'].tolist())
        if not (bool(tools_only_users)):
            num_school_tool_only_logs = 0
        else:
            num_school_tool_only_logs_temp = set(school_tool_data[school_tool_data['user_id'].isin(tools_only_users)][
                'date_created'].unique())
            temp_all_dates = logs_modul_tools.union(logs_module_only, logs_tools_only) - num_school_tool_only_logs_temp
            temp_all_dates_1 = server_on_dates - num_school_tool_only_logs_temp
            print('In school - {}', school_dframe['server_id'].unique()[0])
            print('tool logs not in super set dates', temp_all_dates)
            print('tool logs not in server on dates', temp_all_dates_1)

        #print('Super Tool only activity is {}', tools_only_users)
        '''
        days_server_wo_activity = (len(server_on_dates) + adtnl_days) - num_tool_modul_logs - num_module_only - (num_tool_only + adtnl_days)

        school_dframe['days_server_wo_activity'] = days_server_wo_activity
        school_dframe['tools_only_activity'] = num_tool_only + adtnl_days
        school_dframe['module_only_activity'] = num_module_only
        school_dframe['tool_with_module_activity'] = num_tool_modul_logs
        school_dframe['total_days_server_on'] = len(server_on_dates) + adtnl_days
        return school_dframe
