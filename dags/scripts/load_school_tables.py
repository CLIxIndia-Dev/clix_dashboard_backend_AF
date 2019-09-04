# Collection of functions to process and laod tables for visualisation
# for a set of schools whose data has been updated through syncthing_data
from math import ceil

from scripts.clix_platform_data_processing.get_metrics import metrics_data
from scripts.clix_platform_data_processing.load_tables import load_into_db

#import scripts.clix_platform_data_processing.get_metrics.get_modulevisits
#import scripts.clix_platform_data_processing.get_metrics.get_timespent
import config.clix_config as clix_config
import time
from datetime import datetime

from airflow.models import Variable

def load_to_db(metric_data):
    pass

def partition(lst, n=clix_config.num_school_chunks):
    if (len(lst) < n):
        return [lst, [], [], []]
    else:
        division = len(lst) / n
        return [lst[round(division * i):round(division * (i + 1))] for i in range(n)]

def process_school_tables(state, chunk, **context):
    '''
    Function to process tables for a set of schools whose
    data has been updated through syncthing
    '''
    list_of_schools = context['ti'].xcom_pull(task_ids='sync_state_data_' + state, key = 'school_update_list')
    #list_of_schools = Variable.get('school_update_list')
    #list_of_schools = ['2031030-mz30']

    schools_to_process = partition(list_of_schools)[chunk]
    if schools_to_process:
        #print('Got all schools')
        date_range = [Variable.get('prev_update_date'), Variable.get('curr_update_date')]
        schools_data = metrics_data(schools=schools_to_process, state=state, date_range=date_range)

        metric1_attendance = schools_data.get_num_stud_daily()
        load_into_db(metric1_attendance, 'metric1')

        metric2_module_engagement = schools_data.get_module_visits_daily()
        load_into_db(metric2_module_engagement, 'metric2')

        metric3_tool_engagement = schools_data.get_tool_visits_daily()
        load_into_db(metric3_tool_engagement, 'metric3')

        metric4_num_idle_days = schools_data.get_num_idle_days()
        load_into_db(metric4_num_idle_days, 'metric4')

        if chunk >= clix_config.num_school_chunks - 1:
            Variable.set('prev_update_date', Variable.get('curr_update_date'))
            Variable.set('curr_update_date', datetime.utcnow().date())
        #metric2_modulevisits = get_modulevisits(schools_to_process, state, date_range)
        #status2 = load_into_db(metric2_modulevisits)

        #metric3_timespent = get_timespent(schools_to_process, state, date_range)
        #status3= load_into_db(metric3_timespent)

        #modules_data = get_modules_data(schools_to_process)
        # To get school attendance data. Time variation of number of unique logins
        # from modules and tools data
        #attendance_table = get_attendance_schools(schools_to_process, tools_data, modules_data)
        # To get number of modules visited broken down by subject/domain over time.
        #module_visits_table = get_modulevisits_schools(schools_to_process, modules_data)
        # To get time spent on different tools in school over time.
        #timespent_tools_table = get_timespent_schools(schools_to_process, tools_data)
        #time.sleep(10)

    else:
        print('No schools to process for this task')

    return None
