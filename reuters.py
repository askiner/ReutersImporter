"""
Reuters processor.
2016-07-07
получает фото от Reuters ContentDownloader
Важен каталог backup - с ним сравнивается пришедшие файлы. Если файлы лежат дольше 24 часов - их можно удалять.

2017-12-19 comments and use temporary for copy
"""
import os
import re
from xml.etree import cElementTree as et
from shutil import copyfile, move
import datetime

from tassphotoapi import get_item_by_original_unique_number as get_in_archive
from direct_db import hide_db_fixedid_item

DEBUG = True

if not DEBUG:
    import_video = r'\\ftp.tass.ru\FTP\Photo\assets\Partners\Video\Reuters'
    import_xml = r'\\ftp.tass.ru\FTP\Photo\assets\Partners\Video\Reuters\xml_source'
    #import_backup = r'\\msk-oft-app01.corp.tass.ru\c$\backup\Reuters'
    import_backup = r'C:\backup\Reuters'
    temp_path = r'C:\temp'
    duplicates = r''
else:
    import_video = r'/Users/shkirya_a/Documents/test/Reuters_out'
    import_xml = r'/Users/shkirya_a/Documents/test/Reuters_xml_out'
    import_backup = r'/Users/shkirya_a/Documents/test/backup'
    temp_path = r'/Users/shkirya_a/Documents/test'
    duplicates = r'/Users/shkirya_a/Documents/test/duplicates'

class reu_xml_util:
    ns = {'def': 'http://iptc.org/std/nar/2006-10-01/',
          'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
          'rtr': 'http://www.reuters.com/ns/2003/08/content',
          'x':   'http://www.w3.org/1999/xhtml',
          'xml': 'http://www.w3.org/XML/1998/namespace'}

    qcode = {'text': 'icls:text', 'video': 'icls:video'}

    def_source = 'Reuters'
    no_data = 'No-Data-Available'

    def __init__(self):
        pass

    @staticmethod
    def get_def_tag(name):
        """Get default tag
        """
        if name is not None and isinstance(name, str):
            return '{' + reu_xml_util.ns['def'] + '}' + name
        else:
            return name


    @staticmethod
    def get_item_class(elem):
        return elem.find('def:itemMeta/def:itemClass', reu_xml_util.ns)

    @staticmethod
    def is_item_class_type(elem, type_str):
        return elem.attrib['qcode'] == reu_xml_util.qcode[type_str]

    @staticmethod
    def get_package_unique_id(elem):

        pattern = re.compile(r"newsml_(.+)", re.IGNORECASE)

        uniqueId = pattern.search(elem.attrib['guid'])

        if uniqueId.lastindex > 0:
            return uniqueId.group(1)
        else:
            return None

    @staticmethod
    def get_package_version(elem):
        return elem.attrib['version']

    @staticmethod
    def get_keywords(elem):
        lst = []
        for keyword in elem.findall('def:contentMeta/def:keyword', reu_xml_util.ns):
            lst.append(keyword.text)
        return lst

    @staticmethod
    def get_creationdate(elem):
        if elem.find('def:itemMeta/def:versionCreated', reu_xml_util.ns) is not None:
            return datetime.datetime.strptime(elem.find('def:itemMeta/def:versionCreated', reu_xml_util.ns).text,
                                              '%Y-%m-%dT%H:%M:%S.%fZ').strftime('%d.%m.%Y')
        else:
            return None

    @staticmethod
    def get_files(elem):
        files = []
        for remote_content in elem.findall('def:contentSet/', reu_xml_util.ns):  # file names
            files.append(VideoFileInfo(remote_content))
        return files


