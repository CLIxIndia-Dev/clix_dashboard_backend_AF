# Collection of functions to process and laod tables for visualisation
# for a set of schools whose data has been updated through syncthing_data
from math import ceil

from scripts.clix_platform_data_processing.get_static_vis_data import get_log_level_data, get_engagement_metrics
from scripts.clix_platform_data_processing.get_static_vis_data import get_num_days_tools, get_num_stud_tools, get_avgtime_perday_tools, get_studperday_tools
from scripts.clix_platform_data_processing.get_static_vis_data import get_avg_percnt_visits_modules, get_num_stud_modules, clean_code
import config.clix_config as clix_config
import time
from datetime import datetime

from airflow.models import Variable
import pandas
import json
from functools import reduce

tools_modules_server_logs_datapath = clix_config.local_dst_state_data_logs

def load_to_db(metric_data):
    pass

def partition(lst, n=clix_config.num_school_chunks):
    if (len(lst) < n):
        return [lst, [], [], []]
    else:
        division = len(lst) / n
        return [lst[round(division * i):round(division * (i + 1))] for i in range(n)]

def process_school_data(state, chunk, **context):
    '''
    Function to process tables for a set of schools whose
    data has been updated through syncthing
    '''
    if state == 'tg':
        state_new  = 'ts'
    if state == 'ct':
        state_new = 'cg'
    else:
        state_new = state

    list_of_schools = context['ti'].xcom_pull(task_ids='sync_state_data_' + state_new, key = 'school_update_list')
    #if state == 'mz':
    #    list_of_schools = ['2041011-mz54', '2041001-mz44', '2031030-mz30', '2031022-mz22', '2031014-mz14', '2041015-mz58', '2041008-mz51', '2031017-mz17', '2031016-mz16', '2041006-mz49', '2031010-mz10', '2031006-mz6', '2041003-mz46', '2011009-mz86', '2031028-mz28', '2031021-mz21', '2031011-mz11', '2031025-mz25', '2041004-mz47', '2011005-mz82', '2011006-mz83', '2011008-mz85', '2031026-mz26', '2041013-mz56', '2011010-mz87', '2031009-mz9', '2031033-mz33', '2031027-mz27', '2041002-mz45', '2031004-mz4', '2031007-mz7', '2011002-mz79', '2031018-mz18', '2031034-mz34', '2031005-mz5', '2031008-mz8', '2031020-mz20']
    #if state == 'tg':
    #    list_of_schools =  ['4152031-tg231', '4221034-tg134', '4152082-tg282', '4141045-tg145', '4152033-tg233', '4112043-tg243', '4141038-tg138', '4202034-tg234', '4231019-tg119', '4231084-tg184', '4202057-tg257', '4231027-tg127', '4221067-tg167', '4202058-tg258', '4152002-tg202', '4202052-tg252', '4192099-tg299', '4231082-tg182', '4152092-tg292', '4202032-tg232', '4231051-tg151', '4183023-tg23', '4202007-tg207', '4202059-tg259', '4173079-tg79', '4202003-tg203', '4152038-tg238', '4152008-tg208', '4141008-tg108', '4231064-tg164', '4231023-tg123', '4152072-tg272', '4141035-tg135', '4202004-tg204', '4231058-tg158', '4152012-tg212', '4231057-tg157', '4202018-tg218', '4232045-tg245', '4141088-tg188', '4231036-tg136', '4192081-tg281', '4141090-tg190', '4231046-tg146', '4112005-tg205', '4232044-tg244', '4202047-tg247', '4202073-tg273', '4202098-tg298', '4141009-tg109', '4152024-tg224', '4173074-tg74']
    #if state == 'ct':
    #    list_of_schools = ['1011028-ct28', '1011004-ct4', '1011026-ct26', '1011014-ct14', '1011017-ct17', '1011011-ct11', '1011019-ct19', '1011023-ct23', '1011006-ct6', '1011008-ct8', '1011003-ct3', '1011016-ct16', '1011018-ct18', '1011009-ct9', '1011001-ct1', '1011005-ct5', '1011007-ct7', '1011022-ct22', '1011021-ct21', '1011010-ct10', '1011013-ct13', '1011020-ct20', '1011024-ct24']
    #if state == 'rj':
    #    list_of_schools = ['3051008-rj8', '3072042-rj92', '3072048-rj98', '3072044-rj94', '3072028-rj78', '3072031-rj81', '3072033-rj83', '3072040-rj90', '3072036-rj86', '3072029-rj79', '3072049-rj99', '3072032-rj82', '3072026-rj76', '3072030-rj80', '3072043-rj93', '3072027-rj77', '3072034-rj84', '3072047-rj97', '3072041-rj91', '3072035-rj85', '3072024-rj74', '3072025-rj75', '3072046-rj96', '3051010-rj10']

    schools_to_process = partition(list_of_schools)[chunk]
    print(schools_to_process)
    if schools_to_process:
        #print('Got all schools')
        #This date range is just to process latest data logs and then append them to already processed logs data
        # for each state
        date_range = [Variable.get('prev_update_date_static_' + state), Variable.get('curr_update_date_static_' + state)]
        schools_log_data = get_log_level_data(schools=schools_to_process, state=state, date_range=date_range)

        # Save chunk of tools data of a state
        tools_temp_path = tools_modules_server_logs_datapath + 'tools_temp' + '/' + state + '_' + str(chunk) + '.csv'
        schools_log_data[0].to_csv(tools_temp_path, index=False)
        # Save chunk of modules data of a state
        modules_temp_path = tools_modules_server_logs_datapath + 'modules_temp' + '/' + state + '_' + str(chunk) + '.csv'
        schools_log_data[1][0].to_csv(modules_temp_path, index=False)

        # Save chunk of serverlogs data of a state
        serverlogs_temp_path = tools_modules_server_logs_datapath + 'serverlogs_temp' + '/' + state + '_' + str(chunk) + '.json'
        server_logs_data = {key: [each.strftime('%Y%m%d') for each in values] for key, values in schools_log_data[1][1].items()}

        with open(serverlogs_temp_path, 'w', encoding='utf-8') as f:
          json.dump(server_logs_data, f, ensure_ascii=True, indent=4)
        f.close()

        if chunk >= clix_config.num_school_chunks - 1:
            Variable.set('prev_update_date_static_' + state, Variable.get('curr_update_date_static_' + state))
            Variable.set('curr_update_date_static_' + state, datetime.utcnow().date())
    else:

        print('No schools to process for this task')

    return None

