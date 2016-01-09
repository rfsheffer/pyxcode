import os
import ply.lex as lex
import collections
import hashlib

__author__ = "Ryan Sheffer"
__credits__ = [__author__]
__version__ = "1.0"


class XCodeProject:
    """
    Xcode Project parser, modifier, and exporter
    """

    class Lex(object):
        """
        Lexicographical Analysis of the xcode project file
        """
        def __init__(self):
            self.comment_open = False
            self.string = ''
            self.string_open = False

        # All important Xcode project file tokens
        tokens = (
            'SPACE'
            'LCOMMENT',
            'RCOMMENT',
            'LPAREN',
            'RPAREN',
            'COMMENT',
            'SEMICOLON',
            'RBRACE',
            'LBRACE',
            'COMMA',
            'EQUALS',
            'WORD',
            'QUOTE',
            'QUOTE_LITERAL',
            'NEWLINE_LITERAL'
        )

        def parse_project(self, project_path):
            """
            Parses an Xcode project lexicographically so it can be further processed
            :param project_path: The project path of the project to parse
            :return: The lexer containing the list of the files structure
            """
            # Build the lexer
            lexer = lex.lex(module=self)

            fp = open(project_path, 'rb')
            if fp is None:
                raise Exception('Could not open Xcode Project at path ' + project_path)

            fp_bytes = fp.read()
            fp.close()

            # Give the lexer our xcode project
            lexer.input(fp_bytes)

            return lexer

        def update_string(self, value):
            if self.string_open:
                self.string += value
                return True
            return False

        def in_comment(self):
            return self.comment_open

        def t_SPACE(self, t):
            r'\s'
            if self.string_open:
                self.update_string(t.value)
            return

        def t_QUOTE(self, t):
            r'"'
            if self.in_comment():
                return
            if not self.string_open:
                self.string = '"'
                self.string_open = True
                return
            else:
                self.string += '"'
                self.string_open = False
                t.value = self.string
                t.type = 'WORD'
            return t

        def t_QUOTE_LITERAL(self, t):
            r'\\"'
            if self.in_comment() or self.update_string(t.value):
                return

            t.type = 'WORD'
            return t

        def t_NEWLINE_LITERAL(self, t):
            r'\\n'
            self.update_string(t.value)
            return

        def general_op(self, t):
            if self.in_comment() or self.update_string(t.value):
                return
            return t

        def t_SEMICOLON(self, t):
            r';'
            return self.general_op(t)

        def t_LBRACE(self, t):
            r'\{'
            return self.general_op(t)

        def t_RBRACE(self, t):
            r'\}'
            return self.general_op(t)

        def t_COMMA(self, t):
            r','
            return self.general_op(t)

        def t_LPAREN(self, t):
            r'\('
            return self.general_op(t)

        def t_RPAREN(self, t):
            r'\)'
            return self.general_op(t)

        def t_EQUALS(self, t):
            r'='
            return self.general_op(t)

        def t_LCOMMENT(self, t):
            r'/\*'
            self.comment_open = True
            return

        def t_RCOMMENT(self, t):
            r'\*/'
            self.comment_open = False
            return

        def t_COMMENT(self, t):
            r'//.*'
            return

        def t_WORD(self, t):
            r"[!|#-'|\*|\+|\--:|<|>-\[|\]-z|\||~]+"
            return self.general_op(t)

        # A string containing ignored characters (new line literal is handled above)
        t_ignore = '\t\n'

        # Error handling rule
        def t_error(self, t):
            print("Illegal character '%s'" % t.value[0])
            t.lexer.skip(1)

    def __init__(self, project_path):
        """
        Init
        :param project_path: The project folder path
        """
        self.proj_obj = collections.OrderedDict()

        project_path = os.path.join(project_path, 'project.pbxproj')
        lexer = self.Lex().parse_project(project_path)
        self.parse_lex(lexer)

        root_id = self.proj_obj['rootObject']

        # Root Project Object
        self.root_object = self.get_isa(root_id)

        # The root group (editor file layout)
        self.main_group = self.get_isa(self.root_object['mainGroup'])

    def parse_lex(self, lexer):
        """
        Parses the xcode project which has been lexigraphically analyized by ply
        :param lexer: the ply lexer object
        """
        finished = False

        obj_stack = []
        cur_obj = None  # name of current object

        while not finished:
            tok = lexer.token()
            if not tok:
                break      # No more input

            if tok.type == 'LBRACE':
                new_obj = collections.OrderedDict()
                if len(obj_stack) != 0:
                    obj_stack[0][cur_obj] = new_obj
                obj_stack.insert(0, new_obj)
                cur_obj = None
            elif tok.type == 'RBRACE':
                obj = obj_stack.pop(0)
                if len(obj_stack) == 0:
                    finished = True
                    self.proj_obj = obj
            elif tok.type == 'LPAREN':
                new_obj = []
                obj_stack[0][cur_obj] = new_obj
                obj_stack.insert(0, new_obj)
                cur_obj = None
            elif tok.type == 'RPAREN':
                if cur_obj is not None:
                    obj_stack[0].append(cur_obj)
                    cur_obj = None
                obj_stack.pop(0)
            elif tok.type == 'SEMICOLON':
                pass  # we don't really care
            elif tok.type == 'COMMA':
                obj_stack[0].append(cur_obj)
                cur_obj = None
            elif tok.type == 'EQUALS':
                if not cur_obj:
                    raise Exception('Invalid assignment operation in xcode project!')
            elif tok.type == 'WORD':
                if not cur_obj:
                    cur_obj = tok.value
                else:
                    obj_stack[0][cur_obj] = tok.value
                    cur_obj = None

    def get_isa(self, isa_id):
        return self.proj_obj['objects'][isa_id]

    def add_isa(self, isa_id, isa):
        if isa_id in self.proj_obj['objects']:
            raise Exception('ISA ID Collision!')
        self.proj_obj['objects'][isa_id] = isa

    def _get_config_from_list(self, build_config_list, config_name):
        build_configurations = build_config_list['buildConfigurations']
        for config_id in build_configurations:
            config = self.get_isa(config_id)
            if config['name'] == config_name:
                return config
        return None

    def get_configuration(self, config_name):
        """
        Gets a configuration. Note: These are configurations global to all targets.
        :param config_name: The name of the configuration to get
        :return: configration
        """
        build_config_list = self.get_isa(self.root_object['buildConfigurationList'])
        return self._get_config_from_list(build_config_list, config_name)

    def get_configuration_names(self):
        """
        :return: The configuration names
        """
        config_names = []
        build_config_list = self.get_isa(self.root_object['buildConfigurationList'])
        build_configurations = build_config_list['buildConfigurations']
        for config_id in build_configurations:
            config = self.get_isa(config_id)
            config_names.append(config['name'])
        return config_names

    def get_target(self, target_name):
        """
        Gets a target by name
        :param target_name: target name
        :return: the target
        """
        for target_id in self.root_object['targets']:
            target = self.get_isa(target_id)
            if target['name'] == target_name:
                return target
        return None

    def get_target_configuration(self, target_name, config_name):
        """
        Gets a targets configuration
        :param config_name: Configuration name
        :param target_name: Target name
        :return: target configuration
        """
        target = self.get_target(target_name)
        if target is not None:
            build_config_list = self.get_isa(target['buildConfigurationList'])
            return self._get_config_from_list(build_config_list, config_name)
        return None

    def get_target_names(self):
        """
        :return: The target names
        """
        target_names = []
        for target_id in self.root_object['targets']:
            target = self.get_isa(target_id)
            target_names.append(target['name'])
        return target_names

    @staticmethod
    def split_into_file_groups(file_path):
        return [p for p in file_path.split(os.path.sep) if p != '..']

    @staticmethod
    def create_new_group(group_name):
        group = collections.OrderedDict()
        group['isa'] = 'PBXGroup'
        group['children'] = []
        group['name'] = group_name
        group['sourceTree'] = '"<group>"'
        return group

    def create_groups_for_file(self, file_path, file_ref_id):
        """
        With a file path, creates an appropriate tree of groups and adds the file reference ID
        :param file_path: the file path
        :param file_ref_id: the file reference id
        """
        group_list = self.split_into_file_groups(file_path)
        cur_group = self.main_group
        group_id_str = ''
        for group_name in group_list:
            if group_list[-1] == group_name:  # at the end, append the file reference to the children
                cur_group['children'].append(file_ref_id)
                break

            group_child = None
            for child_id in cur_group['children']:
                child = self.get_isa(child_id)
                if child.get('name', '') == group_name:
                    group_child = child
                    break
            group_id_str += group_name
            if group_child is None:
                group_child = self.create_new_group(group_name)
                new_group_id = self.get_unique_id(group_id_str + 'PBXGroup')
                self.add_isa(new_group_id, group_child)
                cur_group['children'].insert(0, new_group_id)
            cur_group = group_child

    @staticmethod
    def is_valid_source_tree(source_tree):
        """
        Checks for valid source tree id
        :param source_tree: source tree id string
        :return: True if valid source tree
        """
        return source_tree in ['BUILT_PRODUCTS_DIR', 'SDKROOT', '<group>']

    @staticmethod
    def get_unique_id(unique_path):
        """
        Returns an xcode compatible hash string for global IDs
        :param unique_path: A unique name or path
        :return: The xcode compatible global unique id
        """
        m = hashlib.md5()
        m.update(unique_path)
        return m.hexdigest().upper()

    def add_source_file(self, file_path, target_name, source_tree='<group>', compile_flags=''):
        """
        Adds a source file to the project tree
        :param file_path: The source file path relative to the source_tree
        :param target_name: The target to add sources to
        :param source_tree: The origin of the path
        :param compile_flags: Compiler flags string
        """
        if not self.is_valid_source_tree(source_tree):
            print('Invalid source tree trying to add source {}!'.format(file_path))
            return

        target = self.get_target(target_name)
        if target is None:
            print('Invalid target ({}) for source file!'.format(target_name))
            return

        pbx_build_file_id = self.get_unique_id(file_path + 'PBXBuildFile')
        pbx_file_ref_id = self.get_unique_id(file_path)

        # Add build entry (extra information for building the file)
        settings = collections.OrderedDict(COMPILER_FLAGS='"{}"'.format(compile_flags))
        pbx_build_entry = collections.OrderedDict()
        pbx_build_entry['isa'] = 'PBXBuildFile'
        pbx_build_entry['fileRef'] = pbx_file_ref_id
        pbx_build_entry['settings'] = settings

        # Add file reference
        pbx_file_entry = collections.OrderedDict()
        pbx_file_entry['isa'] = 'PBXFileReference'
        pbx_file_entry['fileEncoding'] = '4'
        pbx_file_entry['name'] = os.path.basename(file_path)
        pbx_file_entry['path'] = file_path
        pbx_file_entry['sourceTree'] = '"{}"'.format(source_tree)

        self.add_isa(pbx_build_file_id, pbx_build_entry)
        self.add_isa(pbx_file_ref_id, pbx_file_entry)

        # Add to target sources
        for build_phase_id in target['buildPhases']:
            build_phase = self.get_isa(build_phase_id)
            if build_phase['isa'] == 'PBXSourcesBuildPhase':
                build_phase['files'].append(pbx_build_file_id)
                break

        # Now we need to add the file to the appropriate group
        self.create_groups_for_file(file_path, pbx_file_ref_id)

    def add_search_paths(self, target_name, paths):
        """
        Adds header search paths to a project target
        :param target_name: The target
        :param paths: A list of paths
        """
        for config_name in self.get_configuration_names():
            config = self.get_target_configuration(target_name, config_name)
            if 'HEADER_SEARCH_PATHS' not in config['buildSettings']:
                config['buildSettings']['HEADER_SEARCH_PATHS'] = []
            config_search_paths = config['buildSettings']['HEADER_SEARCH_PATHS']
            for path in paths:
                if path not in config_search_paths:
                    config_search_paths.append(path)

    def add_preprocessor_defines(self, target_name, config_name, defines):
        """
        Adds pre-processor defines to a project target configuration
        :param target_name: The target to write to
        :param config_name: The configuration to write to
        :param defines: The defines to add (a list)
        """
        config = self.get_target_configuration(target_name, config_name)
        if 'GCC_PREPROCESSOR_DEFINITIONS' not in config['buildSettings']:
            config['buildSettings']['GCC_PREPROCESSOR_DEFINITIONS'] = []
        config_defines = config['buildSettings']['GCC_PREPROCESSOR_DEFINITIONS']
        for define in defines:
            if define not in config_defines:
                define = define if '=' not in define else '"{}"'.format(define)
                config_defines.append(define)

    class Writer:
        """
        Helper class for writing out the xcode project object to a plist structured text file
        """
        def __init__(self, project_file):
            self.indent = 1
            self.condensed = False
            self.proj_file = project_file
            self.proj_file.write('// !$*UTF8*$!\n{\n')

        def write_indent(self):
            if not self.condensed:
                self.proj_file.write('\t' * self.indent)

        def write_newline(self):
            if not self.condensed:
                self.proj_file.write('\n')

        def write_var(self, k, v):
            self.write_indent()
            self.proj_file.write('%s = %s; ' % (k, v))
            self.write_newline()

        def write_dict(self, k):
            self.write_indent()
            self.proj_file.write('{} = {{ '.format(k))
            self.write_newline()
            self.indent += 1

        def end_dict(self):
            self.indent -= 1
            self.write_indent()
            self.proj_file.write('}; ')
            self.write_newline()

        def write_list(self, k):
            self.write_indent()
            self.proj_file.write('{} = ( '.format(k))
            self.write_newline()
            self.indent += 1

        def write_list_entry(self, v):
            self.write_indent()
            self.proj_file.write('{}, '.format(v))
            self.write_newline()

        def end_list(self):
            self.indent -= 1
            self.write_indent()
            self.proj_file.write('); ')
            self.write_newline()

        def close(self):
            self.proj_file.write('}\n')
            self.proj_file.close()

    @staticmethod
    def recursive_write(obj, writer):
        """
        Recursively writes an xcode project structured object (dicts and lists) with a writer
        :param obj: The Xcode object to write (a json like object from the xcode import process)
        :param writer: The helper writer class which writes to xcode project plist syntax
        """
        if type(obj) is list:
            for v in obj:
                writer.write_list_entry(v)
        else:
            for k, v in obj.items():
                if type(v) is collections.OrderedDict:
                    condensed = False
                    if v.get('isa', '') in ['PBXBuildFile', 'PBXFileReference']:
                        condensed = True
                        writer.write_indent()
                        writer.condensed = True
                    writer.write_dict(k)
                    XCodeProject.recursive_write(v, writer)
                    writer.end_dict()
                    if condensed:
                        writer.condensed = False
                        writer.write_newline()
                elif type(v) is list:
                    writer.write_list(k)
                    XCodeProject.recursive_write(v, writer)
                    writer.end_list()
                else:
                    if type(v) is not str:
                        raise Exception('Bad variable write! Trying to write {}!'.format(type(v)))
                    writer.write_var(k, v)

    def export_project(self, dest):
        """
        Exports the project to the desired xcode .xcodeproj path
        :param dest: The destination xcode .xcodeproj path
        """
        if not os.path.isdir(dest):
            os.makedirs(dest)

        with open(os.path.join(dest, 'project.pbxproj'), 'wb') as proj_file:
            writer = self.Writer(proj_file)
            self.recursive_write(self.proj_obj, writer)
            writer.close()
