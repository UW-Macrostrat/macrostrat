class PBDBMatches:
    meta = {
        'mariadb': True,
        'pg': False
    }
    @staticmethod
    def build(mariaConnection):
        connection = mariaConnection()
        cursor = connection.cursor()

        ## update pbdb_matches with latest pbdb data
        cursor.execute("""
            UPDATE pbdb_matches, pbdb.collections
            SET pbdb_matches.collection_name = pbdb.collections.collection_name
            WHERE pbdb_matches.collection_no = pbdb.collections.collection_no
        """)
        cursor.execute("""
            UPDATE pbdb_matches, pbdb.coll_matrix
            SET occs = n_occs
            WHERE pbdb_matches.collection_no = coll_matrix.collection_no
        """)
        cursor.execute("""
            UPDATE pbdb_matches, pbdb.collections
            SET pbdb_matches.release_date = collections.release_date
            WHERE pbdb_matches.collection_no = collections.collection_no
        """)
        connection.commit()
        cursor.close()
        connection.close()
