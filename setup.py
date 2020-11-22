import os
import setuptools

import sync_addon_metadata_translations

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

_ROOT = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(_ROOT, 'README.md')) as f:
    LONG_DESCRIPTION = f.read()

setuptools.setup(
    name="sync-addon-metadata-translations",
    version=sync_addon_metadata_translations.__version__,
    description="Sync Kodi add-on metadata translations",
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    author="anxdpanic",
    url="https://github.com/anxdpanic/sync_addon_metadata_translations",
    download_url="https://github.com/anxdpanic/sync_addon_metadata_translations/archive/master.zip",
    packages=setuptools.find_packages(exclude=['tests*']),
    package_data={
        'sync_addon_metadata_translations': ['xml_schema/*.xsd']
    },
    install_requires=requirements,
    python_requires=">=3.5",
    setup_requires=['setuptools>=38.6.0'],
    entry_points={
        'console_scripts': [
            'sync-addon-metadata-translations = sync_addon_metadata_translations.__main__:main'
        ]
    },
    keywords=['kodi add-on', 'kodi', 'kodi translation', 'kodi addon.xml', 'kodi po'],
    classifiers=[
                    "Operating System :: POSIX :: Linux",
                    "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
                    "Operating System :: Microsoft :: Windows",
                    "Operating System :: MacOS",
                    "Development Status :: 5 - Production/Stable",
                    "Environment :: Console",
                    "Intended Audience :: Developers",
                    "Topic :: Utilities"
                ] + [('Programming Language :: Python :: %s' % x)
                     for x in '3 3.5 3.6 3.7 3.8 3.9'.split()]
)
