from google.appengine.ext import vendor
import os
import platform

vendor.add(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'lib'))

def patch(module):
    def decorate(func):
        setattr(module, func.func_name, func)
        return func
    return decorate

@patch(platform)
def platform(bool):
    return 'AppEngine'
