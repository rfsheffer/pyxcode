# pyxcode 

This is a simple python package for parsing xcode projects, making edits, and re-exporting to the project.

## Usage
I created this project so I could parse a Visual Studio project (which is in a much friendlier format, just xml) and using all of the sources, defines, paths, and compile settings, along with an excludes list to remove certain windows only sources, export an Xcode project. This script is run on my CI which creates an xcode project and builds it on an OSX slave. This allows me to work in visual studio, and when I commit new changes and the Visual Studio project, an OSX build is also created by the CI. If OSX debugging is required, I can load up the xcode project and run it as is and debug.

```python
from pyxcode.project import XCodeProject

# Open your baseline project (contains all of the general xcode settings you want to use)
xproj = XCodeProject('path/myproject.xcodeproj')

# Add some preprocessor defines
xproj.add_preprocessor_defines('my_target', 'Debug', ['SOME_DEFINE'])

# Add a source file with some compile flags
xproj.add_source_file(src_file, 'my_target', compile_flags='-funsafe-math-optimizations -ffast-math')

# Lets add an LD flag for good measure to all of the configurations
for config_name in xproj.get_configuration_names():
    config = xproj.get_target_configuration('my_target', config_name)
    ld_flags = config['buildSettings']['OTHER_LDFLAGS']
    ld_flags.append('"-ObjC"')

# And export the project
xproj.export_project('path/my_new_project.xcodeproj')
```

## Thoughts
So why didn't I just use cmake and use an xcode generator? Well the VC Project to Cmake converters out there don't always get it the way I want or need, and fail, and require more of my time. With this package, and my own code to support it, issues rarely happen, and I don't have to worry about these other unmaintained projects breaking all the time. I suggest others to do the same, as nobody knows your project quite like... YOU!

## What you need
Ply package, just pip install ply