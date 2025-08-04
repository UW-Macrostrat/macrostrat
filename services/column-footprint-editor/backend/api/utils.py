def clean_change_set(change_set):
    """
    We can sort the changeset by lmbda x: x['feature']['id'],
    ensuring all feature actions will be next to eachother.

    if draw.create:
        change_coords => swap geometries
        draw.delete => pop current
    if change_coords:
        change_coords | draw.delete => pop current item and append.

    similar to this leetcode problem and solution:
    https://leetcode.com/problems/merge-intervals/solution/
    """
    if not len(change_set):
        return []

    # sort by feature id
    change_set.sort(key=lambda x: x["feature"]["id"])

    final_changes = [change_set[0]]
    for i in range(1, len(change_set)):
        last_action = final_changes[-1]
        current_action = change_set[i]

        if last_action["feature"]["id"] != current_action["feature"]["id"]:
            final_changes.append(current_action)
            continue

        if last_action["action"] == "draw.create":
            if current_action["action"] == "change_coordinates":
                last_action["feature"]["geometry"] = current_action["feature"][
                    "geometry"
                ]
            else:  # draw.delete
                final_changes.pop()

        elif last_action["action"] == "change_coordinates":
            final_changes[-1] = current_action

    return final_changes