def combine_chunks(state, **context):

    list_of_data_chunks_tools = []
    list_of_data_chunks_modules = []
    list_of_data_chunks_serverlogs = []

    for chunk in list(range(clix_config.num_school_chunks)):

        tools_temp_path = tools_modules_server_logs_datapath + 'tools_temp/' + state + '_' + str(chunk) + '.csv'
        list_of_data_chunks_tools.append(pandas.read_csv(tools_temp_path))

        modules_temp_path = tools_modules_server_logs_datapath + 'modules_temp/' + state + '_' + str(chunk) + '.csv'
        list_of_data_chunks_modules.append(pandas.read_csv(modules_temp_path))

        serverlogs_temp_path = tools_modules_server_logs_datapath + 'serverlogs_temp/' + state + '_' + str(chunk) + '.json'
        with open(serverlogs_temp_path, 'r', encoding='utf-8') as f:
          list_of_data_chunks_serverlogs.append(json.load(f))
        f.close()

    #Combine and save tools data of a state
    state_tools_logs_file = tools_modules_server_logs_datapath +  'tool_logs_' + state + '.csv'
    pandas.concat(list_of_data_chunks_tools).to_csv(state_tools_logs_file)
    #Combine and save modules data of a state
    state_modules_logs_file = tools_modules_server_logs_datapath + 'module_logs_' + state + '.csv'
    pandas.concat(list_of_data_chunks_modules).to_csv(state_modules_logs_file)
    #Combine and save serverlog file of a state
    state_server_logs_file = tools_modules_server_logs_datapath + 'server_logs_' + state + '.json'
    with open(state_server_logs_file, 'w', encoding='utf-8') as fp:
        server_logs_data = reduce(lambda x, y: x.update(y) or x, list_of_data_chunks_serverlogs)
        json.dump(server_logs_data, fp, ensure_ascii=True, indent=4)
    fp.close()

    return None

