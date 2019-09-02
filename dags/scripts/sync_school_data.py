# Collection of functions to sync 'syncthing_data' from field with
# local repository of the same.
# This is done at state level.
# Have to intitalize prev_update_date and curr_update_date in variables of UI.

#import config.clix_config as clix_config
import pexpect
import pandas
import re
import config.clix_config as clix_config
from datetime import datetime

from airflow.models import Variable

def schools_updated(rsync_log):
    log_text = rsync_log.decode('utf-8')
    pattern = re.compile(r"(\d+-\D{2}\d+)\/(gstudio)")
    schools = set([each[0] for each in pattern.findall(log_text) if each[1] == 'gstudio'])
    return list(schools)

def rsync_data_local(state, src, dst, **context):
    '''
    Function to sync state data from local hdd.
    '''

    user = clix_config.remote_user
    ip = clix_config.remote_ip
    passwd = clix_config.remote_passwd

    def local_sync(src, dst):
        cmd = "rsync -avzhP --stats {2} {3}".format(src, dst)
        #cmd = "rsync -avzhP --stats {0} {1}".format(src, dst)
        rsync = pexpect.spawn(cmd, timeout=3600)

        try:
            i = rsync.expect()
        except pexpect.EOF:
            print("EOF Exception for Syncing")
            raise Exception('Rysnc didnt work!')

        except pexpect.TIMEOUT:
            print("TIMEOUT Exception Syncing")
            raise Exception('Not enough time given to Rsync!')

        else:
          rsync_log = rsync.read()
          list_of_schools_updated = schools_updated(rsync_log)

          context['ti'].xcom_push(key='school_update_list', value=list_of_schools_updated)
          Variable.set('school_update_list', list_of_schools_updated)
          #if list_of_schools_updated:
        #     Variable.set('prev_update_date', Variable.get('curr_update_date'))
        #     Variable.set('curr_update_date', datetime.utcnow())
          rsync.close()

    return local_sync(src, dst)

def rsync_data_ssh(state, src, dst, **context):
    '''
    Function to sync state data through ssh.
    '''

    user = clix_config.remote_user
    ip = clix_config.remote_ip
    passwd = clix_config.remote_passwd

    def ssh_sync(src, dst):
        cmd = "rsync -avzhP --stats {0}@{1}:{2} {3}".format(user, ip, src, dst)
        #cmd = "rsync -avzhP --stats {0} {1}".format(src, dst)
        rsync = pexpect.spawn(cmd, timeout=3600)

        try:
            i = rsync.expect(['Password:', 'continue connecting (yes/no)?'])
            if i == 0 :
                rsync.sendline(passwd)
            elif i == 1:
                rsync.sendline('yes')
                rsync.expect('Password: ')
                rsync.sendline(passwd)
        except pexpect.EOF:
            print("EOF Exception for Syncing")
            raise Exception('Rysnc didnt work!')

        except pexpect.TIMEOUT:
            print("TIMEOUT Exception Syncing")
            raise Exception('Not enough time given to Rsync!')

        else:
          rsync_log = rsync.read()
          list_of_schools_updated = schools_updated(rsync_log)

          context['ti'].xcom_push(key='school_update_list', value=list_of_schools_updated)
          Variable.set('school_update_list', list_of_schools_updated)
          #if list_of_schools_updated:
        #     Variable.set('prev_update_date', Variable.get('curr_update_date'))
        #     Variable.set('curr_update_date', datetime.utcnow())
          rsync.close()

    return ssh_sync(src, dst)