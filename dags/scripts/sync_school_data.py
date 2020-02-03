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
import json
import re

def append_school_list(school_update_info, list_of_schools_updated, state):
    re_obj = re.compile( '.*' + re.escape('syncInfo') + '*.')
    school_update_info_state = school_update_info[state]
    index = str(int(max([key.split('_')[1] for key in school_update_info_state.keys() if re_obj.match(key)])) + 1)
    school_update_info[state]["syncInfo_" + index] = {"date": str(datetime.utcnow().date()), "schools": list_of_schools_updated}
    if len(school_update_info_state["schools_synced_so_far"]) != 0:
       schools_so_far = school_update_info[state]["schools_synced_so_far"]
       schools_so_far.extend(list_of_schools_updated)
       list_of_schools_updated_latest = list(set(schools_so_far))
    else:
       list_of_schools_updated_latest = list_of_schools_updated

    school_update_info[state]["schools_synced_so_far"] = list_of_schools_updated_latest
    return json.dumps(school_update_info)

def schools_updated(rsync_log):
    log_text = rsync_log.decode('utf-8')
    pattern = re.compile(r"(\d+-\D{2}\d+)\/(gstudio)")
    schools = set([each[0] for each in pattern.findall(log_text) if each[1] == 'gstudio'])
    return list(schools)


def rsync_data_local(state, src, dst, **context):
    '''
    Function to sync state data from local hdd.
    '''
    def local_sync(src, dst):
        import pdb
        pdb.set_trace()
        cmd = "rsync -avzhP --stats {0} {1}".format(src, dst)
        #cmd = "rsync -avzhP --stats {0} {1}".format(src, dst)
        #rsync = pexpect.spawn(cmd, timeout=3600)
        try:
            rsync = pexpect.spawn(cmd, timeout=3600)
            #i = rsync.expect()
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


def rsync_data_ssh(state, src, dst, static_flag, **context):
    '''
    Function to sync state data through ssh.
    '''

    user = clix_config.remote_user
    ip = clix_config.remote_ip
    passwd = clix_config.remote_passwd

    def ssh_sync(src, dst):
        cmd = "rsync -avzhP --stats {0}@{1}:{2} {3}".format(user, ip, src, dst)
        #cmd = "rsync -avzhP --stats {0} {1}".format(src, dst)
        # TODO: Need to explicitly catch error from pexpect when there is
        # timeout or eof error. try and except is ot working.
        # For now setup a very high timeout to not get these
        # errors

        rsync = pexpect.spawn(cmd, timeout=7200)

        try:
            i = rsync.expect(["{0}@{1}'s password: ".format(user, ip),
            'continue connecting (yes/no)?',
            'Are you sure you want to'])

            if i == 0 :
                rsync.sendline(passwd)

            elif (i == 1) or (i == 2):
                rsync.sendline('yes')
                i = rsync.expect("{0}@{1}'s password: ".format(user, ip))
                rsync.sendline(passwd)
            else:
                import pdb
                pdb.set_trace()
                raise Exception('Something wrong with authentication!')

        except pexpect.TIMEOUT as e:
            pass

        except pexpect.EOF as e:
            pass

        finally:
            rsync_log = rsync.read()
            list_of_schools_updated = schools_updated(rsync_log)
            context['ti'].xcom_push(key='school_update_list', value=list_of_schools_updated)
            # Change tracking variables only if there is any school synced
            if len(list_of_schools_updated) != 0:
             if static_flag:
               school_update_info = Variable.get('clix_variables_config_static_vis', deserialize_json=True)
               Variable.set('clix_variables_config_static_vis', append_school_list(school_update_info, list_of_schools_updated, state))
             else:
               school_update_info = Variable.get('clix_variables_config_schooldb', deserialize_json=True)
               Variable.set('clix_variables_config_schooldb', append_school_list(school_update_info, list_of_schools_updated, state))

            rsync.close()
    return ssh_sync(src, dst)
