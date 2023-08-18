#!/usr/bin/env python3

import glob
from itertools import islice
import re

DEBUG = True
DEBUG_LEVEL = 0

if __name__ == "__main__":
    files = glob.glob('.' + '/**/*.tf', recursive=True)
    for file in files:
        if DEBUG_LEVEL > 0: print('Working on [%s] file' % (file))
        
        if DEBUG_LEVEL > 1:
            step = 1
            print(' %i. Reading file and removing all spaces and indentation' % (step))
        file_lines = open(file, 'r').readlines()
        raw_lines = {}
        line_number = 0
        for i, line in enumerate(file_lines):
            """Returns a string completly stripped.

            Replaces all whitespaces between chars with only one whitespace,
            and removes all trailling whitespaces.
            """
            while '  ' in line: line = line.replace('  ', ' ')
            line = line.strip()
            
            # If current line is a new line character only (empty line)
            # and is the first line, ignore
            if line == '' and i == 0:
                continue

            # If current line is a new line character only (empty line)
            # and previoues line was the same, ignore current line
            if line == '':
                if file_lines[i-1] in ('\n', '\r\n'):
                    continue

            # If current line is a new line character only (empty line)
            # and next line is the same, ignore current line
            if line == '' and i < (len(file_lines) - 1):
                if file_lines[i+1] in ('\n', '\r\n'):
                    continue

            raw_lines[line_number] = {}
            raw_lines[line_number]["content"] = line
            raw_lines[line_number]["left_padding_group"] = 0
            raw_lines[line_number]["right_padding_group"] = 0
            line_number += 1

        if DEBUG_LEVEL > 2: print(raw_lines)
        
        if DEBUG_LEVEL > 1:
            step += 1
            print(' %i. Configure padding groups' % (step))
        current_left_padding_group = 0
        current_right_padding_group = 1
        # can be 'increase' or 'same'
        next_left_padding_group = 'same'
        next_right_padding_group = 'same'
        for i in raw_lines:
            line = raw_lines[i]["content"]
            
            # logic
            if next_left_padding_group == 'increase':
                current_left_padding_group += 1
            if next_right_padding_group == 'increase':
                current_right_padding_group += 1

            if line.count('}') > line.count('{') or line.count(']') > line.count('['):
                current_left_padding_group -= 1
                next_right_padding_group = 'increase'
            elif line.count('{') > line.count('}') or line.count('[') > line.count(']'):
                next_left_padding_group = 'increase'
                next_right_padding_group = 'increase'
            else:
                next_left_padding_group = 'same'
                next_right_padding_group = 'same'

            # defing padding groups
            if line == '':
                raw_lines[i]["left_padding_group"] = 0
            else:
                raw_lines[i]["left_padding_group"] = current_left_padding_group

            # do not HCL padd comments, lines without '=' sign and one liners (except for for_each):
            if not line.strip().startswith('for_each') and \
              (line.startswith('#') or not ' = ' in line or re.search("^([^$]*){([^}]*)}$", line)):
                raw_lines[i]["right_padding_group"] = 0
            else:
                raw_lines[i]["right_padding_group"] = current_right_padding_group

        if DEBUG_LEVEL > 2:
            for i in raw_lines:
                print(
                    raw_lines[i]["left_padding_group"],
                    raw_lines[i]["right_padding_group"],
                    ('  ' * raw_lines[i]["left_padding_group"] + raw_lines[i]["content"])
                )

        if DEBUG_LEVEL > 1:
            step += 1
            print(' %i. Configure right HCL padding value after \'=\' sign' % (step))
        blocks_group = {}
        bigger_argument_len = 0
        previous_right_padding_group = 0
        right_padding_per_group = {}
        for i in raw_lines:
            line = raw_lines[i]["content"]
            right_padding_group = raw_lines[i]["right_padding_group"]

            if right_padding_group == 0:
                right_padding_per_group[right_padding_group] = 0
                continue

            if right_padding_group != previous_right_padding_group:
                bigger_argument_len = 0

            argument_len = len(line.split('=', 1)[0].strip())
            if argument_len > bigger_argument_len:
                bigger_argument_len = argument_len + 1

            right_padding_per_group[right_padding_group] = bigger_argument_len
            previous_right_padding_group = right_padding_group

        if DEBUG_LEVEL > 2:
            for i in raw_lines:
                print(
                    raw_lines[i]["right_padding_group"],
                    right_padding_per_group[raw_lines[i]["right_padding_group"]],
                    ('  ' * raw_lines[i]["left_padding_group"] + raw_lines[i]["content"])
                )

        if DEBUG_LEVEL > 1:
            step += 1
            print(' %i. Making custom fixes' % (step))
        for i in raw_lines:
            line = raw_lines[i]["content"]
            left_padding_group = raw_lines[i]["left_padding_group"]

            # If condition is true, means the line is inside a block
            if left_padding_group > 1:
                # Adding new line before block definition
                prev_line_left_padding_group = raw_lines[i-1]["left_padding_group"]
                if left_padding_group > prev_line_left_padding_group:
                    prev_line = raw_lines[i-1]["content"]
                    prev_prev_line = raw_lines[i-2]["content"]
                    if not prev_prev_line.strip() in ('}', ''):
                        raw_lines[i-2]["content"] = prev_prev_line + "\n"

                # Adding after link after block definition
                next_line_left_padding_group = raw_lines[i+1]["left_padding_group"]
                if left_padding_group > next_line_left_padding_group:
                    next_line = raw_lines[i+1]["content"]
                    next_next_line = raw_lines[i+2]["content"]
                    if not next_next_line.strip() in ('}', ''):
                        raw_lines[i+1]["content"] = next_line + "\n"
            
            # rewrite one liners
            # such as 'provider "aws" { region = "us-east-1" }'
            one_liner_re = re.search("^([^$]*){([^}]*)}$", line)
            if one_liner_re:
                raw_lines[i]["content"] = one_liner_re.group(1).strip() + " { " + one_liner_re.group(2).strip() + " }"

        if DEBUG_LEVEL > 2:
            for i in raw_lines:
                print(
                    ('  ' * raw_lines[i]["left_padding_group"] + raw_lines[i]["content"])
                )

        if DEBUG_LEVEL > 1:
            step += 1
            print(' %i. Trucating and rewriting file HCL-style' % (step))
        if DEBUG: file = file + ".debug"
        with open(file, 'w') as formated_file:
            formated_file.truncate()
            for i in raw_lines:
                line = raw_lines[i]["content"]
                left_padding = '  ' * raw_lines[i]["left_padding_group"]
                right_padding_group = raw_lines[i]["right_padding_group"]
                right_padding = right_padding_per_group[raw_lines[i]["right_padding_group"]]

                if right_padding_group != 0:
                    argument_and_value = line.split('=', 1)
                    argument = argument_and_value[0].strip()
                    argument_and_value.pop(0)
                    value = ''.join(str(item) for item in argument_and_value).lstrip()
                    argument = argument.ljust(right_padding, ' ')
                    formated_file.write("%s%s= %s\n" % (left_padding, argument, value))
                else:
                    formated_file.write("%s%s\n" % (left_padding, line))

        if DEBUG_LEVEL > 0: print('Completed!')
