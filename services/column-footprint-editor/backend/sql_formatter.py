import json

class SqlFormatter:
    '''SQL query formatter'''
    # TODO: distingush single and double quotes

    def __init__(self, project_id):
        self.project_id = project_id
      

    def sql_config_paramertize(self, sql, config):
        """ function to parameterize sql schemas based on project config"""

        for k,v in config.items():
            string = '${%s}' % k
            if string in sql:
                sql = sql.replace(string, v)

        return sql