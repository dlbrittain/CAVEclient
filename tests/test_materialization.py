import pytest
import requests
from annotationframeworkclient import FrameworkClient
import os
from annotationframeworkclient import endpoints
import pandas as pd 
import responses
import pyarrow as pa
from urllib.parse import urlencode
from .conftest import test_info, TEST_LOCAL_SERVER, TEST_DATASTACK
 
def test_info_d(myclient):
    info = myclient.info.get_datastack_info()
    assert(info == test_info)

@responses.activate
def test_matclient(myclient):
    endpoints_mapping = endpoints.materialization_endpoints_v2
    mapping = {
        'me_server_address': TEST_LOCAL_SERVER,
        'datastack_name': TEST_DATASTACK,
        'table_name': test_info['synapse_table'],
        'version': 1
    }
    versionurl = endpoints_mapping['versions'].format_map(mapping)
    print(versionurl)
    responses.add(
        responses.GET,
        url=versionurl,
        json=[1],
        status=200
    )

    url = endpoints_mapping['simple_query'].format_map(mapping)
    query_d={'return_pyarrow': True,
        'split_positions': False}
    query_string = urlencode(query_d)
    url = url + "?" + query_string
    correct_query_data = {
        'filter_in_dict':{
            test_info['synapse_table']:{
                'pre_pt_root_id': [500]
            }
        },
        'filter_notin_dict':{
             test_info['synapse_table']:{
                'post_pt_root_id': [501]
            }
        },
        'filter_equal_dict':{
             test_info['synapse_table']:{
                'size': 100
            }
        },
        'offset':0,
        'limit':1000
    }
    df=pd.read_pickle('tests/test_data/synapse_query.pkl')
    
    context = pa.default_serialization_context()
    serialized = context.serialize(df)

    responses.add(
        responses.POST,
        url=url,
        body=serialized.to_buffer().to_pybytes(),
        headers={'content-type': 'x-application/pyarrow'},
        match=[
            responses.json_params_matcher(correct_query_data)
        ]
    )
  
    df=myclient.materialize.query_table(test_info['synapse_table'],
                                     filter_in_dict={'pre_pt_root_id': [500]},
                                     filter_out_dict={'post_pt_root_id': [501]},
                                     filter_equal_dict={'size':100},
                                     limit=1000,
                                     offset=0)
    assert(len(df)==1000)
    assert(type(df)==pd.DataFrame)