import os
import six
from lib import utils
from lib.url_processing import urlProcessing
from lib.api_endpoint.oas3.api_metamodel2openapi import apiMetamodel2Openapi  
from lib.api_endpoint.swagger2.api_metamodel2swagger import apiMetamodel2Swagger  
from lib.api_endpoint.oas3.api_openapi_final_path_processing import apiOpenapiPathProcessing
from lib.api_endpoint.swagger2.api_swagger_final_path_processing import apiSwaggerPathProcessing

api_openapi_fpp = apiOpenapiPathProcessing()
api_swagg_fpp = apiSwaggerPathProcessing()
openapi = apiMetamodel2Openapi()
swagg = apiMetamodel2Swagger()

class apiUrlProcessing(urlProcessing):

    def __init__(self):
        pass

    def process_service_urls(self,package_name, service_urls, output_dir, structure_dict, enum_dict,
                            service_dict, service_url_dict, error_map, rest_navigation_url, enable_filtering
                            , spec, gen_unique_op_id):

        print('processing package ' + package_name + os.linesep)
        type_dict = {}
        path_list = []
        for service_url in service_urls:
            service_name, service_end_point = service_url_dict.get(service_url, None)
            service_info = service_dict.get(service_name, None)
            if service_info is None:
                continue
            if utils.is_filtered(service_info.metadata, enable_filtering):
                continue
            for operation_id, operation_info in service_info.operations.items():
                method, url = self.api_get_url_and_method(operation_info.metadata)

                # check for query parameters
                if 'params' in operation_info.metadata[method].elements:
                    element_value = operation_info.metadata[method].elements['params']
                    params="&".join(element_value.list_value)
                    url = url + '?' + params
                    
                    if spec == '2':
                        path = swagg.get_path(operation_info, method, url, service_name, type_dict, structure_dict, enum_dict,
                                    operation_id, error_map, enable_filtering)
                    if spec == '3':
                        path = openapi.get_path(operation_info, method, url, service_name, type_dict, structure_dict, enum_dict,
                                    operation_id, error_map, enable_filtering)

                    path_list.append(path)
            continue
            
        path_dict = self.convert_path_list_to_path_map(path_list)
        self.cleanup(path_dict=path_dict, type_dict=type_dict)

        if spec == '2':
            api_swagg_fpp.process_output(path_dict, type_dict, output_dir, package_name, gen_unique_op_id)
        if spec == '3':
            api_openapi_fpp.process_output(path_dict, type_dict, output_dir, package_name, gen_unique_op_id)

    def api_get_url_and_method(self,metadata):
        for method in metadata.keys():
            if method in ['POST', 'GET', 'DELETE', 'PUT', 'PATCH']: 
                url_path = metadata[method].elements["path"].string_value
                return method, url_path

