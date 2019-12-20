
import os.path
import shutil

from setuptools import setup, find_namespace_packages, Command
from setuptools.command.sdist import sdist

try:
    from wheel.bdist_wheel import bdist_wheel

except ImportError:
    bdist_wheel = None

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


class UIMakeMixin:
    def __init__(self):
        self.root_path = os.getcwd()
        self.build_path = None

    def copy_frontend_files(self):
        dest_dir = os.path.join(self.build_path, name, 'frontend')

        src_dir = os.path.join(self.root_path, 'frontend', 'dist')
        if not os.path.exists(src_dir):
            # Running from a sdist
            src_dir = os.path.join(self.root_path, 'qtoggleserver', 'frontend')

        # Remove frontend dir created by in-source symlink
        shutil.rmtree(dest_dir)
        shutil.copytree(src_dir, dest_dir)


class SdistCommand(sdist, UIMakeMixin):
    def __init__(self, *args, **kwargs):
        sdist.__init__(self, *args, **kwargs)
        UIMakeMixin.__init__(self)

    def run(self):
        self.build_path = os.path.join(self.root_path, self.distribution.get_fullname())

        sdist.run(self)

    def make_release_tree(self, base_dir, files):
        sdist.make_release_tree(self, base_dir, files)

        self.copy_frontend_files()


if bdist_wheel:
    class BdistWheelCommand(bdist_wheel, UIMakeMixin):
        def __init__(self, *args, **kwargs):
            bdist_wheel.__init__(self, *args, **kwargs)
            UIMakeMixin.__init__(self)

        def egg2dist(self, egginfo_path, distinfo_path):
            self.build_path = self.bdist_dir
            self.copy_frontend_files()

            bdist_wheel.egg2dist(self, egginfo_path, distinfo_path)

else:
    class BdistWheelCommand(Command):
        user_options = []

        def initialize_options(self):
            pass

        def finalize_options(self):
            pass

        def run(self):
            raise NotImplementedError()


class CleanCommand(Command):
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        os.system('rm -vrf ./build ./dist ./*.egg-info')


setup(
    name=name,
    version=version,

    description='A fully fledged qToggle Python implementation',

    author='Calin Crisan',
    author_email='ccrisan@gmail.com',

    license='Apache 2.0',

    packages=find_namespace_packages(include=name + '/*'),
    namespace_packages=['qtoggleserver'],

    install_requires=[
        'jinja2',
        'jsonpointer',
        'jsonschema',
        'pyhocon',
        'pyjwt',
        'pytz',
        'tornado',
    ],

    package_data={
        name: [
            'frontend/*.css',
            'frontend/*.js',
            'frontend/*.map',
            'frontend/font/*.*',
            'frontend/img/*.*',
            'frontend/html/*.*',
        ]
    },

    entry_points={
        'console_scripts': [
            'qtoggleserver=qtoggleserver.commands.server:execute',
            'qtoggleshell=qtoggleserver.commands.shell:execute'
        ],
    },

    cmdclass={
        'sdist': SdistCommand,
        'bdist_wheel': BdistWheelCommand,
        'clean': CleanCommand
    }
)
