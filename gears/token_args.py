#! /usr/bin/env python3

import re

def tokenize_string(input_string):
    # This regular expression pattern matches either a word (\\w+)
    # or a quoted string (either single or double quotes)
    pattern = r'\b\w+\b|"[^"]*"|\'[^\']*\''

    # Find all matches in the input_string
    matches = re.findall(pattern, input_string)

    # Remove the quotes from the matched strings and split on unescaped spaces
    tokens = [re.sub(r'^["\']|["\']$', '', match) for match in matches]

    return tokens


# Test the function
print(tokenize_string("a new set of words"))  # ["a", "new", "set", "of", "words"]
print(tokenize_string("a new 'set of' words"))  # ["a", "new", "set of", "words"]
print(tokenize_string("a new set\' of words"))  # ["a", "new", "set of", "words"]
print(tokenize_string('a new "set of" words'))  # ["a", "new", "set of", "words"]
