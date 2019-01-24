from collections import defaultdict

weather_conditions = defaultdict(lambda: None, {
    1: ('Sunny/Clear', 'Grass', 'Ground', 'Fire'),
    2: ('Rain', 'Water', 'Electric', 'Bug'),
    3: ('Partly Cloudy', 'Normal', 'Rock'),
    4: ('Cloudy', 'Fairy', 'Fighting', 'Poison'),
    5: ('Windy', 'Dragon', 'Flying', 'Psychic'),
    6: ('Snow', 'Ice', 'Steel'),
    7: ('Foggy', 'Dark', 'Ghost')
})