def get_state_static_vis_data(state, all_states_flag, **context):

    months_list = Variable.get('static_vis_range', deserialize_json=True)['months_list']

    # Get all the data files required for vis data generation
    if not all_states_flag:
        state_tools_logs_file = tools_modules_server_logs_datapath +  'tool_logs_' + state + '.csv'
        state_tools_data = pandas.read_csv(state_tools_logs_file)

        state_modules_logs_file = tools_modules_server_logs_datapath + 'module_logs_' + state + '.csv'
        state_modules_data = pandas.read_csv(state_modules_logs_file)
    else:
        list_of_all_state_df_tools = [pandas.read_csv(tools_modules_server_logs_datapath + 'tool_logs_' + each + '.csv') for each in clix_config.static_visuals_states]
        state_tools_data = pandas.concat(list_of_all_state_df_tools, ignore_index=True)

        list_of_all_state_df_modules = [pandas.read_csv(tools_modules_server_logs_datapath + 'module_logs_' + each + '.csv') for each in clix_config.static_visuals_states]
        state_modules_data = pandas.concat(list_of_all_state_df_modules, ignore_index=True)

    state_tools_data['date_created_new'] = pandas.to_datetime(state_tools_data['date_created'],
    format="%Y-%m-%d").apply(lambda x: x.strftime("%b%Y"))

    state_modules_data['date_created'] = pandas.to_datetime(state_modules_data['timestamp'],
    format = "%Y-%m-%d %H:%M:%S").apply(lambda x: x.date())
    state_modules_data['date_created_new'] = pandas.to_datetime(state_modules_data['timestamp'],
    format = "%Y-%m-%d %H:%M:%S").apply(lambda x: x.strftime("%b%Y"))

    for each_month in months_list:
        #Filter out monthly data for tools and modules
        if not each_month == 'all_months':
            state_tools_data_new = state_tools_data[state_tools_data['date_created_new'].isin([each_month])]
            state_modules_data_new = state_modules_data[state_modules_data['date_created_new'].isin([each_month])]
        else:
            state_tools_data_new = state_tools_data
            state_modules_data_new = state_modules_data

        state_tools_data_new = state_tools_data_new[~((state_tools_data_new['tool_name'] == 'policesquad') & (state_tools_data_new['time_spent'] >= 120))]
        state_tools_data_new = state_tools_data_new[state_tools_data_new['time_spent'] <= 200]

        state_vis_data_path = tools_modules_server_logs_datapath + 'vis_data/' + state + '_' + each_month

        if not state_tools_data_new.empty:
            state_tools_data_new = state_tools_data_new.groupby(["school_server_code"]).apply(lambda x: get_engagement_metrics(x,
              'tools')).reset_index(level=None, drop=True)

            # To get data for vis - Number of Students accessing different tools
            get_num_stud_tools(state_tools_data_new).to_csv( state_vis_data_path + '_toolwise_stud.csv', index=False)

            #To get data for vis -  Number of days of tools usage
            get_num_days_tools(state_tools_data_new).to_csv(state_vis_data_path + '_toolwise_days.csv', index=False)

            # To get data for vis - Number of students using tools per day
            get_studperday_tools(state_tools_data_new).to_csv(state_vis_data_path + '_toolwise_studperday.csv', index=False)

            # To get data for vis - Average time spent by students per day
            get_avgtime_perday_tools(state_tools_data_new).to_csv(state_vis_data_path + '_toolwise_timespperday.csv', index=False)

        # To get data for vis - Monthly variation of time spent
        #TODO

        #Modules engagement metrics
        if not state_modules_data_new.empty:

           school_server_code = [each[0] + each[1] for each in zip(state_modules_data_new['school_code'].apply(str).apply(lambda x: x.split('.')[0]).tolist(),
                              state_modules_data_new['server_id'].astype(str).apply(lambda x: '-' + x).tolist())]

           state_modules_data_new['school_server_code'] = pandas.Series(school_server_code, index=state_modules_data_new.index).apply(lambda x: clean_code(x))
           state_modules_data_new = state_modules_data_new.groupby(["school_server_code"]).apply(lambda x: get_engagement_metrics(x, 'modules')).reset_index(level=None, drop=True)

           # To get data for vis - average percentage of activities visited in different modules
           get_avg_percnt_visits_modules(state_modules_data_new).to_csv(state_vis_data_path + '_modulewise_activ_visit.csv', index=False)
           # To get data for vis - number of students accessing different modules
           get_num_stud_modules(state_modules_data_new).to_csv(state_vis_data_path + '_modulewise_stud.csv', index=False)

    return None