class VideoDescription:
    headline = None
    caption = None
    credit = None
    source = None
    keywords = []
    creationdate = None
    copyright = None
    copyrightNotice = None
    uniqueId = None
    # country = None
    # country_code = None
    xml_file_name = None
    video_files = []

    def __init__(self):
        pass

    def ready(self):
        return self.caption is not None and self.headline is not None and len(self.video_files) > 0

    def save_xml(self, file_path):
        """
        Creates and serilizes XML for Orphea
        :return: None
        """

        if file_path is None:
            raise ValueError('name is Empty')

        name = os.path.basename(file_path)

        root = et.Element("assets")
        et.SubElement(root, "subtitle").text = os.path.splitext(name)[0]

        if self.source:
            et.SubElement(root, "source").text = self.source

        if self.headline:
            et.SubElement(root, "title").text = self.headline

        if self.caption:
            et.SubElement(root, "captionweb").text = self.caption
            et.SubElement(root, "caption").text = self.caption

        if self.credit:
            et.SubElement(root, "credit").text = self.credit
        elif self.source:
            et.SubElement(root, "credit").text = self.source + '/TASS'

        if len(self.keywords) > 0:
            try:
                et.SubElement(root, "keyword").text = ';'.join(self.keywords)
            except:
                et.SubElement(root, "keyword").text = ''

        et.SubElement(root, "modifieddate").text = datetime.datetime.now().strftime("%Y%m%d")
        et.SubElement(root, "modifiedtime").text = datetime.datetime.now().strftime("%H%M%S+3000")

        if self.uniqueId:
            et.SubElement(root, "fixident").text = self.uniqueId

        if self.copyright:
            et.SubElement(root, "copyright").text = self.copyright

        if self.copyrightNotice:
            et.SubElement(root, "observations").text = self.copyrightNotice



        if self.creationdate:
            et.SubElement(root, "creationdate").text = self.creationdate

        tree = et.ElementTree(root)
        tree.write(file_path,
                   encoding='utf-8',
                   xml_declaration=True)


class Publisher:

    path = {
        'video': import_video,
        'xml': import_xml,
        'backup': import_backup,
        'temp': temp_path,
        'duplicate': duplicates
    }

    description = None

    def __init__(self, descriptor):
        if descriptor is not None and isinstance(descriptor, VideoDescription):
            self.description = descriptor

    def send(self):

        if self.description.ready():

            # if file already exists ...
            # TODO: remove old file and send this one to ingest
            # get_in_archive
            data = get_in_archive(self.description.uniqueId)

            if data is not None:
                for item in data:
                    hide_db_fixedid_item(item['Id'])

            if os.path.exists(self.description.xml_file_name):
                search_path = os.path.dirname(self.description.xml_file_name)

                for file_info in self.description.video_files:
                    if os.path.exists(os.path.join(search_path, file_info.name)):
                        # create XML
                        self.description.save_xml(os.path.join(self.path['temp'], os.path.splitext(file_info.name)[0] + '.xml'))

                        # backup all
                        if self.path['backup'] is not None and \
                                        len(self.path['backup']) > 0 and \
                                os.path.exists(self.path['backup']):
                            copyfile(os.path.join(self.path['temp'], os.path.splitext(file_info.name)[0] + '.xml'),
                                     os.path.join(self.path['backup'], os.path.splitext(file_info.name)[0] + '.xml'))
                            copyfile(os.path.join(search_path, file_info.name),
                                     os.path.join(self.path['backup'], file_info.name))  # video file
                            copyfile(self.description.xml_file_name,
                                     os.path.join(self.path['backup'],
                                                  os.path.basename(self.description.xml_file_name)))  # xml file

                        # move file for XML import
                        move(os.path.join(self.path['temp'], os.path.splitext(file_info.name)[0] + '.xml'),
                                 os.path.join(self.path['xml'], os.path.splitext(file_info.name)[0] + '.xml'))

                        # copy video
                        copyfile(os.path.join(search_path, file_info.name),
                                 os.path.join(self.path['temp'], file_info.name))

                        move(os.path.join(self.path['temp'], file_info.name),
                                 os.path.join(self.path['video'], file_info.name))

                        os.remove(self.description.xml_file_name)
                        os.remove(os.path.join(search_path, file_info.name))

                        # delete all
                        # we don't need delete file right after send to import
                        # TODO: need garbage (old files) collector
                        # os.remove(os.path.join(self.path['temp'], os.path.splitext(file_info.name)[0] + '.xml'))
                        # os.remove(os.path.join(search_path, file_info.name))
                        # os.remove(self.description.xml_file_name)
        else:
            print("Description is not ready!")


# Object for storing data about video file
class VideoFileInfo:
    name = None,
    content_type = None,
    size = None

    def __init__(self, xml_elem):
        if xml_elem is not None and isinstance(xml_elem, et.Element):

            self.name = xml_elem.find('rtr:altId[@type="idType:fileBIN"]', reu_xml_util.ns).text
            self.content_type = xml_elem.attrib['contenttype']
            self.size = xml_elem.attrib['size']


