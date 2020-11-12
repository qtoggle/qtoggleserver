
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
        exclude=[f'{name}.frontend.node_modules.*']
    ),
    namespace_packages=[name],
    py_modules=[f'{name}.{module}' for module in [
        'persist',
        'version'
    ]],

    install_requires=[
        'jinja2>=2.10,<3',
        'jsonpointer>=2.0,<3',
        'jsonschema>=2.5,<4',
        'psutil>=5.5,<6',
        'pyhocon>=0.3.50,<1',
        'pyjwt>=1.7,<2',
        'pytz',
        'qui-server>=1.13.3',
        'tornado>=6.0,<7',
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
