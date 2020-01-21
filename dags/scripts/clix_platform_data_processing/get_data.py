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
from datetime import datetime

syncthing_live_data_path = clix_config.local_dst

tool_mod_map = {'ice' : ["[u'Proportional Reasoning']"], 'astroamer_element_hunt_activity' : ["[u'Basic Astronomy']"],
                'policesquad' : ["[u'Geometric Reasoning Part I']", "[u'Geometric Reasoning Part II']"],
                'astroamer_moon_track' : ["[u'Basic Astronomy']"],
                'food_sharing_tool' : ["[u'Proportional Reasoning']"],
                'astroamer_planet_trek_activity' : ["[u'Basic Astronomy']"], 'ages_puzzle' : ["[u'Linear Equations']"],
                'coins_puzzle': ["[u'Linear Equations']"], 'factorisation': ["[u'Linear Equations']"],
                'rationpatterns': ["[u'Proportional Reasoning']"]}

all_modules = ["[u'Proportional Reasoning']", "[u'Basic Astronomy']",
                "[u'Geometric Reasoning Part I']", "[u'Geometric Reasoning Part II']",
                "[u'Basic Astronomy']", "[u'Proportional Reasoning']", "[u'Basic Astronomy']", "[u'Linear Equations']",
                "[u'Linear Equations']", "[u'Linear Equations']", "[u'Proportional Reasoning']"]

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
        Following are some of the points to note:
         - We are trying to estimate number of days only tools are done, only modules are done and modules-tools done together
         - we know timestamp of module usage upto the nearest days
         - we know exact timestamp of tool usage
         - Key idea we want to use - If a student does a module and the related tool within 7 days(earlier or later), we want to consider
           that the student has done those tools and modules together
         - To use this idea, we need to combine a student's logs of modules and tools in some way
         - As we know more precisely about tool log timestamps, we iterate through each tool log of a student and then check if there
           is any related module entry for that specific user
         - This way we may be completely ignoring logs of students who have only tool logs and no module logs(the way we
           iterate through for-loop). So we get these users seperately as 'tool_only_users'
         - For a given school, we fetch tools data, modules data and server_log_dates
         - Objective is to identify days on which tools were done along with modules, i.e are done 'together' by a student
         - 'together' is defined as plus/minus one day difference between tool log and module log of a student
         - Also, for a given student, we check only those tools which correspond to a given module example: 'astroamer_element_hunt_activity' tool
           is in ["[u'Basic Astronomy']" module
         - Following are the steps followed:
            1. For a school, identify users who did only tools (no module usage). 'adtnl_days' is calculated,
               these are dates on which tool log is present but module log is not present.
            2. For each user in modules data, we do the following
                a. identify user's tool logs
                b. For each of these tool logs:
                  a. identify the module corresponding to the tool log
                  b. see if user has any log for identified module in module_data of user
                     -  if there is a log, whether it is within 1 day plus/minus to the tool log
                     -  if there is any such module log, it is considered to be done along with the tool log of the user
                  c. this is counted as 'modules_n_tools'
                c. similarly, 'tools_only' and 'module_only'  logs are calculated
            3. Then we combine these three sets of logs across all users of a school. To this end we compare all three sets across all the users.
            4. There are four types of days we want to identify:
                - days on which all students used tools
                - days on which all students used modules
                - days on which some students used only modules, some students used only tools and some used both modules and tools
                - days on which nothing was used but server was up

        '''
        # defaultdict to be able to store list for each user
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

        # here we are finding logs of tool_only_users. they correspond to days on which module log was not registered at all due to
        # no module activity or systems were on only for small amount of time during which tool was used (which didnt overlap with module
        # registering times)
        server_on_dates = set(school_server_logs)
        adtnl_days = 0
        if tool_only_users and not(all([elem == 0 for elem in tool_only_users])):
           adtnl_tool_logs = school_tool_data.loc[school_tool_data['user_id'].isin(tool_only_users)]['createdat_end'].unique()
           adtnl_tool_logs_new = pandas.Series(pandas.to_datetime(adtnl_tool_logs, format="%Y-%m-%d %H:%M:%S")).apply(lambda x: str(x.date()))
           # Issue with comparing string with datetime object resulted in error in finding the difference of sets
           # and that is resolved
           # there was also a glitch in accounting for logs of students who appear only in tools data.
           # earlier we ignored the possibility that logs of these students may be overlapping with logs of other students who have
           # both tools data and modules data. This could be because of some internal error, where only module logs of some students is
           # left out
           logs_adtnl_days = set(adtnl_tool_logs_new) - set([str(each) for each in server_on_dates])

        for each_user in school_dframe['user_id'].unique():
            '''
            This code tries to find the non-overlapping access of tools and modules section of the platform
            using tools and course modules date.
            Objective: for a given user, find the module only logs, module and tools logs (these are tool logs, which
            were generated while using modules), tool only logs and server up with no activity.

            '''
            df = school_dframe[school_dframe['user_id'] == each_user]
            user = each_user

            #Tool logs of user from tools data
            if not school_tool_data.empty:
                tool_logs = school_tool_data[school_tool_data["user_id"] == str(user)]
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

                    #If we consider only those modules which correspond to a tool based on the
                    # mapping tool_mod_map
                    tool_module = tool_mod_map[each_row[1]['tool_name']]

                    # Here we are using all modules, without considering only those
                    # modules which are mapped to a particular tool as in tool_mod_map
                    #tool_module = all_modules

                    each_tool_ts = each_row[1]['createdat_end']

                    # Get all the module activities corresponding to this tool log
                    module_dates_df = df[df['module_name'].isin(tool_module)]

                    if not(module_dates_df.empty):
                        module_dates_tools = module_dates_df['timestamp']

                        # we look at tool logs which happened in the interval of a week before or later
                        # than the module log
                        def both_in_a_week(module_date, tool_date):
                            return abs((module_date - tool_date).days) <= 2
                        user_modul_activity = [each for each in module_dates_tools if both_in_a_week(each, each_tool_ts)]

                    else:

                        user_modul_activity = []

                    if not user_modul_activity:

                        # If there is no module activity for user after(within a week) tool log, then tool and
                        # module activity together didnt happen
                        tools_only[user].append(each_tool_ts)

                    else:

                        # If there was module activity after tool log, we assume that tool activity happened
                        # through module. remember we are using module logs corresponding to tool under consideration
                        mod_activ_capture = user_modul_activity
                        modules_n_tools[user].extend(mod_activ_capture)

                        #Picking module logs which are overlapping with tools
                        # this is used to remove them from module_only logs
                        modul_tool_capture.extend(mod_activ_capture)

            if modul_tool_capture:
                modul_only_dates = [each for each in module_dates if not(pandas.Series([each]).isin(modul_tool_capture)[0])]
                for each in modul_only_dates:
                    modules_only[user].append(each)
            else:
                modul_only_dates = module_dates
                for each in modul_only_dates:
                    modules_only[user].append(each)

        # Now we combine three sets of logs for each student to arrive at three sets for the school
        logs_tools_only = set([log.date() for tool_logs in tools_only.values() for log in tool_logs if log])

        try:
            logs_module_only = set([log.date() for mod_logs in modules_only.values() for log in mod_logs if log])
        except Exception as e:
            print(e)
            import pdb
            pdb.set_trace()

        logs_modul_tools = set([log.date() for tool_logs in modules_n_tools.values() for log in tool_logs if log])

        # to identify logs on which some students did tools only and others did modules Only
        logs_tool_only_module_only = logs_tools_only.intersection(logs_module_only)

        # As the module only log date of one user may be the modul-tool log date of another user, we are removing mod-tool logs
        # from modul-only logs at school level, while counting the number.
        logs_module_common = logs_module_only.intersection(logs_modul_tools)

        # considering module only as those days in which all students did only modules
        num_module_only = len((logs_module_only - logs_module_common) - logs_tool_only_module_only)

        # As the tool only log date of one user may be the modul-tool log date of another user, we are removing mod-tool logs
        # from tool-only logs at school level, while counting the number.
        logs_tool_common = logs_tools_only.intersection(logs_modul_tools)

        # we consider days on which all users did both modules and tools or some users did modules only and others
        # did tools only --- as modules and tools together days.
        num_tool_modul_logs = len(logs_modul_tools.union(logs_tool_only_module_only))

        # Accounting for additional logs when users only appear in tool logs but not in module logs
        adtnl_tool_day_logs =  {datetime.strptime(each, '%Y-%m-%d') for each in logs_adtnl_days}
        total_server_up_days = len(server_on_dates.union(adtnl_tool_day_logs))

        # considering tool only as those days in which all students did only tools
        # we are adding tool logs of users who didnt appear in the module logs
        num_tool_only = len(((logs_tools_only - logs_tool_common) - logs_tool_only_module_only).union(adtnl_tool_day_logs))

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
        days_server_wo_activity = (total_server_up_days - num_tool_modul_logs - num_module_only - num_tool_only)

        school_dframe['days_server_wo_activity'] = days_server_wo_activity
        school_dframe['tools_only_activity'] = num_tool_only
        school_dframe['module_only_activity'] = num_module_only
        school_dframe['tool_with_module_activity'] = num_tool_modul_logs
        school_dframe['total_days_server_on'] = total_server_up_days
        return school_dframe
