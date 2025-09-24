from typer import Typer

from macrostrat.core.database import get_database

app = Typer(
    name="gbdb",
    no_args_is_help=True,
    short_help="Geologic map database integration",
)


# function stackUnitsByAge(units: UnitLong[]): UnitLong[] {
#                                                         /** Find groups of units with same top and bottom age, and stack them */
# const used = new Set<number>();
# const newUnits: UnitLong[] = [];
# for (let i = 0; i < units.length; i++) {
# if (used.has(i)) continue;
# const u1 = units[i];
# const group = [u1];
# used.add(i);
# for (let j = i + 1; j < units.length; j++) {
# if (used.has(j)) continue;
# const u2 = units[j];
# if (u1.t_age === u2.t_age && u1.b_age === u2.b_age) {
# group.push(u2);
# used.add(j);
# }
# }
# if (group.length === 1) {
# newUnits.push(u1);
# } else {
# // Stack the units in the group
# let u0 = group[0];
# const totalThickness = u0.b_age - u0.t_age;
# const fracThickness = totalThickness / group.length;
# let cumulativeThickness = 0;
# // Sort group by height
# group.sort((a, b) => (b.t_pos ?? 0) - (a.t_pos ?? 0));
#
# for (const u of group) {
#     const newTAge = u.t_age + cumulativeThickness;
# const newBAge = newTAge + fracThickness;
# cumulativeThickness += fracThickness;
# newUnits.push({
# ...u,
# t_age: newTAge,
# b_age: newBAge,
# });
# }
# }
# }
# return newUnits;
# }


def update_age_model():
    """
    Stack units by age
    """
    db = get_database()

    res = db.run_query("SELECT count(*) FROM macrostrat_gbdb.strata").scalar()
    print(res)
