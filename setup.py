import platform

if platform.system() != 'Windows':
    # Unfortunately, this stalled on Windows when I tested it...
    import ez_setup
    ez_setup.use_setuptools()

from setuptools import setup

requirements = ['lxml',
                'numpy',
                'pandas',
                'seaborn',
                'sphinx-argparse',
                ]

setup(
    name='pygcam',
    version='1.0a3',
    description='Python 2.7 library and scripts for interfacing with GCAM',

    packages=['pygcam'],
    entry_points={'console_scripts': ['gt = pygcam.tool:main']},
    install_requires=requirements,
    include_package_data = True,

    url='https://bitbucket.org/plevin/pygcam',
    # download_url='ssh://git@bitbucket.org/plevin/pygcam.git',
    download_url='https://plevin@bitbucket.org/plevin/pygcam.git',
    license='MIT License',
    author='Richard Plevin',
    author_email='rich@plevin.com',

    classifiers=[
          'Development Status :: 3 - Alpha',
          'License :: OSI Approved :: MIT License',
          'Intended Audience :: Science/Research',
          ],

    zip_safe=True,

    # TBD
    # test_suite="string identifying test module etc."

)
