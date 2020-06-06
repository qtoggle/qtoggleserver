
import os.path

from setuptools import setup, find_namespace_packages

import qtoggleserver.version

try:
    import fastentrypoints

except ImportError:
    pass

try:
    import setupnovernormalize

except ImportError:
    pass


name = 'qtoggleserver'
version = qtoggleserver.version.VERSION
here = os.path.dirname(__file__) or '.'


setup(
    name=name,
    version=version,
    description='A fully fledged qToggle Python implementation',
    author='The qToggle Team',
    author_email='ccrisan@gmail.com',
    url='https://github.com/qtoggle/qtoggleserver',
    license='Apache 2.0',

    packages=find_namespace_packages(
        include=[name, f'{name}.*'],
        exclude=[f'{name}.frontend', f'{name}.frontend.*']
    ),
    namespace_packages=[name],
    py_modules=[f'{name}.{module}' for module in [
        'persist',
        'version'
    ]],

    install_requires=[
        'jinja2>=2.10',
        'jsonpointer>=2.0',
        'jsonschema>=2.5',
        'psutil>=5.5',
        'pyhocon>=0.3.50',
        'pyjwt>=1.7',
        'pytz',
        'qui-server>=1.11.0-beta.2',
        'tornado>=6.0',
    ],

    zip_safe=False,
    include_package_data=False,
    package_data={
        name: [
            'frontend/dist/font/*',
            'frontend/dist/templates/*',
            'frontend/dist/img/*',
            'frontend/dist/*'
        ]
    },
    data_files=[
        (f'share/{name}/{root[len(here) + 1:]}', [f'{root[len(here) + 1:]}/{f}' for f in files])
        for (root, dirs, files) in os.walk(os.path.join(here, 'extra'))
    ],

    entry_points={
        'console_scripts': [
            'qtoggleserver=qtoggleserver.commands.server:execute',
            'qtoggleshell=qtoggleserver.commands.shell:execute'
        ],
    }
)
