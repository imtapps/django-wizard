import os
import re
from distutils.core import Command, setup

REQUIREMENTS = [
    'django',
]

TEST_REQUIREMENTS = [
    'mock',
    'django-jenkins',
    'pep8',
    'pyflakes',
]

def do_setup():
    setup(
        name="django-wizard",
        version='0.2.4',
        author="Matthew J. Morrison",
        author_email="mattjmorrison@mattjmorrison.com",
        description="A wizard that helps to control page flow.",
        long_description=open('README.txt', 'r').read(),
        url="https://github.com/imtapps/django-wizard",
        packages=("wizard",),
        install_requires=REQUIREMENTS,
        tests_require=TEST_REQUIREMENTS,
        test_suite='runtests.runtests',
        zip_safe=False,
        classifiers = [
            "Development Status :: 5 - Production/Stable",
            "Environment :: Web Environment",
            "Framework :: Django",
            "Intended Audience :: Developers",
            "License :: OSI Approved :: BSD License",
            "Operating System :: OS Independent",
            "Programming Language :: Python",
            "Topic :: Software Development",
            "Topic :: Software Development :: Libraries :: Application Frameworks",
        ],
        cmdclass={
            'install_dev': InstallDependencies,
            'uninstall_dev': UninstallDependencies,
        },
    )

class PipDependencies(Command):
    pip_command = ""
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def get_all_dependencies(self):
        """
        replace all > or < in the dependencies so the system does not
        try to redirect stdin or stdout from/to a file.
        """
        command_line_deps = ' '.join(REQUIREMENTS + TEST_REQUIREMENTS)
        return re.sub(re.compile(r'([<>])'), r'\\\1', command_line_deps)

    def run(self):
        os.system("pip %s %s" % (self.pip_command, self.get_all_dependencies()))

class InstallDependencies(PipDependencies):
    pip_command = 'install'

class UninstallDependencies(PipDependencies):
    pip_command = 'uninstall'

if __name__ == '__main__':
    do_setup()