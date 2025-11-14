test_input = [
    {
        "id": "col:97619",
        "lng": -117.445,
        "lat": 47.650002,
        "max_interval": "Langhian",
        "formation": "Latah",
    },
    {
        "id": "col:106382",
        "lng": -105.283333,
        "lat": 38.916668,
        "max_interval": "Chadronian",
        "formation": "Florissant",
    },
    {"id": "col:113350", "lng": 103.627197, "lat": 50.350101, "max_interval": "Aptian"},
    {
        "id": "col:113371",
        "lng": 119.238609,
        "lat": 41.316387,
        "max_interval": "Callovian",
        "min_interval": "Oxfordian",
        "formation": "Daohugou",
    },
    {
        "id": "col:124194",
        "lng": 19.940001,
        "lat": 54.869999,
        "max_interval": "Priabonian",
    },
    {
        "id": "col:125656",
        "lng": 118.921997,
        "lat": 41.536999,
        "max_interval": "Late Barremian",
        "formation": "Yixian",
        "group": "Jehol",
    },
    {
        "id": "col:128550",
        "lng": 118.714996,
        "lat": 36.549999,
        "max_interval": "Burdigalian",
        "formation": "Shanwang",
    },
    {
        "id": "col:168272",
        "lng": -0.0626,
        "lat": 51.555801,
        "max_interval": "Middle Pleistocene",
        "formation": "Highbury Silts and Sands",
    },
]

test_response = {
    "success": {
        "v": 2,
        "license": "CC-BY 4.0",
        "data": [
            {"id": "col:97619", "column_id": "xxxxx", "unit_id": "yyyyy"},
            {
                "id": "col:106382",
                "column_id": "zzzzz",
                "unit_id": "aaaaa",
                "weight": 80.5,
            },
            {
                "id": "col:106382",
                "column_id": "bbbbb",
                "unit_id": "ccccc",
                "weight": 19.5,
            },
            {"id": "col:133350", "column_id": "ddddd", "unit_id": "eeeee"},
            {"id": "col:113371"},
            {"id": "col:124194", "column_id": "fffff", "unit_id": "ggggg"},
            {"id": "col:125656"},
            {"id": "col:128550"},
            {"id": "col:168272"},
        ],
    }
}
