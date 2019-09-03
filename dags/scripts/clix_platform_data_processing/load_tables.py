from sqlalchemy import create_engine, MetaData
from config.clix_config import SQLALCHEMY_DATABASE_URI, POOL_SIZE

Engine = create_engine(SQLALCHEMY_DATABASE_URI, pool_size=POOL_SIZE, max_overflow=0)

def load_into_db(dframe, table):
    try:
        #col_map = {'date_created': 'date', 'num_stud_day_tools': 'attendance_tools', 'num_stud_day_modules': 'attendance_modules'}
        dframe['district'] = 'mz'
        dframe['state'] = 'mz'
        #dframe = dframe.rename(columns=col_map)
        dframe.to_sql(table, Engine, if_exists='append', index=False)
        return 'Done'
    except Exception as e:
        print(e)
        import pdb
        pdb.set_trace()
