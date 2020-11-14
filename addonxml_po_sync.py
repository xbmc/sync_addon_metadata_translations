# -*- coding: utf-8 -*-

import argparse
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


def get_addon_xml():
    addon_xml = {}
    filename_and_path = os.path.join('.', 'addon.xml')

    if os.path.isfile(filename_and_path):
        with open(filename_and_path) as file_handle:
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
        language_code = '_'.join([language_code.split('_')[0],
                                  language_code.split('_')[1][:2].upper() +
                                  language_code.split('_')[1][2:]])

    return language_code


def generate_po_index():
    file_index = []
    for path, _, filenames in list(os.walk('.')):
        files = [filename for filename in filenames if filename.endswith('.po')]
        for filename in files:
            filename_and_path = os.path.join(path, filename)

            with open(filename_and_path) as file_handle:
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


def _merge_items(group_one, group_two):
    payload = group_one.copy()
    for group_item in group_two:
        if not any(item for item in payload if item[0] == group_item[0]):
            payload.append(group_item)

    return payload


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

    descriptions = _merge_items(xml_descriptions, po_descriptions)
    disclaimers = _merge_items(xml_disclaimers, po_disclaimers)
    summaries = _merge_items(xml_summaries, po_summaries)


def po_to_xml(addon_xml, po_index):
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

    descriptions = _merge_items(po_descriptions, xml_descriptions)
    disclaimers = _merge_items(po_disclaimers, xml_disclaimers)
    summaries = _merge_items(po_summaries, xml_summaries)

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
        with open('addon.xml', 'w') as file_handle:
            file_handle.writelines(payload)

        print('addon.xml has been modified... completed')
        return

    print('No changes made to addon.xml... completed')


if __name__ == '__main__':
    _addon_xml = get_addon_xml()
    if not _addon_xml:
        print('No addon.xml file found... aborting')
        sys.exit(1)

    _po_index = generate_po_index()
    if not _po_index:
        print('No po files found... aborting')
        sys.exit(1)

    _default_po = get_default_po(_po_index)
    if not _default_po:
        print('No en_gb po file found... aborting')
        sys.exit(1)

    parser = argparse.ArgumentParser()
    parser.add_argument('-ptx', '--po-to-xml', action='store_true',
                        help='Sync po file values to the addon.xml file')
    parser.add_argument('-xtp', '--xml-to-po', action='store_true',
                        help='Sync addon.xml values to all po files')

    args = parser.parse_args()

    if args.po_to_xml:
        po_to_xml(_addon_xml, _po_index)
        sys.exit(0)

    if args.xml_to_po:
        xml_to_po(_addon_xml, _po_index)
        sys.exit(0)

    sys.exit(1)
