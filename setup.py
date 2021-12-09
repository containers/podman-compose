import os
from setuptools import setup

try:
    readme = open(os.path.join(os.path.dirname(__file__), 'README.md')).read()
except:
    readme = ''

setup(
    name='podman-compose',
    description="A script to run docker-compose.yml using podman",
    long_description=readme,
    long_description_content_type='text/markdown',
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "Development Status :: 3 - Alpha",
        "Topic :: Software Development :: Build Tools",
        "License :: OSI Approved :: GNU General Public License v2 (GPLv2)",
    ],
    keywords='podman, podman-compose',
    author='Muayyad Alsadi',
    author_email='alsadi@gmail.com',
    url='https://github.com/containers/podman-compose',
    py_modules=['podman_compose'],
    entry_points={
        'console_scripts': [
            'podman-compose = podman_compose:main'
        ]
    },
    include_package_data=True,
    license='GPL-2.0-only',
    install_requires=[
        'pyyaml',
        'python-dotenv',
    ],
    # test_suite='tests',
    # tests_require=[
    #     'coverage',
    #     'pytest-cov',
    #     'pytest',
    #     'tox',
    # ]
)
