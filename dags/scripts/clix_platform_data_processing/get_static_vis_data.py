# This file has all the functions required to get different metrics of a schools
# using syncthing data from the school_syncthing_data_live folder
from scripts.clix_platform_data_processing.get_data import get_modules_data, get_tools_data, get_lab_usage
import config.clix_config as clix_config

import pandas

modules_domain_map = {"e" : ["[u'English Beginner']", "[u'English Elementary']", "[u'i2C']"],
                      "m" : ["[u'Geometric Reasoning Part I']", "[u'Geometric Reasoning Part II']", "[u'Linear Equations']",
                             "[u'Proportional Reasoning']"],
                      "s" : ["[u'Atomic Structure']", "[u'Sound']", "[u'Understanding Motion']", "[u'Basic Astronomy']",
                             "[u'Health and Disease']", "[u'Ecosystem']", "[u'Reflecting on Values']"]
                      }

tools_domain_map = {
        'e': [],
        'm': ['ice', 'factorisation', 'coins_puzzle','rationpatterns', 'food_sharing_tool', 'ages_puzzle', 'policesquad'],
        's': ['astroamer_element_hunt_activity', 'astroamer_moon_track', 'astroamer_planet_trek_activity']
    }

tools = ['ice', 'factorisation', 'coins_puzzle','rationpatterns', 'food_sharing_tool', 'ages_puzzle', 'policesquad',
         'astroamer_element_hunt_activity', 'astroamer_moon_track', 'astroamer_planet_trek_activity']

modules = ["[u'English Beginner']", "[u'English Elementary']", "[u'Geometric Reasoning Part I']",
           "[u'Geometric Reasoning Part II']", "[u'Linear Equations']", "[u'Proportional Reasoning']",
           "[u'Atomic Structure']", "[u'Sound']", "[u'Understanding Motion']", "[u'Basic Astronomy']",
           "[u'Health and Disease']", "[u'Ecosystem']", "[u'Reflecting on Values']", "[u'I2c']"]

tools_modules_server_logs_datapath = clix_config.local_dst_state_data_logs

def get_log_level_data(schools, state, date_range):
     tools_data_latest  = get_tools_data(schools, date_range, state)
     (modules_data_latest, server_log_data_latest) = get_modules_data(schools, date_range, state)
     return tools_data_latest, (modules_data_latest, server_log_data_latest)

def get_engagement_metrics(df, tools_module_flag):

    if (tools_module_flag == 'tools'):
        #domain_map = tools_domain_map
        tools_or_modules = tools
        m_column = 'tool_name'

    elif (tools_module_flag == 'modules'):
        #domain_map = modules_domain_map
        tools_or_modules = modules
        m_column = 'module_name'

    #domains = ['e', 'm', 's']
    df['month'] = pandas.to_datetime(df['date_created'], format="%Y-%m-%d").apply(lambda x: x.month)

    def get_num_stud(df_month, dom, m_column):
        df_month['stud_per_month_' + dom] = len(df_month.loc[df_month[m_column].isin([dom])]['user_id'].unique())
        return df_month

    def get_num_days(df_month, dom, m_column):
        df_month['days_per_month_' + dom] = len(df_month.loc[df_month[m_column].isin([dom])]['date_created'].unique())
        return df_month

    def get_num_studperday(df_month, dom, m_column):
        m_logs = df_month.loc[df_month[m_column].isin([dom])]
        if not m_logs.empty:
            def get_daily_numstud(x):
                return len(x['user_id'].unique())
            daily_num_stud = m_logs.groupby(['date_created']).apply(lambda x: get_daily_numstud(x))
            df_month['studperday_per_month_' + dom] = daily_num_stud.mean()
            return df_month
        else:
            df_month['studperday_per_month_' + dom] = 0
            return df_month

    if tools_module_flag == 'tools':

        def get_time_spent_day(df_month, each_tool):
            # Trying to capture range of average daily time spent
            # in a month across all schools in a state.
            tool_logs = df_month.loc[df_month['tool_name'].isin([each_tool])]
            if not tool_logs.empty:
                def get_daily_time(x):
                    return x.groupby(['session_id', 'user_id']).apply(lambda x: x['time_spent'].unique()[0]).sum()
                daily_time_spent = tool_logs.groupby(['date_created']).apply(lambda x: get_daily_time(x))
                df_month['avg_time_spent_month_' + each_tool] = daily_time_spent.mean()
                return df_month
            else:
                df_month['avg_time_spent_month_' + each_tool] = 0
                return df_month

        for each in tools:
            #To get total time spent (averaged to per day) by all students in a month for a particular domain
            df = df.groupby(['month']).apply(lambda x: get_time_spent_day(x, each)).reset_index(level=None, drop=True)
            df['avg_timesp_year_' + each] = df.groupby(['month']).apply(lambda x: x['avg_time_spent_month_' + each]).mean()


    if tools_module_flag == 'modules':

        def get_stud_visit_activit(df_month, each_module):
            modul_dframe = df_month.loc[df_month['module_name'].isin([each_module])]
            df_month['stud_visit_activ_month_' + each_module] = len(modul_dframe[modul_dframe['percentage_activities_visited'] >= 50]['user_id'].unique())
            return df_month

        #To get total number of students who visited atleast 50% of the activities
        for each in modules:
            df = df.groupby(['month']).apply(lambda x: get_stud_visit_activit(x, each)).reset_index(level=None, drop=True)
            agg_modul_df = df.loc[df['module_name'].isin([each])]
            df['stud_vist_activit_year_' + each] = len(agg_modul_df[agg_modul_df['percentage_activities_visited'] >= 50]['user_id'].unique())

    for each in tools_or_modules:
        df = df.groupby(['month']).apply(lambda x: get_num_stud(x, each, m_column)).reset_index(level=None, drop=True)
        df = df.groupby(['month']).apply(lambda x: get_num_days(x, each, m_column)).reset_index(level=None, drop=True)
        df['total_stud_' + each] = len(df.loc[df[m_column].isin([each])]['user_id'].unique())
        df['total_days_' + each] = len(df.loc[df[m_column].isin([each])]['date_created'].unique())
        df = df.groupby(['month']).apply(lambda x: get_num_studperday(x, each, m_column)).reset_index(level=None, drop=True)
        df['studperday_year_' + each] = df.groupby(['month']).apply(lambda x: x['studperday_per_month_' + each]).mean()

    return df

