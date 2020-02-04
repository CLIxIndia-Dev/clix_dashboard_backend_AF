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

from airflow.models import Variable
from airflow.models import TaskInstance
from airflow.models import DagBag

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
    elif state == 'ct':
        state_new = 'cg'
    else:
        state_new = state

    list_of_schools = context['ti'].xcom_pull(task_ids='sync_state_data_' + state_new, key = 'school_update_list')
    schools_to_process = partition(list_of_schools)[chunk]
    print(schools_to_process)
    if schools_to_process:
        #print('Got all schools')
        #This date range is just to process latest data logs and then append them to already processed logs data
        # for each state

        date_range = ['2018-06-01', str(datetime.utcnow().date())]
        #date_range = [Variable.get('prev_update_date_static_' + state), Variable.get('curr_update_date_static_' + state)]
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

        all_chunks = [*range(clix_config.num_school_chunks)]
        all_chunks.remove(chunk)
        try:
          dag_bag = DagBag('/usr/local/airflow/dags/clix_static_visuals_dag.py')
          target_dag = dag_bag.get_dag('clix_static_visuals_dag')
          dr = target_dag.get_dagrun(target_dag.latest_execution_date)
          ti_list = [dr.get_task_instance('process_raw_state_data_' + str(each) + '_' + state) for each in all_chunks]
        except Exception as e:
          import pdb
          pdb.set_trace()
        other_tasks_status = all([each.current_state() == 'success' for each in ti_list])
        if other_tasks_status:
            Variable.set('last_updated_date_static_' + state, datetime.utcnow().date())

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
        list_of_all_state_df_tools = [pandas.read_csv(tools_modules_server_logs_datapath + 'tool_logs_' + each + '.csv') for each in ['mz', 'ct', 'rj', 'tg']]
        state_tools_data = pandas.concat(list_of_all_state_df_tools, ignore_index=True)

        list_of_all_state_df_modules = [pandas.read_csv(tools_modules_server_logs_datapath + 'module_logs_' + each + '.csv') for each in ['mz', 'ct', 'rj', 'tg']]
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

        if not all_states_flag:
            state_vis_data_path = tools_modules_server_logs_datapath + 'vis_data/' + state + '_' + each_month
        elif all_states_flag:
            state_vis_data_path = tools_modules_server_logs_datapath + 'vis_data/' + 'all_states_' + each_month
        else:
            import pdb
            pdb.set_trace()

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
