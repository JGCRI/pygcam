from distutils.core import setup
from glob import glob

requirements = ['lxml',
                'numpy',
                'pandas']

scripts = glob('bin/*.py')

setup(
    name='pygcam',
    description='Python 2.7 library and scripts for interfacing with GCAM',
    version='0.1.0',
    packages=['pygcam'],
    url='https://bitbucket.org/plevin/pygcam',
    download_url='ssh://git@bitbucket.org/plevin/pygcam.git',
    license='MIT License',
    author='Richard Plevin',
    author_email='rich@plevin.com',
    requires=requirements,
    scripts=scripts,
    classifiers=[
          'Development Status :: 2 - Pre-Alpha',
          'License :: OSI Approved :: MIT License',
          'Intended Audience :: Science/Research',
          ],
)
