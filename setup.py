from distutils.core import setup

setup(
    name='pygcam',
    description='Python library for interfacing with GCAM',
    version='0.1.0',
    packages=['pygcam'],
    url='https://bitbucket.org/plevin/pygcam',
    download_url='ssh://git@bitbucket.org/plevin/pygcam.git',
    license='',
    author='Richard Plevin',
    author_email='rich@plevin.com',
    requires=['lxml'],
    scripts=['bin/gcamProtectLand'],
    classifiers=[
          'Development Status :: 2 - Pre-Alpha',
          'License :: OSI Approved :: MIT License',
          'Intended Audience :: Science/Research',
          ],
)
