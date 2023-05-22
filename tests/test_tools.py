import pytest


def test_get_slow_match_jjwxc(client):
    response = client.get('/tools/slow-match/jjwxc')
    assert response.status_code == 200
    assert '慢速匹配晋江文学城字体'.encode('utf-8') in response.data


@pytest.mark.parametrize('font_name', (
        'jjwxcfont_2o8eo',
))
def test_post_slow_match_jjwxc(client, font_name):
    response = client.post(
        '/tools/slow-match/jjwxc',
        data={
            "jjwxc_font_name": font_name,
            "std_font": "SourceHanSansSC-Normal",
            "guest_range": "jjwxc"
        })
    assert response.status_code == 200


@pytest.mark.parametrize('font_name', (
        'jjwxcfont_3o8eo',
))
def test_post_slow_match_jjwxc_404(client, font_name):
    response = client.post(
        '/tools/slow-match/jjwxc',
        data={
            "jjwxc_font_name": font_name,
            "std_font": "SourceHanSansSC-Normal",
            "guest_range": "jjwxc"
        })
    assert response.status_code == 404
