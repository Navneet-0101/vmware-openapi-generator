import os
import re
import collections
from lib import utils
from lib.path_processing import PathProcessing


class ApiOpenapiPathProcessing(PathProcessing):

    def __init__(self):
        pass

    def process_output(
            self,
            path_dict,
            type_dict,
            output_dir,
            output_filename,
            gen_unique_op_id):
        reqBody = {}
        description_map = utils.load_description()
        self.remove_com_vmware_from_dict(path_dict)
        if gen_unique_op_id:
            self.create_unique_op_ids(path_dict)
        self.remove_query_params(path_dict)
        self.remove_com_vmware_from_dict(type_dict)
        if 'requestBodies' in type_dict:
            self.remove_com_vmware_from_dict(type_dict['requestBodies'])
            reqBody = collections.OrderedDict(
                sorted(type_dict['requestBodies'].items()))
        swagger_template = {
            'openapi': '3.0.0',
            'info': {
                'description': description_map.get(
                    output_filename,
                    ''),
                'title': utils.remove_curly_braces(output_filename),
                'version': '2.0.0'},
            'paths': collections.OrderedDict(
                sorted(
                    path_dict.items())),
            'components': {
                'requestBodies': reqBody}}
        if 'requestBodies' in type_dict:
            del type_dict['requestBodies']
        swagger_template['components']['schemas'] = collections.OrderedDict(
            sorted(type_dict.items()))

        if not os.path.exists(output_dir):
            os.mkdir(output_dir)

        utils.write_json_data_to_file(
            output_dir +
            os.path.sep +
            '/api' +
            "_" +
            utils.remove_curly_braces(output_filename) +
            '.json',
            swagger_template)

    def remove_query_params(self, path_dict):
        """
        Swagger/Open API specification prohibits appending query parameter to the request mapping path.

        Duplicate paths in Open API :
            Since request mapping paths are keys in the Open Api JSON, there is no scope of duplicate request mapping paths

        Partial Duplicates in Open API: APIs which have same request mapping paths but different HTTP Operations.

        Such Operations can be merged together under one path
            eg: Consider these two paths
                /A/B/C : [POST]
                /A/B/C : [PUT]
            On merging these, the new path would look like:
            /A/B/C : [POST, PUT]

        Absolute Duplicates in Open API: APIs which have same request mapping path and HTTP Operation(s)
            eg: Consider two paths
                /A/B/C : [POST, PUT]
                /A/B/C : [PUT]
        Such paths can not co-exist in the same Open API definition.

        This method attempts to move query parameters from request mapping url to parameter section.

        There are 4 possibilities which may arise on removing the query parameter from request mapping path:

        1. Absolute Duplicate
            The combination of path and the HTTP Operation Type(s)are same to that of an existing path:
            Handling Such APIs is Out of Scope of this method. Such APIs will appear in the Open API definition unchanged.
            Example :
                    /com/vmware/cis/session?~action=get : [POST]
                    /com/vmware/cis/session : [POST, DELETE]
        2. Partial Duplicate:
            The Paths are same but the HTTP operations are Unique:
            Handling Such APIs involves adding the Operations of the new duplicate path to that of the existing path
            Example :
                    /cis/tasks/{task}?action=cancel : [POST]
                    /cis/tasks/{task} : [GET]
        3. New Unique Path:
            The new path is not a duplicate of any path in the current Open API definition.
            The Path is changed to new path by trimming off the path post '?'

        4. The duplicate paths are formed when two paths with QueryParameters are fixed
            All the scenarios under 1, 2 and 3 are possible.
            Example :
                    /com/vmware/cis/tagging/tag-association/id:{tag_id}?~action=detach-tag-from-multiple-objects
                    /com/vmware/cis/tagging/tag-association/id:{tag_id}?~action=list-attached-objects
        :param path_dict:
        """
        paths_to_delete = []
        for old_path in list(path_dict.keys()):
            http_operations = path_dict[old_path]
            if '?' in old_path:
                paths_array = re.split(r'\?', old_path)
                new_path = paths_array[0]

                query_param = []
                for query_parameter in paths_array[1].split('&'):
                    key_value = query_parameter.split('=')
                    q_param = {
                        'name': key_value[0],
                        'in': 'query',
                        'description': key_value[0] + '=' + key_value[1],
                        'required': True}
                    q_param['schema'] = {}
                    q_param['schema']['type'] = 'string'
                    q_param['schema']['enum'] = [key_value[1]]
                    query_param.append(q_param)

                if new_path in path_dict:
                    new_path_operations = path_dict[new_path].keys()
                    path_operations = http_operations.keys()
                    if len(set(path_operations).intersection(
                            new_path_operations)) < 1:
                        for http_method, operation_dict in http_operations.items():
                            operation_dict['parameters'] = operation_dict['parameters'] + query_param
                        path_dict[new_path] = self.merge_dictionaries(
                            http_operations, path_dict[new_path])
                        paths_to_delete.append(old_path)
                else:
                    for http_method, operation_dict in http_operations.items():
                        operation_dict['parameters'].append(q_param)
                    path_dict[new_path] = path_dict.pop(old_path)
        for path in paths_to_delete:
            del path_dict[path]
