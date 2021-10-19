#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    Copyright (C) 2021 TeamKodi

    This file is part of sync_addon_metadata_translations

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.

    With this tool you can sync a Kodi add-on's metadata (Summary, Description, Disclaimer, and Lifecyclestates)
    translations between the addon.xml and related po files.

    Regular expressions are used instead of an xml parser to avoid changing the formatting of the
    xml, and addon.xml.in's are not valid xml files until built

    usage: sync-addon-metadata-translations [-h] [-ptx] [-xtp] [-path [PATH]] [-multi] [-v]

    optional arguments:
      -h, --help                    show this help message and exit
      -ptx, --po-to-xml             sync po file values to the addon.xml file
      -xtp, --xml-to-po             sync addon.xml values to all po files
      -path [PATH], --path [PATH]   working directory
      -multi, --multiple-addons     multiple add-ons in the working directory
      -v, --version                 prints the version of sync-addon-metadata-translations
"""

import argparse
import copy
import fnmatch
import os
import re
import sys

from . import __version__

CTXT_DESCRIPTION = 'Addon Description'
CTXT_DISCLAIMER = 'Addon Disclaimer'
CTXT_SUMMARY = 'Addon Summary'
CTXT_LIFECYCLESTATE = 'Addon Lifecyclestate'

RE_DESCRIPTION = re.compile(r'^(?P<whitespace>\s*?)<description lang=["\']'
                            r'(?P<language_code>[^"\']+?)["\']>'
                            r'(?P<body>[^<]+?)</description>\s*?$',
                            re.MULTILINE)

RE_DISCLAIMER = re.compile(r'^(?P<whitespace>\s*?)<disclaimer lang=["\']'
                           r'(?P<language_code>[^"\']+?)["\']>'
                           r'(?P<body>[^<]+?)</disclaimer>\s*?$',
                           re.MULTILINE)

RE_SUMMARY = re.compile(r'^(?P<whitespace>\s*?)<summary lang=["\']'
                        r'(?P<language_code>[^"\']+?)["\']>'
                        r'(?P<body>[^<]+?)</summary>\s*?$',
                        re.MULTILINE)

RE_LIFECYCLESTATE = re.compile(r'^(?P<whitespace>\s*?)'
                               r'<lifecyclestate.+?lang=["\'](?P<language_code>[^"\']+?)["\'][^>]*>'
                               r'(?P<body>[^<]+?)</lifecyclestate>\s*?$',
                               re.MULTILINE)

RE_LIFECYCLESTATE_TYPE = re.compile(r'^(?P<whitespace>\s*?)'
                                    r'<lifecyclestate.+?type=["\'](?P<type>[^"\']+?)["\'][^>]*>'
                                    r'(?P<body>[^<]+?)</lifecyclestate>\s*?$',
                                    re.MULTILINE)

RE_METADATA_WHITESPACE = re.compile(r'^(?P<whitespace>\s*?)<'
                                    r'(?:news|assets|platform|license|'
                                    r'source|forum|reuselanguageinvoker)'
                                    r'>[^<]*?'
                                    r'(?:</(?:news|assets|platform|license|'
                                    r'source|forum|reuselanguageinvoker)>)?'
                                    r'\s*?$',
                                    re.MULTILINE)

XMLTPL_DESCRIPTION = '{whitespace}<description lang="{language_code}">{body}</description>\n'
XMLTPL_DISCLAIMER = '{whitespace}<disclaimer lang="{language_code}">{body}</disclaimer>\n'
XMLTPL_SUMMARY = '{whitespace}<summary lang="{language_code}">{body}</summary>\n'
XMLTPL_LIFECYCLESTATE = '{whitespace}<lifecyclestate type="{type}" lang="{language_code}">' \
                        '{body}</lifecyclestate>\n'

POTPL_MSGCTXT = 'msgctxt "{string}"\n'
POTPL_MSGID = 'msgid "{string}"\n'
POTPL_MSGSTR = 'msgstr "{string}"\n'


def directory_type(string):
    """
    Check if string is a directory, raise NotADirectoryError if not a directory
    Used by argparse to validate path argument
    :param string: string to check if it's a directory
    :type string: str
    :return: provided string
    :rtype: str
    """
    if os.path.isdir(string):
        return string

    raise NotADirectoryError(string)


def get_po_metadata(po_index, ctxt):
    """
    Get the metadata (translated strings) matching `ctxt` from the po files
    :param po_index: index of po files from generate_po_index()
    :type po_index: list[dict]
    :param ctxt: ctxt to match for retrieval CTXT_DESCRIPTION, CTXT_DISCLAIMER, CTXT_LIFECYCLESTATE or CTXT_SUMMARY constants
    :type ctxt: str
    :return: all translations of `ctxt` from po files, [(<language_code>, <translated string>), ...]
    :rtype: list[tuple]
    """
    payload = []

    for po_file in po_index:
        msgctxt = False
        msgstr = False
        string = ''

        for line in po_file['content_lines']:
            if not msgctxt and line.startswith('msgctxt "{ctxt}"'.format(ctxt=ctxt)):
                msgctxt = True
                continue

            if msgctxt:
                if po_file['language_code'] == 'en_GB':
                    if not msgstr and line.startswith('msgid '):
                        msgstr = True
                        string += line.replace('msgid ', '')
                        continue

                    if line.startswith('msgstr '):
                        break

                    string += line
                    continue

                else:
                    if not msgstr and not line.startswith('msgstr '):
                        continue

                    if not msgstr and line.startswith('msgstr '):
                        msgstr = True
                        string += line.replace('msgstr ', '')
                        continue

                    if not line.startswith('"'):
                        break

                    string += line
                    continue

        if string:
            string = string.replace('"\n"', '')
            string = string.replace('\n', '')
            string = string.replace('\\"', '%repdq%')
            string = string.replace('"', '')
            string = string.replace('%repdq%', '\\"')

            payload.append((po_file['language_code'], string))

    print('{ctxt} from po files...'.format(ctxt=ctxt))
    print(payload)
    print('')
    return payload


def get_xml_descriptions(addon_xml):
    """
    Get all the description metadata from the addon.xml
    :param addon_xml: addon.xml information from get_addon_xml()
    :type addon_xml: dict
    :return: descriptions from the addon.xml [(<whitespace>, <language code>, <description>), ...]
    :rtype: list[tuple]
    """
    descriptions = RE_DESCRIPTION.findall(addon_xml.get('content', ''))
    print('Descriptions from the addon.xml...')
    print(descriptions)
    print('')
    return descriptions


def get_xml_disclaimers(addon_xml):
    """
    Get all the disclaimers metadata from the addon.xml
    :param addon_xml: addon.xml information from get_addon_xml()
    :type addon_xml: dict
    :return: descriptions from the addon.xml [(<whitespace>, <language code>, <disclaimer>), ...]
    :rtype: list[tuple]
    """
    disclaimers = RE_DISCLAIMER.findall(addon_xml.get('content', ''))
    print('Disclaimers from the addon.xml...')
    print(disclaimers)
    print('')
    return disclaimers


def get_xml_summaries(addon_xml):
    """
    Get all the summaries metadata from the addon.xml
    :param addon_xml: addon.xml information from get_addon_xml()
    :type addon_xml: dict
    :return: summaries from the addon.xml [(<whitespace>, <language code>, <summary>), ...]
    :rtype: list[tuple]
    """
    summaries = RE_SUMMARY.findall(addon_xml.get('content', ''))
    print('Summaries from the addon.xml...')
    print(summaries)
    print('')
    return summaries


def get_xml_lifecyclestates(addon_xml):
    """
    Get all the lifecyclestates metadata from the addon.xml
    :param addon_xml: addon.xml information from get_addon_xml()
    :type addon_xml: dict
    :return: lifecyclestates from the addon.xml [(<whitespace>, <language code>, <lifecyclestate>), ...]
    :rtype: list[tuple]
    """
    lifecyclestates = RE_LIFECYCLESTATE.findall(addon_xml.get('content', ''))
    print('Lifecyclestates from the addon.xml...')
    print(lifecyclestates)
    print('')
    return lifecyclestates


def xml_remove_elements(addon_xml):
    """
    Remove all descriptions, disclaimers, and summaries from the addon.xml
    :param addon_xml: addon.xml information from get_addon_xml()
    :type addon_xml: dict
    :return: addon.xml information from get_addon_xml() with elements removed
    :rtype: dict
    """
    new_lines = []
    for line in addon_xml['content_lines']:
        if '<description lang=' in line:
            continue

        if '<disclaimer lang=' in line:
            continue

        if '<summary lang=' in line:
            continue

        if '<lifecyclestate ' in line:
            continue

        new_lines.append(line)

    if new_lines != addon_xml['content_lines']:
        addon_xml['content_lines'] = new_lines

    return addon_xml


def walk(directory, pattern):
    """
    Generator to walk the provided directory and yield files matching the pattern
    :param directory: directory to recursively walk
    :type directory: str
    :param pattern: glob pattern, https://docs.python.org/3/library/fnmatch.html
    :type pattern: str
    :return: filenames (with path) matching pattern
    :rtype: str
    """
    for root, dirs, files in os.walk(directory):
        for basename in files:
            if fnmatch.fnmatch(basename, pattern):
                fname = os.path.join(root, basename)
                yield fname


def find_addon_xml_in(working_directory):
    """
    Walk the provided working directory to find the addon.xml.in
    :param working_directory: directory to recursively search for the addon.xml.in
    :type working_directory: str
    :return: path with filename to the addon.xml.in
    :rtype: str
    """
    for filename in walk(working_directory, 'addon.xml.in'):
        print('Found addon.xml.in:', filename)
        return filename

    return ''


def get_addon_xml(working_directory):
    """
    Get the addon.xml[.in] in the working directory
    :param working_directory: directory to recursively search for the addon.xml[.in]
    :type working_directory: str
    :return: addon.xml information
             {'filename': <filename with path to addon.xml[.in]>,
              'content': <contents of the addon.xml[.in] from read()>,
              'content_lines': <contents of the addon.xml[.in] from readlines()>}
    :rtype: dict
    """
    addon_xml = {}

    filename_and_path = os.path.join(working_directory, 'addon.xml')
    if not os.path.isfile(filename_and_path):
        filename_and_path = find_addon_xml_in(working_directory)  # binary add-on

    if os.path.isfile(filename_and_path):
        with open(filename_and_path, encoding='utf-8') as file_handle:
            addon_xml = {
                'filename': filename_and_path,
                'content_lines': file_handle.readlines(),
            }

            file_handle.seek(0)
            addon_xml['content'] = file_handle.read()

    return addon_xml


def language_code_from_path(language_path):
    """
    Get the language code from the path
    :param language_path: path containing the language files
    :type language_path: str
    :return: language code ie. en_GB
    :rtype: str
    """
    language_code = ''
    match = re.search(
        r'resource\.language\.(?P<language_code>[a-z]{2,3}(?:_[A-Za-z]{2})?(?:@\S+)?)',
        language_path
    )
    if match:
        language_code = match.group('language_code')
        if '_' in language_code:
            language_code = '_'.join([language_code.split('_')[0],
                                      language_code.split('_')[1][:2].upper() +
                                      language_code.split('_')[1][2:]])

    return language_code


def generate_po_index(working_directory):
    """
    Generate and index of all po files in the working directory (recursive)
    :param working_directory: directory to search for po files
    :type working_directory: str
    :return: list of po files found in the working directory
             [{'filename': <filename with path to the po file>,
              'language_code': <language code of the po file>,
              'content': <contents of the po file from read()>,
              'content_lines': <contents of the po file from readlines()>}, ...]
    :rtype: list[dict]
    """
    file_index = []
    for path, _, filenames in list(os.walk(working_directory)):
        if 'resource.language.' not in path:
            continue

        files = [filename for filename in filenames if filename.endswith('.po')]
        for filename in files:
            filename_and_path = os.path.join(path, filename)

            with open(filename_and_path, encoding='utf-8') as file_handle:
                content_lines = file_handle.readlines()
                file_handle.seek(0)
                content = file_handle.read()

            file_index.append({
                'filename': filename_and_path,
                'language_code': language_code_from_path(path),
                'content_lines': content_lines,
                'content': content
            })

    return file_index


def get_default_po(po_index):
    """
    Find the default (en_GB) po file
    :param po_index: index of po files from generate_po_index()
    :type po_index: list[dict]
    :return: default po file information from the po index
    :rtype: dict
    """
    for po_file in po_index:
        if po_file['language_code'] in ['en_gb', 'en_GB']:
            return po_file

    return {}


def get_xml_whitespace(addon_xml, descriptions, disclaimers, summaries, lifecyclestates):
    """
    Get the whitespace used in the xml to keep formatting consistent
    Descriptions, disclaimers, summaries and other metadata is checked in that order
    and the first match is used
    :param addon_xml: addon.xml information from get_addon_xml()
    :type addon_xml: dict
    :param descriptions: all the addon.xml descriptions [(<whitespace>, <language code>, <description>), ...]
    :type descriptions: list[tuple]
    :param disclaimers: all the addon.xml disclaimers [(<whitespace>, <language code>, <disclaimer>), ...]
    :type disclaimers: list[tuple]
    :param summaries: all the addon.xml summaries [(<whitespace>, <language code>, <summary>), ...]
    :type summaries: list[tuple]
    :param lifecyclestates: all the addon.xml lifecyclestates [(<whitespace>, <language code>, <lifecyclestates>), ...]
    :type lifecyclestates: list[tuple]
    :return: whitespace
    :rtype: str
    """
    if len(descriptions) > 0:
        return descriptions[0][0]

    if len(disclaimers) > 0:
        return disclaimers[0][0]

    if len(summaries) > 0:
        return summaries[0][0]

    if len(lifecyclestates) > 0:
        return lifecyclestates[0][0]

    whitespace_candidates = RE_METADATA_WHITESPACE.findall(addon_xml['content'])
    if len(whitespace_candidates) > 0:
        return whitespace_candidates[0]

    return ''


def get_lifecyclestate_type(addon_xml):
    """
    Get the lifecyclestate type attribute value
    :param addon_xml: addon.xml information from get_addon_xml()
    :type addon_xml: dict
    :return: lifecyclestate type attribute value
    :rtype: str|None
    """
    found_type = RE_LIFECYCLESTATE_TYPE.search(addon_xml.get('content', ''))

    if found_type:
        return found_type.group('type')

    return None


def get_xml_insert_index(addon_xml):
    """
    Find where in the addon.xml to insert metadata
    :param addon_xml: addon.xml information from get_addon_xml()
    :type addon_xml: dict
    :return: index of the line to insert metadata
    :rtype: int
    """
    insert_line = -1

    for index, line in enumerate(addon_xml['content_lines']):
        if '<extension' in line and 'xbmc.addon.metadata' in line:
            insert_line = index + 1

        if insert_line > -1 and '</extension>' in line:
            insert_line = index
            break

    if insert_line == -1:
        raise Exception('Unable to determine addon.xml insert index')

    return insert_line


def merge_items(group_one, group_two):
    """
    Merge two lists of tuples, group one will not be overwritten if group[0] matches in both groups
    :param group_one: xml or po metadata
    :type group_one: list[tuple]
    :param group_two: xml or po metadata
    :type group_two: list[tuple]
    :return: combined groups
    :rtype: list[tuple]
    """
    payload = group_one.copy()
    for group_item in group_two:
        if not any(item for item in payload if item[0] == group_item[0]):
            payload.append(group_item)

    return payload


def merge_po_lines(summary_lines, description_lines, disclaimer_lines, lifecyclestate_lines):
    """
    Merge summary, description, disclaimer lines and group by language
    :param summary_lines: summaries for all po files [(<language_code>, <summary>), ...]
    :type summary_lines: list[tuple]
    :param description_lines: descriptions for all po files [(<language_code>, <description>), ...]
    :type description_lines: list[tuple]
    :param disclaimer_lines: disclaimers for all po files [(<language_code>, <disclaimer>), ...]
    :type disclaimer_lines: list[tuple]
    :param lifecyclestate_lines: lifecyclestates for all po files [(<language_code>, <lifecyclestate>), ...]
    :type lifecyclestate_lines: list[tuple]
    :return: summary, description, disclaimer, lifecyclestate lines grouped by language
    :rtype: dict
    """
    payload = {}

    en_gb_summary = next((item[1] for item in summary_lines if item[0] == 'en_GB'), [])
    en_gb_description = next((item[1] for item in description_lines if item[0] == 'en_GB'), [])
    en_gb_disclaimer = next((item[1] for item in disclaimer_lines if item[0] == 'en_GB'), [])
    en_gb_lifecyclestate = \
        next((item[1] for item in lifecyclestate_lines if item[0] == 'en_GB'), [])

    languages = list(set(
        [item[0] for item in summary_lines] +
        [item[0] for item in description_lines] +
        [item[0] for item in disclaimer_lines] +
        [item[0] for item in lifecyclestate_lines]
    ))

    for language in languages:
        payload[language] = []
        payload[language] += next(
            (item[1] for item in summary_lines if item[0] == language), en_gb_summary
        )
        payload[language] += next(
            (item[1] for item in description_lines if item[0] == language), en_gb_description
        )
        payload[language] += next(
            (item[1] for item in disclaimer_lines if item[0] == language), en_gb_disclaimer
        )
        payload[language] += next(
            (item[1] for item in lifecyclestate_lines if item[0] == language), en_gb_lifecyclestate
        )

    return payload


def get_po_lines(items, ctxt):
    """
    Create po lines from descriptions, disclaimers or summaries
    :param items: descriptions, disclaimers or summaries
    :type items: list[tuple]
    :param ctxt: ctxt to use for po lines
    :type ctxt: str
    :return: created po lines
    :rtype: list[tuple]
    """
    payload = []

    en_gb = next((item for item in items if item[0] == 'en_GB'), None)

    if en_gb:
        for item in items:
            payload.append((
                item[0],
                [
                    POTPL_MSGCTXT.format(string=ctxt),
                    POTPL_MSGID.format(string=en_gb[1]),
                    POTPL_MSGSTR.format(string='' if item[0] == 'en_GB' else item[1]),
                    '\n'
                ]
            ))

    else:
        print('Unable to generate lines for {ctxt}... missing en_GB'.format(ctxt=ctxt))

    return payload


def remove_po_lines(po_index):
    """
    Remove metadata lines from po files
    :param po_index: index of po files from generate_po_index()
    :type po_index: list[dict]
    :return: po index with metadata lines removed 'content_lines'
    :rtype: list[dict]
    """
    payload = copy.deepcopy(po_index)

    ctxt_targets = (
        'msgctxt "{ctxt}"'.format(ctxt=CTXT_SUMMARY),
        'msgctxt "{ctxt}"'.format(ctxt=CTXT_DESCRIPTION),
        'msgctxt "{ctxt}"'.format(ctxt=CTXT_DISCLAIMER),
        'msgctxt "{ctxt}"'.format(ctxt=CTXT_LIFECYCLESTATE)
    )

    for index, po_item in enumerate(po_index):
        msgctxt = False
        msgid = False
        msgstr = False

        payload[index]['content_lines'] = []
        for line in po_item['content_lines']:
            if not msgctxt and line.startswith(ctxt_targets):
                msgctxt = True
                continue

            if msgctxt:
                if not msgid:
                    if line.startswith('msgid '):
                        msgid = True
                    continue

            if msgid:
                if not msgstr:
                    if line.startswith('msgstr '):
                        msgstr = True
                    continue

            if msgctxt and msgid and msgstr:

                if not line.strip():
                    msgctxt = False
                    msgid = False
                    msgstr = False
                    continue

                elif line.startswith('"'):
                    continue

                else:
                    msgctxt = False
                    msgid = False
                    msgstr = False

            payload[index]['content_lines'] = payload[index].get('content_lines', []) + [line]

    return payload


def get_po_insert_index(po_file):
    """
    Find where in the po file to insert metadata
    :param po_file: contents of po_index[<#>]['content_lines']
    :type po_file: list
    :return: index of the line to insert metadata
    :rtype: int
    """
    msgstr = False
    first_quote = False

    insert_index = -1

    for index, line in enumerate(po_file):
        if not msgstr and line.startswith('msgstr ""'):
            msgstr = True
            continue

        if msgstr:
            if not first_quote and line.startswith('"'):
                first_quote = True
                continue

            if first_quote and not line.startswith('"'):
                insert_index = index + 1
                break

    return insert_index


def format_po_lines(po_lines):
    """
    Format po lines for addition to po files
    :param po_lines: un-formatted lines to be added to the po file
    :type po_lines: list
    :return: formatted lines to be added to the po file
    :rtype: list
    """
    format_lines = []
    po_lines = [line for line in po_lines if line.strip()]  # remove empty lines
    po_lines = list(zip(*(iter(po_lines),) * 3))  # group in threes (msgctxt, msgid, msgstr)

    for lines in po_lines:  # add sorting weights
        if lines[0].startswith('msgctxt "{ctxt}"'.format(ctxt=CTXT_SUMMARY)):
            format_lines.append((lines, 0))
            continue

        if lines[0].startswith('msgctxt "{ctxt}"'.format(ctxt=CTXT_DESCRIPTION)):
            format_lines.append((lines, 1))
            continue

        if lines[0].startswith('msgctxt "{ctxt}"'.format(ctxt=CTXT_DISCLAIMER)):
            format_lines.append((lines, 2))
            continue

        if lines[0].startswith('msgctxt "{ctxt}"'.format(ctxt=CTXT_LIFECYCLESTATE)):
            format_lines.append((lines, 3))
            continue

    format_lines.sort(key=lambda x: x[1])
    format_lines = [lines[0] for lines in format_lines]  # remove weights

    payload = []
    for lines in format_lines:
        payload.extend(list(lines) + ['\n'])

    return payload


def insert_po_lines(po_index, po_lines):
    """
    Insert po lines into po_index[<#>]['content_lines']
    :param po_index: index of po files from generate_po_index()
    :type po_index: list[dict]
    :param po_lines: un-formatted lines to be added to the po file by language code
    :type po_lines: dict
    :return: po_index with po_index[<#>]['content_lines'] updated
    :rtype: dict
    """
    payload = copy.deepcopy(po_index)
    languages = list(po_lines.keys())

    for index, po_item in enumerate(po_index):
        insert_index = get_po_insert_index(po_item['content_lines'])
        if insert_index <= 0:
            print('Skipped inserting lines into {language_code} po file...'
                  .format(language_code=po_item.get('language_code')))

        insert_lines = []
        if po_item.get('language_code') in languages:
            insert_lines = po_lines.get(po_item.get('language_code'))
        elif 'en_GB' in languages:
            insert_lines = po_lines.get('en_GB')

        if insert_lines:
            insert_lines = format_po_lines(insert_lines)

            payload[index]['content_lines'] = po_item['content_lines'][:insert_index] + \
                                              insert_lines + \
                                              po_item['content_lines'][insert_index:]

            # remove whitespace from eof
            for idx, line in reversed(list(enumerate(payload[index]['content_lines']))):
                if line.strip() == '':
                    del payload[index]['content_lines'][idx]
                else:
                    break

            # ensure one new line at end of file
            po_item['content_lines'] += ['\n']

    return payload


def write_po_files(po_index, output_index):
    """
    Write po files which have altered `po_index`, compared against `output_index`
    :param po_index: index of po files from generate_po_index()
    :type po_index: list[dict]
    :param output_index: index of languages with modified po_index[<#>]['content_lines']
    :type output_index: dict
    """
    print('Writing po files... starting')

    for index, po_item in enumerate(output_index):
        if po_item.get('content_lines') != po_index[index].get('content_lines'):
            print('{language_code} po file changed... writing'
                  .format(language_code=po_item.get('language_code')))

            with open(po_item.get('filename'), 'w', encoding='utf-8') as file_handle:
                file_handle.writelines(po_item.get('content_lines'))

    print('Writing po files... completed')


def escape_characters(source, dest='po'):
    """
    Escape quotes in metadata for target medium; po: `\"`, xml: `&quot;`
    :param source: list of strings to escape [(<language_code>, <string>), ...]
    :type source: list[tuple]
    :param dest: `po` or `xml`
    :type dest: str
    :return: escaped strings
    :rtype: list[tuple]
    """
    if dest not in ['xml', 'po']:
        dest = 'po'

    if dest == 'po':
        return [(lang_code, string.replace(r'&quot;', r'\"'))
                for lang_code, string in source]
    else:
        return [
            (
                lang_code,
                string.replace(r'"', r'&quot;')
                    .replace(r"'", r'&apos;')
                    .replace(r'<', r'&lt;')
                    .replace(r'>', r'&gt;')
                    .replace(r'&', r'&amp;'),
            )
            for lang_code, string in source
        ]


def xml_to_po(addon_xml, po_index, priority='xml'):
    """
    Sync addon.xml metadata to PO files
    :param addon_xml: addon.xml information from get_addon_xml()
    :type addon_xml: dict
    :param po_index: index of po files from generate_po_index()
    :type po_index: list[dict]
    :param priority: which file takes priority if metadata exists in both files; `xml` or `po`
    :type priority: str
    """
    print('Syncing addon.xml to po files...')

    if priority not in ['xml', 'po']:
        priority = 'xml'

    lifecyclestate_type = get_lifecyclestate_type(addon_xml)

    xml_lifecyclestates = []
    if lifecyclestate_type:
        xml_lifecyclestates = get_xml_lifecyclestates(addon_xml)

    xml_descriptions = get_xml_descriptions(addon_xml)
    xml_disclaimers = get_xml_disclaimers(addon_xml)
    xml_summaries = get_xml_summaries(addon_xml)

    xml_descriptions = [(language_code, body) for _, language_code, body in xml_descriptions]
    xml_disclaimers = [(language_code, body) for _, language_code, body in xml_disclaimers]
    xml_summaries = [(language_code, body) for _, language_code, body in xml_summaries]
    xml_lifecyclestates = [(language_code, body) for _, language_code, body in xml_lifecyclestates]

    po_descriptions = get_po_metadata(po_index, CTXT_DESCRIPTION)
    po_disclaimers = get_po_metadata(po_index, CTXT_DISCLAIMER)
    po_summaries = get_po_metadata(po_index, CTXT_SUMMARY)
    po_lifecyclestates = get_po_metadata(po_index, CTXT_LIFECYCLESTATE)

    if priority == 'xml':
        descriptions = merge_items(xml_descriptions, po_descriptions)
        disclaimers = merge_items(xml_disclaimers, po_disclaimers)
        summaries = merge_items(xml_summaries, po_summaries)
        lifecyclestates = merge_items(xml_lifecyclestates, po_lifecyclestates)
    else:  # 'po'
        descriptions = merge_items(po_descriptions, xml_descriptions)
        disclaimers = merge_items(po_disclaimers, xml_disclaimers)
        summaries = merge_items(po_summaries, xml_summaries)
        lifecyclestates = merge_items(po_lifecyclestates, xml_lifecyclestates)

    descriptions = escape_characters(descriptions, dest='po')
    disclaimers = escape_characters(disclaimers, dest='po')
    summaries = escape_characters(summaries, dest='po')
    lifecyclestates = escape_characters(lifecyclestates, dest='po')

    description_lines = get_po_lines(descriptions, CTXT_DESCRIPTION)
    disclaimer_lines = get_po_lines(disclaimers, CTXT_DISCLAIMER)
    summary_lines = get_po_lines(summaries, CTXT_SUMMARY)
    lifecyclestate_lines = get_po_lines(lifecyclestates, CTXT_LIFECYCLESTATE)

    po_lines = merge_po_lines(summary_lines, description_lines,
                              disclaimer_lines, lifecyclestate_lines)

    payload_index = remove_po_lines(po_index)

    payload_index = insert_po_lines(payload_index, po_lines)

    write_po_files(po_index, payload_index)


def po_to_xml(addon_xml, po_index):
    """
    Sync PO metadata to addon.xml
    :param addon_xml: addon.xml information from get_addon_xml()
    :type addon_xml: dict
    :param po_index: index of po files from generate_po_index()
    :type po_index: list[dict]
    """
    print('Syncing po files to addon.xml...')
    lifecyclestate_type = get_lifecyclestate_type(addon_xml)

    xml_lifecyclestates = []
    if lifecyclestate_type:
        xml_lifecyclestates = get_xml_lifecyclestates(addon_xml)

    xml_descriptions = get_xml_descriptions(addon_xml)
    xml_disclaimers = get_xml_disclaimers(addon_xml)
    xml_summaries = get_xml_summaries(addon_xml)

    addon_xml = xml_remove_elements(addon_xml)

    xml_whitespace = get_xml_whitespace(addon_xml, xml_descriptions, xml_disclaimers,
                                        xml_summaries, xml_lifecyclestates)

    xml_descriptions = [(language_code, body) for _, language_code, body in xml_descriptions]
    xml_disclaimers = [(language_code, body) for _, language_code, body in xml_disclaimers]
    xml_summaries = [(language_code, body) for _, language_code, body in xml_summaries]
    xml_lifecyclestates = [(language_code, body) for _, language_code, body in xml_lifecyclestates]

    po_descriptions = get_po_metadata(po_index, CTXT_DESCRIPTION)
    po_disclaimers = get_po_metadata(po_index, CTXT_DISCLAIMER)
    po_summaries = get_po_metadata(po_index, CTXT_SUMMARY)
    po_lifecyclestates = get_po_metadata(po_index, CTXT_LIFECYCLESTATE)

    descriptions = merge_items(po_descriptions, xml_descriptions)
    disclaimers = merge_items(po_disclaimers, xml_disclaimers)
    summaries = merge_items(po_summaries, xml_summaries)
    lifecyclestates = merge_items(po_lifecyclestates, xml_lifecyclestates)

    descriptions = escape_characters(descriptions, dest='xml')
    disclaimers = escape_characters(disclaimers, dest='xml')
    summaries = escape_characters(summaries, dest='xml')
    lifecyclestates = escape_characters(lifecyclestates, dest='xml')

    descriptions.sort(key=lambda item: item[0])
    disclaimers.sort(key=lambda item: item[0])
    summaries.sort(key=lambda item: item[0])
    lifecyclestates.sort(key=lambda item: item[0])

    description_lines = [
        XMLTPL_DESCRIPTION.format(whitespace=xml_whitespace, language_code=language_code, body=body)
        for language_code, body in descriptions if body
    ]
    disclaimer_lines = [
        XMLTPL_DISCLAIMER.format(whitespace=xml_whitespace, language_code=language_code, body=body)
        for language_code, body in disclaimers if body
    ]
    summary_lines = [
        XMLTPL_SUMMARY.format(whitespace=xml_whitespace, language_code=language_code, body=body)
        for language_code, body in summaries if body
    ]
    lifecyclestate_lines = [
        XMLTPL_LIFECYCLESTATE.format(whitespace=xml_whitespace, type=lifecyclestate_type,
                                     language_code=language_code, body=body)
        for language_code, body in lifecyclestates if body
    ]

    insert_index = get_xml_insert_index(addon_xml)
    payload = addon_xml['content_lines'].copy()

    payload = payload[:insert_index] + summary_lines + description_lines + disclaimer_lines + \
              lifecyclestate_lines + payload[insert_index:]

    if payload != addon_xml['content_lines']:
        with open(addon_xml['filename'], 'w', encoding='utf-8') as file_handle:
            file_handle.writelines(payload)

        print('addon.xml has been modified... completed')
        return

    print('No changes made to addon.xml... completed')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-ptx', '--po-to-xml', action='store_true',
                        help='sync po file values to the addon.xml file')
    parser.add_argument('-xtp', '--xml-to-po', action='store_true',
                        help='sync addon.xml values to all po files')
    parser.add_argument('-path', '--path', type=directory_type, nargs='?', default='.',
                        const='.', help='working directory')
    parser.add_argument('-multi', '--multiple-addons', action='store_true',
                        help='multiple add-ons in the working directory')
    parser.add_argument('-v', '--version', action='store_true',
                        help='prints the version of sync-addon-metadata-translations')

    args = parser.parse_args()

    if args.version:
        print('Version %s' % __version__)
        sys.exit(0)

    directories = [args.path]
    if args.multiple_addons:
        directories = [item for item in os.listdir(args.path)
                       if os.path.isdir(os.path.join(args.path, item))]

    for directory in directories:
        print('Running sync-addon-metadata-translations on %s...' % directory)

        _addon_xml = get_addon_xml(directory)
        if not _addon_xml:
            print('No addon.xml file found in %s... aborted' % directory)
            continue

        _po_index = generate_po_index(directory)
        if not _po_index:
            print('No po files found in %s... aborted' % directory)
            continue

        _default_po = get_default_po(_po_index)
        if not _default_po:
            print('No en_gb po file found... aborted')
            continue

        if args.po_to_xml:
            po_to_xml(_addon_xml, _po_index)
            continue

        if args.xml_to_po:
            xml_to_po(_addon_xml, _po_index)
            continue

        po_to_xml(_addon_xml, _po_index)
        xml_to_po(_addon_xml, _po_index, priority='po')

    sys.exit(0)


if __name__ == '__main__':
    main()
