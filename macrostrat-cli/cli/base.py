from psycopg2.extras import NamedTupleCursor

class Base(object):

    def __init__(self, connections, *args):

        if 'pg' in connections:
            setattr(self, 'pg', {'connection': None, 'cursor': None})
            self.pg['connection'] = connections['pg']()
            self.pg['cursor'] = self.pg['connection'].cursor(cursor_factory = NamedTupleCursor)

        if 'mariadb' in connections:
            setattr(self, 'mariadb', {'connection': None, 'cursor': None})
            self.mariadb['connection'] = connections['mariadb']()
            self.mariadb['cursor'] = self.mariadb['connection'].cursor()

        self.args = args

    def run(self):
        raise NotImplementedError('You must implement the run() method yourself!')