def is_xml(file_name):
    """Check if file is XML
    returns filename if is really XML
    """
    pattern = re.compile(r".+.xml", re.IGNORECASE)

    match = pattern.match(file_name)

    return match


def get_content_items(item_set):
    """
    Gather the text data from XML
    :param item_set: list of itemSet XML element blocks
    :return: VideoDescription object
    """
    desc = VideoDescription()

    for elem in item_set:
        if elem.tag == reu_xml_util.get_def_tag('packageItem'):
            desc.keywords = reu_xml_util.get_keywords(elem)
            desc.creationdate = reu_xml_util.get_creationdate(elem)
            desc.uniqueId = reu_xml_util.get_package_unique_id(elem)

            desc.copyright = elem.find('def:rightsInfo/def:copyrightNotice', reu_xml_util.ns).text

            for cpr in elem.findall('def:rightsInfo/def:usageTerms', reu_xml_util.ns):
                if cpr.attrib.get('{' + reu_xml_util.ns['xml'] + '}lang') and \
                                cpr.attrib.get('{' + reu_xml_util.ns['xml'] + '}lang') == 'ru':
                    desc.copyrightNotice = cpr.text
                    break

        elif elem.tag == reu_xml_util.get_def_tag('newsItem'):
            item_class = reu_xml_util.get_item_class(elem)
            if item_class is not None:
                if reu_xml_util.is_item_class_type(item_class, 'text'):

                    desc.headline = elem.find('def:contentMeta/def:headline', reu_xml_util.ns).text

                    desc_body = elem.find('def:contentSet/def:inlineXML/x:html/x:body', reu_xml_util.ns)

                    if desc_body is not None:    # if we found body for description
                        list_of_str = et.tostring(desc_body, encoding='utf-8', method='text')\
                            .decode(encoding='utf-8')\
                            .strip()\
                            .splitlines()

                        list_of_str = [s.strip() for s in list_of_str]

                        desc.caption = '\n'.join(list_of_str)

                if reu_xml_util.is_item_class_type(item_class, 'video'):
                    # from video we load copyrights, source, files

                    desc.video_files = reu_xml_util.get_files(elem)

                    try:
                        orig_prov = elem.find('def:contentMeta/def:infoSource[@role="cRole:origProv"]', reu_xml_util.ns)\
                            .attrib['literal']
                        source = elem.find('def:contentMeta/def:infoSource[@role="cRole:source"]', reu_xml_util.ns)\
                            .attrib['literal']

                        if source != reu_xml_util.no_data:
                            desc.source = source
                        elif orig_prov != reu_xml_util.no_data:
                            desc.source = orig_prov
                        else:
                            desc.source = reu_xml_util.def_source
                    except AttributeError:
                        desc.source = reu_xml_util.def_source

    return desc


def read_xml(file_name):

    if os.path.exists(file_name):

        xtree = et.parse(file_name)

        itemSet = xtree.findall('./def:itemSet/', reu_xml_util.ns)
        if (itemSet and len(itemSet)) > 0:
            work_item = get_content_items(itemSet)
            work_item.xml_file_name = file_name

            pub = Publisher(work_item)
            pub.send()


def is_in_backup(file_to_check, test_folder):
    """
    is_in_backup - сравнение XML файла с файлом резерве
    :param file_to_check: any filename to check with backup files
    :param test_folder: folder where we check file existence
    :return: boolean value - True if found file in backup - so file already in system,
    False - no in backup? no in system
    """
    return os.path.exists(os.path.join(test_folder, file_to_check))


if __name__ == "__main__":

    import sys

    if not os.path.exists(import_backup):
        print("Test (backup) folder is wrong! Stop processing...")

    root_path = sys.argv[1]

    if os.path.exists(root_path):
        for item in os.listdir(root_path):
            root_item_path = os.path.join(root_path, item)            
            if os.path.isdir(root_item_path):
                print(item)
                for file in os.listdir(root_item_path):
                    # if not os.path.exists(os.path.join(import_backup, file)): # remove check with backup
                    if is_xml(file):
                        print(file)
                        read_xml(os.path.join(root_item_path, file))
