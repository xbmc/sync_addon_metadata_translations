#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    Copyright (C) 2020 anxdpanic

    This file is part of sync_addon_metadata_translations

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only.txt for more information.
"""

import argparse
import copy
import os
import re
import sys

CTXT_DESCRIPTION = 'Addon Description'
CTXT_DISCLAIMER = 'Addon Disclaimer'
CTXT_SUMMARY = 'Addon Summary'

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

POTPL_MSGCTXT = 'msgctxt "{string}"\n'
POTPL_MSGID = 'msgid "{string}"\n'
POTPL_MSGSTR = 'msgstr "{string}"\n'


def directory_type(string):
    if os.path.isdir(string):
        return string

    raise NotADirectoryError(string)


def get_po_metadata(po_index, ctxt):
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

            if string:
                payload.append((po_file['language_code'], string))

    print('{ctxt} from po files...'.format(ctxt=ctxt))
    print(payload)
    print('')
    return payload


def get_xml_descriptions(addon_xml):
    descriptions = RE_DESCRIPTION.findall(addon_xml.get('content', ''))
    print('Descriptions from the addon.xml...')
    print(descriptions)
    print('')
    return descriptions


def get_xml_disclaimers(addon_xml):
    disclaimers = RE_DISCLAIMER.findall(addon_xml.get('content', ''))
    print('Disclaimers from the addon.xml...')
    print(disclaimers)
    print('')
    return disclaimers


def get_xml_summaries(addon_xml):
    summaries = RE_SUMMARY.findall(addon_xml.get('content', ''))
    print('Summaries from the addon.xml...')
    print(summaries)
    print('')
    return summaries


def xml_remove_tags(addon_xml):
    new_lines = []
    for line in addon_xml['content_lines']:
        if 'description lang=' in line:
            continue

        if 'disclaimer lang=' in line:
            continue

        if 'summary lang=' in line:
            continue

        new_lines.append(line)

    if new_lines != addon_xml['content_lines']:
        addon_xml['content_lines'] = new_lines

    return addon_xml


def get_addon_xml(working_directory):
    addon_xml = {}
    filename_and_path = os.path.join(working_directory, 'addon.xml')

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
    for po_file in po_index:
        if po_file['language_code'] in ['en_gb', 'en_GB']:
            return po_file

    return {}


def get_xml_whitespace(addon_xml, descriptions, disclaimers, summaries):
    if len(descriptions) > 0:
        return descriptions[0][0]

    if len(disclaimers) > 0:
        return disclaimers[0][0]

    if len(summaries) > 0:
        return summaries[0][0]

    whitespace_candidates = RE_METADATA_WHITESPACE.findall(addon_xml['content'])
    if len(whitespace_candidates) > 0:
        return whitespace_candidates[0]


def get_xml_insert_index(addon_xml):
    insert_line = -1

    for index, line in enumerate(addon_xml['content_lines']):
        if '<extension point="xbmc.addon.metadata">' in line:
            insert_line = index + 1

        if insert_line > -1 and '</extension>' in line:
            insert_line = index
            break

    return insert_line


def merge_items(group_one, group_two):
    payload = group_one.copy()
    for group_item in group_two:
        if not any(item for item in payload if item[0] == group_item[0]):
            payload.append(group_item)

    return payload


def merge_po_lines(summary_lines, description_lines, disclaimer_lines):
    count = max(map(len, [summary_lines, description_lines, disclaimer_lines]))

    payload = {}

    for index in range(count):
        try:
            payload[summary_lines[index][0]] = \
                payload.get(summary_lines[index][0], []) + summary_lines[index][1]
        except IndexError:
            pass

        try:
            payload[description_lines[index][0]] = \
                payload.get(description_lines[index][0], []) + description_lines[index][1]
        except IndexError:
            pass

        try:
            payload[disclaimer_lines[index][0]] = \
                payload.get(disclaimer_lines[index][0], []) + disclaimer_lines[index][1]
        except IndexError:
            pass

    return payload


def get_po_lines(items, ctxt):
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
    payload = copy.deepcopy(po_index)

    ctxt_targets = (
        'msgctxt "{ctxt}"'.format(ctxt=CTXT_SUMMARY),
        'msgctxt "{ctxt}"'.format(ctxt=CTXT_DESCRIPTION),
        'msgctxt "{ctxt}"'.format(ctxt=CTXT_DISCLAIMER)
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

    format_lines.sort(key=lambda x: x[1])
    format_lines = [lines[0] for lines in format_lines]  # remove weights

    payload = []
    for lines in format_lines:
        payload.extend(list(lines) + ['\n'])

    return payload


def insert_po_lines(po_index, po_lines):
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

    return payload


def write_po_files(po_index, output_index):
    print('Writing po files... starting')

    for index, po_item in enumerate(output_index):
        if po_item.get('content_lines') != po_index[index].get('content_lines'):
            print('{language_code} po file changed... writing'
                  .format(language_code=po_item.get('language_code')))

            with open(po_item.get('filename'), 'w', encoding='utf-8') as file_handle:
                file_handle.writelines(po_item.get('content_lines'))

    print('Writing po files... completed')


def xml_to_po(addon_xml, po_index):
    print('Syncing addon.xml to po files...')

    xml_descriptions = get_xml_descriptions(addon_xml)
    xml_disclaimers = get_xml_disclaimers(addon_xml)
    xml_summaries = get_xml_summaries(addon_xml)

    xml_descriptions = [(language_code, body) for _, language_code, body in xml_descriptions]
    xml_disclaimers = [(language_code, body) for _, language_code, body in xml_disclaimers]
    xml_summaries = [(language_code, body) for _, language_code, body in xml_summaries]

    po_descriptions = get_po_metadata(po_index, CTXT_DESCRIPTION)
    po_disclaimers = get_po_metadata(po_index, CTXT_DISCLAIMER)
    po_summaries = get_po_metadata(po_index, CTXT_SUMMARY)

    descriptions = merge_items(xml_descriptions, po_descriptions)
    disclaimers = merge_items(xml_disclaimers, po_disclaimers)
    summaries = merge_items(xml_summaries, po_summaries)

    description_lines = get_po_lines(descriptions, CTXT_DESCRIPTION)
    disclaimer_lines = get_po_lines(disclaimers, CTXT_DISCLAIMER)
    summary_lines = get_po_lines(summaries, CTXT_SUMMARY)

    po_lines = merge_po_lines(summary_lines, description_lines, disclaimer_lines)

    payload_index = remove_po_lines(po_index)

    payload_index = insert_po_lines(payload_index, po_lines)

    write_po_files(po_index, payload_index)


def po_to_xml(directory, addon_xml, po_index):
    print('Syncing po files to addon.xml...')

    xml_descriptions = get_xml_descriptions(addon_xml)
    xml_disclaimers = get_xml_disclaimers(addon_xml)
    xml_summaries = get_xml_summaries(addon_xml)

    addon_xml = xml_remove_tags(addon_xml)

    xml_whitespace = get_xml_whitespace(addon_xml, xml_descriptions, xml_disclaimers, xml_summaries)

    xml_descriptions = [(language_code, body) for _, language_code, body in xml_descriptions]
    xml_disclaimers = [(language_code, body) for _, language_code, body in xml_disclaimers]
    xml_summaries = [(language_code, body) for _, language_code, body in xml_summaries]

    po_descriptions = get_po_metadata(po_index, CTXT_DESCRIPTION)
    po_disclaimers = get_po_metadata(po_index, CTXT_DISCLAIMER)
    po_summaries = get_po_metadata(po_index, CTXT_SUMMARY)

    descriptions = merge_items(po_descriptions, xml_descriptions)
    disclaimers = merge_items(po_disclaimers, xml_disclaimers)
    summaries = merge_items(po_summaries, xml_summaries)

    descriptions.sort(key=lambda item: item[0])
    disclaimers.sort(key=lambda item: item[0])
    summaries.sort(key=lambda item: item[0])

    description_lines = [
        XMLTPL_DESCRIPTION.format(whitespace=xml_whitespace, language_code=language_code, body=body)
        for language_code, body in descriptions
    ]
    disclaimer_lines = [
        XMLTPL_DISCLAIMER.format(whitespace=xml_whitespace, language_code=language_code, body=body)
        for language_code, body in disclaimers
    ]
    summary_lines = [
        XMLTPL_SUMMARY.format(whitespace=xml_whitespace, language_code=language_code, body=body)
        for language_code, body in summaries
    ]

    insert_index = get_xml_insert_index(addon_xml)
    payload = addon_xml['content_lines'].copy()

    payload = payload[:insert_index] + summary_lines + \
              description_lines + disclaimer_lines + payload[insert_index:]

    if payload != addon_xml['content_lines']:
        with open(os.path.join(directory, 'addon.xml'), 'w', encoding='utf-8') as file_handle:
            file_handle.writelines(payload)

        print('addon.xml has been modified... completed')
        return

    print('No changes made to addon.xml... completed')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-ptx', '--po-to-xml', action='store_true',
                        help='Sync po file values to the addon.xml file')
    parser.add_argument('-xtp', '--xml-to-po', action='store_true',
                        help='Sync addon.xml values to all po files')
    parser.add_argument('-path', '--path', type=directory_type, nargs='?',
                        const='.', help='Specify the working directory')
    parser.add_argument('-multi', '--multiple-addons', action='store_true',
                        help='Specify there are multiple add-ons in the working directory')

    args = parser.parse_args()

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
            po_to_xml(directory, _addon_xml, _po_index)
            continue

        if args.xml_to_po:
            xml_to_po(_addon_xml, _po_index)
            continue

        po_to_xml(directory, _addon_xml, _po_index)
        xml_to_po(_addon_xml, _po_index)

    sys.exit(0)


if __name__ == '__main__':
    main()
