def change_set_clean(change_set):
    '''
    This function cleans the change_set passed from frontend
    Right now it only 
    '''
    for line in change_set:
        id_objects = [] # list of objects {id: "internal id", occurences: [indexes]}
        if line['action'] == "draw.create":
            obj = {"id": "", "occurences": []}
            draw_id = line['feature']['id']
            obj['id'] = draw_id
            for index, l in enumerate(change_set):
                if 'id' in l['feature'] and draw_id == l['feature']['id']:
                    obj['occurences'].append(index) # add the indexes to occurneces
            id_objects.append(obj)
        
        for obj in id_objects:
            if len(obj['occurences']) > 1:
                first_index = obj['occurences'][0]
                final_index = obj['occurences'][-1]
                
                first_line = change_set[first_index]
                last_line = change_set[final_index]

                print(first_line)
                print(last_line)
                
                if last_line['action'] == "draw.delete":
                    # remove all the lines
                    print('delete')
                    for i in sorted(obj['occurences'], reverse=True):
                        del change_set[i] ## remove all lines by indexes in occurences
                        ## have to do it in reverse order to not throw off earlier indexes
                else:
                    geom = last_line['feature']['geometry']
                    first_line['feature']['geometry'] = geom
                    for i in sorted(obj['occurences'][1:], reverse=True):
                        # remove all occurences except for the first, which we changed to have 
                        ## the coordinates of the last one.
                        del change_set[i] 
        
    return change_set