import pytest


@pytest.fixture
def manifest():
    return {'version': 1, 'atlas_size': 8, 'padding': 2,
            'palette': [[i, i, i] for i in range(256)], 'pages': ['page.png'],
            'sprites': [{'name': 'TROOA1', 'page': 0, 'x': 0, 'y': 0,
                         'width': 4, 'height': 4, 'left_offset': 0, 'top_offset': 0}]}
