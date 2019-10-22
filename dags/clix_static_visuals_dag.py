# This DAG is for running python scripts to generate static visualisation data
# from syncthing every month end

import airflow
from airflow import DAG

from airflow.operators.bash_operator import BashOperator
from airflow.operators.python_operator import PythonOperator
from airflow.operators.dummy_operator import DummyOperator

from datetime import date, timedelta, datetime

import scripts.sync_school_data as sync_school_data
import scripts.process_raw_school_data as process_raw_school_data
import config.clix_config as clix_config

tools_modules_server_logs_datapath = clix_config.local_dst_state_data_logs
# --------------------------------------------------------------------------------
# set default arguments
# --------------------------------------------------------------------------------

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': airflow.utils.dates.days_ago(1),
    #'email': ['airflow@example.com'],
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
    'provide_context': True,
    # 'queue': 'bash_queue',
    # 'pool': 'backfill',
    # 'priority_weight': 10,
    # 'end_date': datetime(2016, 1, 1),
}

dag = DAG(
    'clix_static_visuals_dag', default_args=default_args,
    schedule_interval= '@monthly')

# --------------------------------------------------------------------------------
# Each state is synced independently. We have four states and syncthing data folders
# corresponding to those states are synced through sync_school_data
# --------------------------------------------------------------------------------
#sshHook = SSHHook(conn_id=<YOUR CONNECTION ID FROM THE UI>)

#dummy_operator = DummyOperator(task_id='dummy_task', retries=3, dag=dag)
list_of_state_vis = []
for each_state in clix_config.static_visuals_states:

    src = clix_config.remote_src_static_vis + each_state
    dst = clix_config.local_dst_static_vis + each_state
    list_of_tasks_chunks = []
    #sync_state_data = SSHExecuteOperator( task_id="task1",
    #bash_command= rsync -avzhe ssh {0}@{1}:{2} {3}".format(user, ip, src, dst),
    #ssh_hook=sshHook,
    #dag=dag)

    sync_state_data = PythonOperator(
        task_id='sync_state_data_' + each_state,
        python_callable=sync_school_data.rsync_data_ssh,
        op_kwargs={'state': each_state, 'src': src, 'dst': dst, 'static_flag': True},
        dag=dag)

    # For parallel processing of files in the list of schools updated
    # we use three parallel tasks each taking the portion of the list
    # of files. This is done instead of generating tasks dynamically.
    # number of schools chunks is set to clix_config.num_school_chunks
    # refer: https://stackoverflow.com/questions/55672724/airflow-creating-dynamic-tasks-from-xcom

    for each in list(range(clix_config.num_school_chunks)):
        if each_state == 'ts':
            each_state_new = 'tg'
        elif each_state == 'cg':
            each_state_new = 'ct'
        else:
            each_state_new = each_state

        process_state_raw_data = PythonOperator(
        task_id='process_raw_state_data_' + str(each) + '_' + each_state_new,
        python_callable=process_raw_school_data.process_school_data,
        op_kwargs={'state': each_state_new, 'chunk': each},
        dag=dag)

        list_of_tasks_chunks.append(process_state_raw_data)
        sync_state_data.set_downstream(process_state_raw_data)

    combine_state_chunks = PythonOperator(
        task_id='combine_chunks_' + each_state_new,
        python_callable=process_raw_school_data.combine_chunks,
        op_kwargs={'state': each_state_new},
        dag=dag)

    list_of_tasks_chunks >> combine_state_chunks

    get_state_static_vis_data = PythonOperator(
        task_id = 'get_static_vis_' + each_state_new,
        python_callable = process_raw_school_data.get_state_static_vis_data,
        op_kwargs = {'state': each_state_new, 'all_states_flag': False},
        dag=dag)

    list_of_state_vis.append(get_state_static_vis_data)
    combine_state_chunks >> get_state_static_vis_data

get_static_vis_data_all = PythonOperator(
        task_id = 'get_static_vis_data_allstates',
        python_callable = process_raw_school_data.get_state_static_vis_data,
        op_kwargs = {'state': None, 'all_states_flag': True},
        dag=dag)

list_of_state_vis >> get_static_vis_data_all
