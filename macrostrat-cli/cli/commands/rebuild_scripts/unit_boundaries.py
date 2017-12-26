from ..base import Base

class UnitBoundaries(Base):
    def __init__(self, *args):
        Base.__init__(self, {}, *args)

    def run(self):
        self.mariadb['cursor'].execute("""
          UPDATE unit_boundaries ub
          JOIN intervals i ON ub.t1 = i.id
          SET ub.t1_age = age_bottom - ((age_bottom - age_top) * t1_prop)
          WHERE boundary_status != 'absolute'
        """)

        self.mariadb['cursor'].execute("""
          UPDATE unit_boundaries ub
          JOIN intervals i ON ub.t1 = i.id
          SET ub.t1_prop = (age_bottom - t1_age)/(age_bottom - age_top)
          WHERE boundary_status = 'absolute'
        """)

        self.mariadb['connection'].commit()
        self.mariadb['cursor'].close()
        self.mariadb['connection'].close()
