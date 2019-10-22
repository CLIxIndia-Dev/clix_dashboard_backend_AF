#Source and destination folders for rsync of syncthing data from prop_schools
remote_src = 'CLIxDashboard/LiveSyncthingData/data/'
#remote_src = 'syncthing_Aug2019/data/'
#local_src = '/home/parthae/Documents/Projects/TISS_Git/projects/CLIxData/syncthing_Aug2019/data/'
local_dst = '/usr/local/airflow/school_syncthing_data_live/'

remote_user = 'parthae'
remote_ip = '103.36.84.138'
remote_passwd = 'uvceece2015'
states = ['mz', 'cg', 'ts', 'rj']
num_school_chunks = 4

DB_TYPE = 'postgresql'
DB_DRIVER = 'psycopg2'
DB_USER = 'admin_clixdata'
DB_PASS = 'clixdata'
DB_HOST = '172.17.0.1'
DB_PORT = '5433'
DB_NAME = 'clix_dashboard_db'
POOL_SIZE = 50
SQLALCHEMY_DATABASE_URI = '%s+%s://%s:%s@%s:%s/%s' % (DB_TYPE, DB_DRIVER, DB_USER,
                                                  DB_PASS, DB_HOST, DB_PORT, DB_NAME)
