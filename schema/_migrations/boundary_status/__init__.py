from macrostrat.core.migrations import Migration, _any, _not, custom_type_exists


class BoundaryStatusMigration(Migration):
    name = "boundary-status"
    description = """
    Relocate custom types for Macrostrat schema
    """
    readiness_state = "ga"

    postconditions = [
        custom_type_exists("macrostrat", "boundary_status"),
        custom_type_exists("macrostrat", "boundary_type"),
        _not(custom_type_exists("public", "boundary_status")),
        _not(custom_type_exists("public", "boundary_type")),
    ]

    preconditions = [
        _any(
            custom_type_exists(s, "macrostrat")
            for s in [
                "interval_boundaries_boundary_status",
                "interval_boundaries_scratch_boundary_status",
                "unit_boundaries_backup_boundary_status",
                "unit_boundaries_backup_boundary_type",
                "unit_boundaries_boundary_status",
                "unit_boundaries_boundary_type",
                "unit_boundaries_scratch_boundary_status",
                "unit_boundaries_scratch_boundary_type",
                "unit_boundaries_scratch_old_boundary_status",
                "unit_boundaries_scratch_old_boundary_type",
            ]
        )
    ]
