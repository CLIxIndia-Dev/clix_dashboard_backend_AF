# This file has all the functions required to get different metrics of a schools
# using syncthing data from the school_syncthing_data_live folder
from scripts.clix_platform_data_processing.get_data import get_modules_data, get_tools_data, get_lab_usage

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



class metrics_data:

    def __init__(self, schools, state, date_range):

        self.school_list = schools
        self.state = state
        self.date_range = date_range
        self.tools_data  = get_tools_data(self.school_list, self.date_range, self.state)
        (self.modules_data, self.server_log_data) = get_modules_data(self.school_list, self.date_range, self.state)

    def get_num_stud_daily(self):

      schools = self.school_list
      state = self.state
      date_range = self.date_range
      tools_data = self.tools_data
      modules_data = self.modules_data

      col_map = {'date_created': 'date', 'num_stud_day_tools': 'attendance_tools', 'num_stud_day_modules': 'attendance_modules'}

      if not tools_data.empty:
          tools_data_temp = tools_data.groupby(['date_created', 'school_server_code'])['num_students_day'].apply(lambda x: x.unique()[0]).reset_index(level=None)
          num_stud_daily_tools = tools_data_temp.rename(columns={'num_students_day': 'num_stud_day_tools'})
      else:
          num_stud_daily_tools = pandas.DataFrame()

      #modules_data = get_modules_data(schools, date_range, state)
      if not modules_data.empty:
          module_data_temp = modules_data.groupby(['school_server_code', 'date_created',
          'school_name'])['user_id'].apply(lambda x: len(x.unique())).reset_index()
          #num_stud_daily_modules = num_stud_daily_modules.drop(['level_0'], axis = 1)
          num_stud_daily_modules = module_data_temp.rename(columns={'user_id': 'num_stud_day_modules'})
      else:
          num_stud_daily_modules = pandas.DataFrame()

      try:
        final_df = pandas.merge(num_stud_daily_tools, num_stud_daily_modules, how='outer', left_on=['date_created', 'school_server_code'],
        right_on=['date_created', 'school_server_code'])
        return final_df.rename(columns=col_map)
      
      except KeyError:
        if num_stud_daily_tools.empty:
            num_stud_daily_modules['num_stud_day_tools'] = 0
            return num_stud_daily_modules.rename(columns=col_map)
        if num_stud_daily_modules.empty:
            num_stud_daily_tools['num_stud_day_modules'] = 0
            return num_stud_daily_tools.rename(columns=col_map)
      except Exception as e:
          import pdb
          pdb.set_trace()


    def get_module_visits_daily(self):
      schools = self.school_list
      state = self.state
      date_range = self.date_range
      modules_data = self.modules_data

      def get_mod_visits(school_df):

          domain_module_map = {each: key for key, value in modules_domain_map.items() for each in value}
          school_df = school_df[school_df['module_name'] != "[u'Pre-CLIx Survey']"]
          school_df = school_df[school_df['module_name'] != "[u'Post-CLIx Survey']"]
          school_df['domain'] = school_df['module_name']
          school_df = school_df.replace({'domain': domain_module_map})

          domain_df = school_df.groupby(['user_id', 'date_created', 'domain'])['module_name'].apply(lambda x: len(x.unique())).reset_index()
          domainwise_df  = domain_df.groupby(['date_created', 'domain'])['module_name'].sum().reset_index()

          final_df = pandas.pivot_table(domainwise_df, values = 'module_name', index=['date_created'], columns=['domain'], fill_value=0).reset_index()
          final_df = final_df.rename(columns= {'e': 'e_num_modules', 'm': 'm_num_modules', 's': 's_num_modules'})

          return final_df

      if not modules_data.empty:
          num_modules_daily = modules_data.groupby(['school_server_code']).apply(lambda x: get_mod_visits(x)).reset_index(level=None)
          num_modules_daily = num_modules_daily.drop(['level_1'], axis = 1)
          num_modules_daily = num_modules_daily.rename(columns={'date_created': 'date'})
      else:
          num_modules_daily = pandas.DataFrame()

      return num_modules_daily


    def get_tool_visits_daily(self):
      schools = self.school_list
      state = self.state
      date_range = self.date_range
      tools_data = self.tools_data

      def get_tool_visits(school_df):
          domain_df = school_df.groupby(['user_id', 'date_created', 'domain'])['tool_name'].apply(lambda x: len(x.unique())).reset_index()
          domainwise_df  = domain_df.groupby(['date_created', 'domain'])['tool_name'].sum().reset_index()

          final_df = pandas.pivot_table(domainwise_df, values = 'tool_name', index=['date_created'], columns=['domain'], fill_value=0).reset_index()
          final_df = final_df.rename(columns= {'e': 'e_num_tools', 'm': 'm_num_tools', 's': 's_num_tools'})

          if 'e_num_tools' not in final_df.columns:
             final_df['e_num_tools'] = 0

          return final_df

      if not tools_data.empty:
          num_tools_daily = tools_data.groupby(['school_server_code']).apply(lambda x: get_tool_visits(x)).reset_index(level=None)
          num_tools_daily = num_tools_daily.drop(['level_1'], axis = 1)
          num_tools_daily = num_tools_daily.rename(columns={'date_created': 'date'})
      else:
          num_tools_daily = pandas.DataFrame()

      return num_tools_daily

    def get_num_idle_days(self):

      schools = self.school_list
      state = self.state
      date_range = self.date_range
      tools_data = self.tools_data
      modules_data = self.modules_data
      server_log_data = self.server_log_data

      def get_lab_usage_tools(tools_data):
        num_idle_days_dframe = tools_data.groupby(['school_server_code']).apply(lambda x: len(x['date_created'].unique())).reset_index()
        num_idle_days_dframe = num_idle_days_dframe.rename(columns={0: 'tools_only_activity'})
        num_idle_days_dframe['days_server_wo_activity'] = 0
        num_idle_days_dframe['module_only_activity'] = 0
        num_idle_days_dframe['tool_with_module_activity'] = 0
        num_idle_days_dframe['total_days_server_on'] = num_idle_days_dframe['tools_only_activity']
        return num_idle_days_dframe

      if modules_data.empty:
        num_idle_days_dframe =  pandas.DataFrame()
        if not tools_data.empty:
            num_idle_days_dframe = get_lab_usage_tools(tools_data)
        else:
            return pandas.DataFrame()
      else:
        schools_dframe_list = []
        for each_school, data in server_log_data.items():
            school_mod_df = modules_data[modules_data['school_server_code'] == each_school]
            if not tools_data.empty:
                school_tool_df = tools_data[tools_data['school_server_code'] == each_school]
            else:
                school_tool_df = pandas.DataFrame()
            schools_dframe_list.append(get_lab_usage(school_mod_df, school_tool_df, data))

        num_idle_days_dframe = pandas.concat(schools_dframe_list)
      
      cols_required = ['school_server_code', 'days_server_wo_activity', 'tools_only_activity',
        'module_only_activity', 'tool_with_module_activity']

      num_idle_days = num_idle_days_dframe.drop_duplicates(subset=cols_required)

      num_idle_days['date_created'] = date_range[1]

      cols_required = cols_required + ['date_created']
      col_map = {'days_server_wo_activity': 'days_server_idle', 'tools_only_activity': 'days_server_tools',
        'module_only_activity': 'days_server_modules', 'tool_with_module_activity': 'days_server_tools_modules',
        'date_created': 'date'}
      return num_idle_days[cols_required].rename(columns = col_map)

    def get_tools_attendance(self):

      schools = self.school_list
      state = self.state
      date_range = self.date_range
      tools_data = self.tools_data

      def get_tool_stud(school_df):

          def get_users(df):
              all_users = df['user_id'].unique()
              num_users = len(all_users)

              if '0' in all_users:
                  anon_users = len(df[df['user_id'] == '0']['session_id'].unique()) - 1
              else:
                  anon_users = 0
              return num_users + anon_users

          toolwise_users_df  = school_df.groupby(['date_created', 'tool_name']).apply(lambda x: get_users(x)).reset_index()

          toolwise_users_df = toolwise_users_df.rename(columns= {0: 'num_stud_tools'})
          toolwise_users_df['tool_name_db'] = toolwise_users_df['tool_name'].apply(lambda x: 'tool' + '_' + x)

          final_df = pandas.pivot_table(toolwise_users_df, values = 'num_stud_tools', index=['date_created'], columns=['tool_name_db'], fill_value=0).reset_index()
          return final_df

      if not tools_data.empty:
          num_tools_daily = tools_data.groupby(['school_server_code']).apply(lambda x: get_tool_stud(x)).reset_index(level=None)
          num_tools_daily = num_tools_daily.drop(['level_1'], axis = 1)
          num_tools_daily = num_tools_daily.rename(columns={'date_created': 'date'})
      else:
          num_tools_daily = pandas.DataFrame()

      return num_tools_daily

    def get_modules_attendance(self):

      schools = self.school_list
      state = self.state
      date_range = self.date_range
      modules_data = self.modules_data

      def get_module_stud(school_df):

          def get_users(df):
              all_users = df['user_id'].unique()
              num_users = len(all_users)
              return num_users

          def get_module_names(module_name):

              if module_name == "[u'Post-CLIx Survey']":
                  module_name_new = 'module_Post_CLIx_Survey'
              elif module_name == "[u'Pre-CLIx Survey']":
                  module_name_new = 'module_Pre_CLIx_Survey'
              else:
                 module_name_new = 'module_' + '_'.join(module_name.split("'")[1].split(" "))
              return module_name_new

          modulewise_users_df  = school_df.groupby(['date_created', 'module_name']).apply(lambda x: get_users(x)).reset_index()
          modulewise_users_df = modulewise_users_df.rename(columns= {0: 'num_stud_modules'})
          modulewise_users_df['module_name_db'] = modulewise_users_df['module_name'].apply(lambda x: get_module_names(x))
          final_df = pandas.pivot_table(modulewise_users_df, values = 'num_stud_modules', index=['date_created'], columns=['module_name_db'], fill_value=0).reset_index()
          return final_df

      if not modules_data.empty:
          num_modules_daily = modules_data.groupby(['school_server_code']).apply(lambda x: get_module_stud(x)).reset_index(level=None)
          num_modules_daily = num_modules_daily.drop(['level_1'], axis = 1)
          num_modules_daily = num_modules_daily.rename(columns={'date_created': 'date'})
      else:
          num_modules_daily = pandas.DataFrame()

      return num_modules_daily
