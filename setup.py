from setuptools import setup

REQUIREMENTS = [
    'django',
]

TEST_REQUIREMENTS = REQUIREMENTS + [
    'mock',
]

setup(
    name="django-wizard",
    version='0.1.4',
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
        "Development Status :: 3 - Alpha",
        "Environment :: Web Environment",
        "Framework :: Django",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Topic :: Software Development",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
    ],
)
