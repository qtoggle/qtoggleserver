
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
        'jinja2==2.11.1',
        'jsonpointer==2.0',
        'jsonschema==3.2.0',
        'psutil==5.7.0',
        'pyhocon==0.3.54',
        'pyjwt==1.7.1',
        'pytz==2019.3',
        'tornado==6.0.4',
    ],

    zip_safe=False,
    include_package_data=False,
    package_data={
        name: [
            'frontend/dist/font/*',
            'frontend/dist/html/*',
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
