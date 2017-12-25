# Module to connect tassphoto.com API Json methods

import urllib.error  # исключение, для получения ситуаций с недоступностью сервиса или изменения его формата
from json import loads as json_loads
from urllib.request import urlopen as request_open

url_templates = {
    'by_id_url': 'http://msk-oft-app01:8080/photos/byid/{0}',
    'by_id_ext_url': 'http://msk-oft-app01:8080/photos/extbyid/{0}',
    'by_unique_id': 'http://msk-oft-app01:8080/photos/byfixid/{0}',
    'by_unique_ext_id': 'http://msk-oft-app01:8080/photos/extbyfixid/{0}'
}

def get_photo_by_id(photo_id):
    pass


def get_photo_by_id_ext(photo_id):
    pass


def get_item_by_original_unique_number(number):
    if number is not None:
        return get_items_by_url(url_templates['by_unique_id'].format(number))
    else:
        return None


def get_item_by_original_unique_number_ext(number):
    if number is not None:
        return get_items_by_url(url_templates['by_unique_ext_id'].format(number))
    else:
        return None


def get_items_by_url(url):
    """ Соединение с сервисом tassphoto.com и получение информации об уже добавленной фото
    :param url: ссылка для получения информации о фото
    :return: объект с информацией о фото на сайте
    """
    try:
        with request_open(url) as service_response:
            if service_response is not None:
                items = json_loads(service_response.read().decode('utf-8'))

                if 'data' in items and items['data']:
                    if isinstance(items['data'], list):
                        return items['data']
                    elif isinstance(items['data'], dict):
                        return [].extend(items['data'])
                    else:
                        raise ValueError("Wrong object in response: {}".format(str(items['data'])))
                else:
                    return None

    except urllib.error.HTTPError as http_error:
        raise(SystemError("Request error, code: {}, message: {}".format(http_error.code, http_error.msg)))
