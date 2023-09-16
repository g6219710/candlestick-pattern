from fuzzywuzzy import fuzz
from fuzzywuzzy import process

x = fuzz.ratio("123322", "34123")
print(x)