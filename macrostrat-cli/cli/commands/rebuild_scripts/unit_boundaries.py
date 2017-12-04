class UnitBoundaries:
    meta = {
        'mariadb': True,
        'pg': False
    }
    @staticmethod
    def build(mariaConnection):
        connection = mariaConnection()
        cursor = connection.cursor()

        cursor.execute("""
          UPDATE unit_boundaries ub
          JOIN intervals i ON ub.t1 = i.id
          SET ub.t1_age = age_bottom - ((age_bottom - age_top) * t1_prop)
          WHERE boundary_status != 'absolute'
        """)

        cursor.execute("""
          UPDATE unit_boundaries ub
          JOIN intervals i ON ub.t1 = i.id
          SET ub.t1_prop = (age_bottom - t1_age)/(age_bottom - age_top)
          WHERE boundary_status = 'absolute'
        """)

        connection.commit()
        cursor.close()
        connection.close()