def clean_code(x):
    if x.split('-')[0] == 'nan':
        return '-' + x.split('-')[1]
    else:
        return x

def get_top_50_rows(df):
    df['total'] = df.sum(axis=1)
    df_new = df.sort_values(by='total', ascending=False)
    df_new50 = df_new.iloc[:50]
    return df_new50.drop(['total'], axis=1)

def get_num_stud_tools(state_tools_df):
    tool_cols_total_stud = ['total_stud_' + each for each in tools]
    sv_tool_total_stud = ['school_server_code'] + tool_cols_total_stud
    tool_stud_sv = state_tools_df[sv_tool_total_stud].drop_duplicates(['school_server_code'])
    total_stud_col_dict = {each: '_'.join(each.split('_')[2:]) for each in tool_cols_total_stud}
    tool_stud_sv_new = tool_stud_sv.rename(columns = total_stud_col_dict)
    return get_top_50_rows(tool_stud_sv_new)

def get_num_days_tools(state_tools_df):
    tool_cols_total_days = ['total_days_' + each for each in tools]
    sv_tool_total_days = ['school_server_code'] + tool_cols_total_days
    tool_days_sv = state_tools_df[sv_tool_total_days].drop_duplicates(['school_server_code'])
    total_days_col_dict = {each: '_'.join(each.split('_')[2:]) for each in tool_cols_total_days}
    tool_days_sv_new = tool_days_sv.rename(columns = total_days_col_dict)
    return get_top_50_rows(tool_days_sv_new)

def get_avgtime_perday_tools(state_tools_df):
    tool_cols_avg_time = ['avg_timesp_year_' + each for each in tools]
    sv_tool_avg_timesp = ['school_server_code'] + tool_cols_avg_time
    tool_timesp_sv = state_tools_df[sv_tool_avg_timesp].drop_duplicates(['school_server_code'])
    total_timesp_col_dict = {each: '_'.join(each.split('_')[3:]) for each in tool_cols_avg_time}
    tool_timesp_sv_new = tool_timesp_sv.rename(columns = total_timesp_col_dict)
    return get_top_50_rows(tool_timesp_sv_new)

def get_studperday_tools(state_tools_df):
    tool_cols_studperday = ['studperday_year_' + each for each in tools]
    sv_tool_studperday = ['school_server_code'] + tool_cols_studperday
    tool_studperday_sv = state_tools_df[sv_tool_studperday].drop_duplicates(['school_server_code'])
    studperday_col_dict = {each: '_'.join(each.split('_')[2:]) for each in tool_cols_studperday}
    tool_studperday_sv_new = tool_studperday_sv.rename(columns = studperday_col_dict)
    return get_top_50_rows(tool_studperday_sv_new)

def get_avg_percnt_visits_modules(state_modules_df):
    module_cols_percnt_activ = ['stud_vist_activit_year_' + each for each in modules]
    sv_module_visit_activ = ['school_server_code'] + module_cols_percnt_activ
    module_activ_visit_sv = state_modules_df[sv_module_visit_activ].drop_duplicates(['school_server_code'])
    percnt_activ_col_dict_mod = {each: '_'.join(each.split('_')[4:]).split("'")[1] for each in module_cols_percnt_activ}
    module_activ_visit_sv_new = module_activ_visit_sv.rename(columns = percnt_activ_col_dict_mod)
    return get_top_50_rows(module_activ_visit_sv_new)

def get_num_stud_modules(state_modules_df):
    module_cols_total_stud = ['total_stud_' + each for each in modules]
    sv_module_total_stud = ['school_server_code'] + module_cols_total_stud
    module_stud_sv = state_modules_df[sv_module_total_stud].drop_duplicates(['school_server_code'])
    total_stud_col_dict_mod = {each: '_'.join(each.split('_')[2:]).split("'")[1] for each in module_cols_total_stud}
    module_stud_sv_new = module_stud_sv.rename(columns = total_stud_col_dict_mod)
    return get_top_50_rows(module_stud_sv_new)

def get_num_days_modules(state_modules_df):
    module_cols_total_days = ['total_days_' + each for each in modules]
    sv_module_total_days = ['school_server_code'] + module_cols_total_days
    module_days_sv = state_modules_df[sv_module_total_days].drop_duplicates(['school_server_code'])
    total_days_col_dict_mod = {each: '_'.join(each.split('_')[2:]).split("'")[1] for each in module_cols_total_days}
    module_days_sv_new = module_days_sv.rename(columns = total_days_col_dict_mod)
    return get_top_50_rows(module_days_sv_new)

def get_studperday_modules(state_modules_df):
    module_cols_total_days = ['total_days_' + each for each in modules]
    sv_module_total_days = ['school_server_code'] + module_cols_total_days
    module_days_sv = state_modules_df[sv_module_total_days].drop_duplicates(['school_server_code'])
    total_days_col_dict_mod = {each: '_'.join(each.split('_')[2:]).split("'")[1] for each in module_cols_total_days}
    module_days_sv_new = module_days_sv.rename(columns = total_days_col_dict_mod)
    return get_top_50_rows(module_days_sv_new)
