from distutils.core import setup

setup(
    name='webpage2html',
    version='0.3.7',

    author='Wenlei Zhu',
    author_email='i@ztrix.me',
    url='https://github.com/zTrix/webpage2html',

    license='LICENSE.txt',
    keywords="webpage html convert",
    description='Save/convert web pages to a single editable html file',
    long_description='View  for project description and usage',


    py_modules=['webpage2html'],

    # Refers to test/test.py
    test_suite='test.test',

    entry_points={
        'console_scripts': [
            'webpage2html=webpage2html:main'
        ]
    },
    classifiers=[

    ],
)
