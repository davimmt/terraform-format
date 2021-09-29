import os,sys,subprocess
from itertools import islice

def get_all_terraform_files():
    """Returns a list with path/name of the chosen files. 

    Uses the Unix 'find' package to recursivly search the
    specified files in the defined scope. 
    """
    files_cmd = subprocess.Popen("find . -type f -name '*.tf'", shell=True, stdout=subprocess.PIPE)
    return list(filter(None, files_cmd.stdout.read().decode('ascii').split('\n')))

def remove_whitespaces(string):
    """Returns a string completly stripped.

    Replaces all whitespaces between chars with only one whitespace,
    and removes all trailling whitespaces.
    """
    while '  ' in string: string = string.replace('  ', ' ')
    return string.strip()

def get_raw_lines(file_lines):
    """Returns a list of all the lines.

    Reads all the lines and uses the remove_whitespaces()
    for each string, and stores in a list.
    """
    raw_lines = []
    for line in file_lines:
        line = remove_whitespaces(line)
        if line != '': raw_lines.append(line)
    return raw_lines

def ignore_block(i, lines):
    """Returns a list of lines to ignore when HCL-formatting.

    Reads all the lines below the defined string (in the main), and
    stores all the line numbers that are inside that block in a list.
    """
    child_i = i
    lines_to_ignore = [child_i]
    bracket_count = 0
    for line in islice(lines, i, None):
        if '{' in line: bracket_count += 1
        if '}' in line: bracket_count -= 1
        if bracket_count != 0:
            child_i += 1
            lines_to_ignore.append(child_i)
        else:
            break 
    return lines_to_ignore

if __name__ == "__main__":
    files = get_all_terraform_files()
    for file in files:
        print('Working on [%s] file' % (file))
        
        print(' 1. Reading file and removing all spaces and indentation')
        raw_lines = get_raw_lines(open(file, 'r').readlines())
        
        print(' 2. Breaking lines')
        spaced_lines = []
        for i, line in enumerate(raw_lines):
            jump_line = 0

            # Avoid index errors
            if i < (len(raw_lines) - 1):
                next_line = raw_lines[i+1]
                
                # Custom (not to break)
                if not line == 'locals {' and \
                not line == 'terraform {' and \
                not line == 'required_providers {' and \
                not line.startswith('#') and \
                not next_line == 'rules = var.rule_self ? concat(var.rules, [{' and \
                not next_line == 'backend "s3" {' and \
                not next_line == 'required_providers {' and \
                not next_line == 'awsutils = {' and \
                not next_line == 'listener_tags = merge(var.tags, {' and \
                len(next_line) > 1:

                    # Custom (to break)
                    if next_line.count('{') > next_line.count('}') and not '=> {' in next_line: jump_line = 1
                    if next_line.count('[') > next_line.count(']') and not ': [' in next_line: jump_line = 1
                    if next_line.startswith('#'): jump_line = 1
                    if line.startswith('}') and not next_line.startswith('}'): jump_line = 1
                    if line.startswith(']') and not next_line.startswith(']'): jump_line = 1

                    if jump_line: spaced_lines.append(line + '\n')
                    else: spaced_lines.append(line)

                else: spaced_lines.append(line)
            else: spaced_lines.append(line)

        print(' 3. Re-indenting lines')
        indented_lines = []
        indentation = 0
        for i, line in enumerate(spaced_lines):
            # Indent down current line
            if ('{' in line and '}' in line) or \
               (']' in line and '[' in line):
                if (line.count('{') < line.count('}')) or \
                   (line.count('[') < line.count(']')):
                    indentation -= 1
            if ('}' in line and not '{' in line) or \
               (']' in line and not '[' in line):
                indentation -= 1

            # Storing indented and current line
            tabbing = '  ' * indentation
            indented_line = tabbing + line
            indented_lines.append(indented_line)

            # Indent up next line
            if ('{' in line and '}' in line) or \
               (']' in line and '[' in line):
                if (line.count('{') > line.count('}')) or \
                   (line.count('[') > line.count(']')):
                    indentation += 1
            elif ('{' in line and not '}' in line) or \
                 ('[' in line and not ']' in line):
                indentation += 1

        print(' 4. Tagging lines not to format with HCL right padding')
        lines_to_ignore = []
        for i, line in enumerate(indented_lines):
            # Break lines
            if not line.strip(): lines_to_ignore.append(i)
            # Comentaries
            if line.startswith('#'): lines_to_ignore.append(i)
            # Lines with no equal sign
            elif not ' = ' in line: lines_to_ignore.append(i)
            # Lines that begin new blocks
            elif (line.count('{') > line.count('}')) or \
                 (line.count('[') > line.count(']')):
                lines_to_ignore.append(i)

            # Custom lines
            elif line == 'variable "region" { default = "us-east-1" }': lines_to_ignore.append(i)
            elif line == 'provider "aws" { region = var.region }': lines_to_ignore.append(i)
            elif line == 'locals { caller = data.aws_caller_identity.current.arn }': lines_to_ignore.append(i)

            # Data block
            #if line.startswith('data "') and '{' in line: lines_to_ignore += ignore_block(i, indented_lines)
            # Locals block
            #if line.startswith('locals {'): lines_to_ignore += ignore_block(i, indented_lines)
        
        lines_to_ignore.sort()

        print(' 5. Grouping blocks of lines')
        lines_group = []
        group = 0
        for i, line in enumerate(indented_lines):
            if i in lines_to_ignore:
                lines_group.append(-1)
                group += 1
            else:
                lines_group.append(group)

        blocks_group = {}
        helper = 0 
        for i, line in enumerate(indented_lines): 
            # Not ignored lines
            if lines_group[i] != -1:
                line_len = len(line.split('=', 1)[0].strip())
                if not lines_group[i] in blocks_group: 
                    blocks_group[lines_group[i]] = line_len
                    helper = line_len
                else:
                    if blocks_group[lines_group[i]] != helper: 
                        blocks_group[lines_group[i]] = line_len
                        helper = line_len
                    elif line_len > blocks_group[lines_group[i]]:
                        blocks_group[lines_group[i]] = line_len
                        helper = line_len

        print(' 6. Trucating and rewriting file HCL-style')
        with open(file, 'w') as formated_file:
            formated_file.truncate()
            for i, line in enumerate(indented_lines):
                if not i in lines_to_ignore:
                    key_value = line.split('=', 1)
                    key = key_value[0].rstrip()
                    key_value.pop(0)
                    value = ''.join(str(item) for item in key_value)
                    
                    # HCL-like before '=' padding
                    indentation = len(key) - len(key.lstrip())
                    padding = blocks_group[lines_group[i]]
                    key = key.ljust((indentation + padding), ' ')

                    formated_file.write('%s =%s\n' % (key, value))
                else:
                    formated_file.write(line + '\n')
        
        print('Completed!\n')
