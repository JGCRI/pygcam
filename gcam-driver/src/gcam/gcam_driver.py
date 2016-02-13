#!/bin/env python
"""GCAM driver

  usage:  gcam_driver.py <configfile>

  This program will run the GCAM automation system using the configuration details
  from the configuration file described on the command line.  The configuraiton
  file format and contents are described in the GCAM Automation Users' Guide.
  
""" 

import sys
import re
import threading

def gcam_parse(cfgfile_name):
    """Parse the configuraiton file for the GCAM driver."""

    ## initialize the structures that will receive the data we are
    ## parsing from the file
    capability_table = {}
    module_list      = []

    ## cfgfile_name is a filename
    with open(cfgfile_name,"r") as cfgfile: 
        section   = None
        module    = None
        sectnpat  = re.compile(r'\[(.+)\]')
        keyvalpat = re.compile(r'(.+)=(.+)')

        for line in cfgfile:
            line = line.lstrip()        # remove leading whitespace

            ## check for comments and blank lines.  A line is a comment if
            ## the first non-whitespace character is a '#'
            if(line == "" or line[0] == '#'):
                continue

            ## check for section header.  Section headers appear in square brackets:  [gcam_module]
            sectnmatch = sectnpat.match(line)
            if sectnmatch:
                section = sectnmatch.group(1)
                print "parser starting section:  %s" % section
                
                if not section.lower()=="global":
                    ## Section header starts a new module
                    ## create the new module:  the section name is the module class
                    ## TODO: is the input from the config file trusted enough to do it this way?
                    modcreate = "%s(capability_table)" % section
                    print "modcreate statement:  %s\n" % modcreate
                    module = eval(modcreate)
                else:
                    ## This is kind of a wart because I want to call
                    ## the section "global", but I don't want to have
                    ## a module called "global".
                    module = GlobalParamsModule(capability_table)
                    
                module_list.append(module) 
                continue        # nothing further to do for a section header line

            ## If we get this far, we have a nonblank line that is not a
            ## comment or a section header.  We had better be in a section
            ## by now, or the config is malformed.
            if section==None:
                raise RuntimeError("Malformed config file:  doesn't open with a section header.")

            kvmatch = keyvalpat.match(line)
            if not kvmatch:
                raise RuntimeError("Malformed line in config file:\n%s"%line)

            key = kvmatch.group(1).lstrip().rstrip()
            val = kvmatch.group(2).lstrip().rstrip()

            print "parser got key= %s\tval= %s" % (key, val)

            module.addparam(key, val)

        ## end of loop over config file lines
    ## end of with block:  config file will be closed
            
    ## close out the parameter processing for all modules in the list
    for module in module_list:
        module.finalize_parsing()

    return (module_list, capability_table)
## end of gcam_parse

if __name__ == "__main__":
    import sys
    import os

    ## arrange so that when run from the top-level directory we still find
    ## the modules we want to load.
    sys.path.append(os.getcwd()+'/src')
    from gcam.modules import *

    try:
        (modlist, cap_table) = gcam_parse(sys.argv[1])
    except IndexError:
        print __doc__
        sys.exit(0)

    ## We will look up "global" in the cap_table and process any
    ## global parameters here, but in the current version we don't
    ## have any global parameters to process, so skip it.

    threads = []
    
    for module in modlist:
        print "running %s" % module.__class__
        threads.append(module.run())

    ## Wait for all threads to complete before printing end message.
    for thread in threads:
        thread.join()

    ## Check to see if any of the modules failed
    fail = 0
    for module in modlist:
        if module.status != 1:
            print 'Module %s returned failure status\n' % str(module.__class__)
            fail += 1

    if fail == 0:
        print '\n****************All modules completed successfully.'
    else:
        print '\n****************%d modules failed.' % fail
        
    print "\nFIN."
    
