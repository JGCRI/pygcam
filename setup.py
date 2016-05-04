import ez_setup
ez_setup.use_setuptools()

from setuptools import setup #, find_packages

requirements = ['lxml',
                'numpy',
                'pandas',
                'seaborn',
                ]

# Apparently 'bin' should be in pygcam/bin, not pygcam/pygcam/bin
# "When we install the package, setuptools will copy the script to
# our PATH and make it available for general use."
# scripts = ['bin/gcamtool.py', 'bin/gt.cmd']

setup(
    name='pygcam',
    version='0.1a1',
    description='Python 2.7 library and scripts for interfacing with GCAM',

    packages=['pygcam'],
    entry_points={'console_scripts': ['gt = pygcam.tool:main']},
    install_requires=requirements,
    include_package_data = True,

    # Obviated by entry_points, which creates gt on Linux/Mac and gt.exe on Windows
    # scripts=scripts,

    url='https://bitbucket.org/plevin/pygcam',
    download_url='ssh://git@bitbucket.org/plevin/pygcam.git',
    license='MIT License',
    author='Richard Plevin',
    author_email='rich@plevin.com',

    classifiers=[
          'Development Status :: 2 - Pre-Alpha',
          'License :: OSI Approved :: MIT License',
          'Intended Audience :: Science/Research',
          ],

    zip_safe=True,

    # TBD
    # test_suite="string identifying test module etc."

)
