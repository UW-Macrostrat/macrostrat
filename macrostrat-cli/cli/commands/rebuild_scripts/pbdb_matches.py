from ..base import Base

class PBDBMatches(Base):
    def __init__(self, *args):
        Base.__init__(self, {}, *args)

    def run(self):
        ## update pbdb_matches with latest pbdb data
        self.mariadb['cursor'].execute("""
            UPDATE pbdb_matches, pbdb.collections
            SET pbdb_matches.collection_name = pbdb.collections.collection_name
            WHERE pbdb_matches.collection_no = pbdb.collections.collection_no
        """)
        self.mariadb['cursor'].execute("""
            UPDATE pbdb_matches, pbdb.coll_matrix
            SET occs = n_occs
            WHERE pbdb_matches.collection_no = coll_matrix.collection_no
        """)
        self.mariadb['cursor'].execute("""
            UPDATE pbdb_matches, pbdb.collections
            SET pbdb_matches.release_date = collections.release_date
            WHERE pbdb_matches.collection_no = collections.collection_no
        """)
        self.mariadb['connection'].commit()
        self.mariadb['cursor'].close()
        self.mariadb['connection'].close()
