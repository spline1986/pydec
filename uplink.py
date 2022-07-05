'''
IDEC uplink implementation for clients.
'''
import os
import urllib.parse
import urllib.request
from base64 import b64encode, b64decode
from collections.abc import Collection
from typing import List, Optional, Set, Tuple

from .exceptions import AreaNameError, MsgIdError
from .message import Message
from .multipartform import MultiPartForm
from .idec_types import *


class Uplink:
    '''
    Uplink implementation.
    '''

    def __init__(self, url: str, authstr: Optional[str]=None, areas: Optional[List[str]]=None):
        self.url = url if url.endswith('/') else f'{url}/'
        self.authstr = authstr
        self.areas = areas if areas else []

    @staticmethod
    def _is_areaname_correct(name: str) -> bool:
        if '.' in name and name.isascii():
            return True
        return False

    @staticmethod
    def _is_area_collection_correct_names(
            area_collection: Collection[str]
    ) -> Tuple[bool, str]:
        for area in area_collection:
            if not Uplink._is_areaname_correct(area):
                return False, area
        return True, ''

    @staticmethod
    def _is_msgid_correct(msgid: str) -> bool:
        if len(msgid) != 20 or not msgid.isascii():
            return False
        return True

    @staticmethod
    def _is_msgid_collection_correct_ids(
            msgid_collection: Collection[str]
    ) -> Tuple[bool, str]:
        for msgid in msgid_collection:
            if not Uplink._is_msgid_correct(msgid):
                return False, msgid
        return True, ''

    @staticmethod
    def _urljoin(*args) -> str:
        return '/'.join(map(lambda x: x.strip('/'), args))

    def listtxt_request(self) -> List[AreaListItem]:
        '''
        Get list.txt scheme.

        Returns:
            Information about public areas of uplink: name, messages count, description.
        '''
        result = []
        with urllib.request.urlopen(self._urljoin(self.url, 'list.txt')) as response:
            for line in response.read().decode('utf-8').strip().split('\n'):
                area = line.split(':')
                result.append(AreaListItem(area[0], int(area[1]), ':'.join(area[2:])))
        return result

    def blacklisttxt_request(self) -> Set[str]:
        '''
        Get blacklist.txt scheme.

        Returns:
            Blacklisted msgids.
        '''
        with urllib.request.urlopen(self._urljoin(self.url, 'blacklist.txt')) as response:
            return set(filter(lambda x: x, response.read().decode('utf-8').split()))

    def e_request(self, area: str) -> Tuple[str, ...]:
        '''
        Get area index by name.

        Args:
            area: Area name.

        Returns:
            Msgids.
        '''
        if not self._is_areaname_correct(area):
            raise AreaNameError(f'incorrect area name: {area}')
        with urllib.request.urlopen(self._urljoin(self.url, 'e', area)) as response:
            return tuple(map(str,
                             filter(lambda x: x, response.read().decode('utf-8').split())))

    def m_request(self, msgid: str) -> Message:
        '''
        Get message by msgid.

        Args:
            msgid: Message id.

        Returns:
            Message object.
        '''
        if not self._is_msgid_correct(msgid):
            raise MsgIdError(f'incorrect msgid: {msgid}')
        with urllib.request.urlopen(self._urljoin(self.url, 'm', msgid)) as response:
            return Message.from_raw_text(msgid, response.read().decode('utf-8'))

    def ue_request(self, area_collection: Collection[str], start: int=0, end: int=0) -> Tuple[str, ...]:
        '''
        Get areas index by areas names with optional slice.

        Args:
            area-collection: Areas names.
            start: Slice start position (default 0 - disabled slice).
            end: Slice end offset (default 0 - disables slice).

        Returns:
            Areas index.
        '''
        is_names_correct, incorrect_area_name = self._is_area_collection_correct_names(area_collection)
        if not is_names_correct:
            raise AreaNameError(f'incorrect area name: {incorrect_area_name}')

        if start and end:
            url = self._urljoin(self.url, 'u/e', *area_collection, f'/{start}:{end}')
        else:
            url = self._urljoin(self.url, 'u/e/', *area_collection)

        with urllib.request.urlopen(url) as response:
            return tuple(map(str,
                             filter(lambda x: x, response.read().decode('utf-8').split())))

    def um_request(self, msgid_collection: Collection[str]) -> List[Message]:
        '''
        Get messages by msgids.

        Args:
            msgid_collection: Messages ids.

        Returns:
            Messages objects.
        '''
        is_msgid_correct, incorrect_msgid = self._is_msgid_collection_correct_ids(msgid_collection)
        if not is_msgid_correct:
            raise MsgIdError(f'incorrect msgid: {incorrect_msgid}')

        result = []
        with urllib.request.urlopen(self._urljoin(self.url, 'u/m', *msgid_collection)) as response:
            for line in response.read().decode('utf-8').split():
                msgid, encoded = line.split(':', 1)
                result.append(Message.from_raw_text(msgid, b64decode(encoded).decode()))
        return result

    def upoint_request(self, message: str) -> str:
        '''
        Send message.

        Args:
            message: Message text with header.

        Returns:
            Uplink response text.
        '''
        data = urllib.parse.urlencode({
            'pauth': self.authstr,
            'tmsg': b64encode(message.encode('utf-8')).decode()
        }).encode('ascii')
        with urllib.request.urlopen(f'{self.url}u/point', data) as response:
            return response.read().decode('utf-8')

    def xc_request(self, area_collection: Collection[str]) -> AreaCount:
        '''
        Get areas messages count.

        Args:
            area_collection: Area names.

        Returns:
            Number of messages in the area, where the key is the name of the
            conference and the value is the number of messages.
        '''
        result = {}
        with urllib.request.urlopen(self._urljoin(self.url, 'x/c', *area_collection)) as response:
            for line in response.read().decode('utf-8').strip().split('\n'):
                field = line.split(':')
                result[field[0]] = int(field[1])
        return result

    def xfeatures_request(self) -> Tuple[str]:
        '''
        Get uplink features list.

        Returns:
            List of uplink features supported.
        '''
        with urllib.request.urlopen(f'{self.url}x/features') as response:
            return tuple(response.read().decode('utf-8').strip().split('\n'))

    def upush_request(self, area: str, bundle: Collection[str]) -> str:
        '''
        Push message-bundle to uplink (node-to-node mode only).

        Args:
            area: Area name.
            bundle: Messages bundle as collection bundle lines.

        Returns:
            Uplink response text.
        '''
        data = urllib.parse.urlencode({
            'nauth': self.authstr,
            'echoarea': area,
            'upush': bundle,
        }).encode('ascii')
        with urllib.request.urlopen(f'{self.url}u/push', data=data) as response:
            return response.read().decode('utf-8')

    def xfilelist_request(self) -> Tuple[FileListItem]:
        '''
        Get uplink file list.

        Returns:
            List of uplink published files (including for points only and private).
        '''
        result = []
        data = urllib.parse.urlencode({
            'pauth': self.authstr,
        }).encode('ascii')
        with urllib.request.urlopen(f'{self.url}x/filelist', data=data) as response:
            for line in response.read().decode('utf-8').strip().split('\n'):
                field = line.split(':')
                result.append(FileListItem(field[0], int(field[1]), ':'.join(field[2:])))
        return tuple(result)

    def xfile_request(self, filename: str) -> bytes:
        '''
        Download file.

        Args:
            filename: Filename.

        Returns:
            File as bytes object.
        '''
        data = urllib.parse.urlencode({
            'pauth': self.authstr,
            'filename': filename,
        }).encode('ascii')
        with urllib.request.urlopen(f'{self.url}x/file', data=data) as response:
            return response.read()

    def flisttxt_request(self) -> List[AreaListItem]:
        '''
        Get filearea list.

        Returns:
            List of uplink fileareas.
        '''
        result = []
        with urllib.request.urlopen(f'{self.url}f/list.txt') as response:
            for line in response.read().decode('utf-8').strip().split('\n'):
                field = line.split(':')
                result.append(AreaListItem(field[0], int(field[1]), ':'.join(field[2:])))
        return result

    def fblacklisttxt_request(self) -> Tuple[str]:
        '''
        Get uplink fileareas blacklist.

        Returns:
            Blacklisted files.
        '''
        with urllib.request.urlopen(f'{self.url}f/blacklist.txt') as response:
            return tuple(response.read().decode('utf-8').strip().split('\n'))

    def fc_request(self, filearea_collection: Collection[str]) -> AreaCount:
        '''
        Get upling fileareas counts of files.

        Args:
            filearea_collection: Fileareas names.

        Returns:
            Number of files in the filearea, where the key is the name of the
            conference and the value is the number of files.
        '''
        result = {}
        with urllib.request.urlopen(self._urljoin(self.url, 'f/c', *filearea_collection)) as response:
            for line in response.read().decode('utf-8').strip().split('\n'):
               field = line.split(':')
               result[field[0]] = int(field[1])
        return result

    def fe_request(self, filearea_collection: Collection[str], start: int=0, end: int=0) -> Tuple[FileAreaItem]:
        '''
        Get filearea undex of uplink.

        Args:
            filearea_collection: Fileareas names.
            start: Slice start position (default 0 - disabled slice).
            end: Slice end offset (default 0 - disables slice).

        Returns:
            Fileareas index.
        '''
        if start and end:
            url = self._urljoin(self.url, 'f/e', * filearea_collection, f'{start}:{end}')
        else:
            url = self._urljoin(self.url, 'f/e', * filearea_collection)
        result = []
        with urllib.request.urlopen(url) as response:
            area_name = ""
            for line in response.read().decode('utf-8').strip().split('\n'):
                field = line.split(':')
                if len(field) == 1:
                    area_name = field[0]
                    continue
                result.append(FileAreaItem(
                    area_name,
                    field[0],
                    field[1],
                    int(field[2]),
                    field[3],
                    ':'.join(field[4:])
                ))
        return tuple(result)

    def ff_request(self, filearea: str, fid: str) -> bytes:
        '''
        Download filearea file.

        Args:
           filearea: Filearea name.
           fid: File ID.

        Returns:
            File as bytes object.
        '''
        with urllib.request.urlopen(self._urljoin(self.url, 'f/f', filearea, fid)) as response:
            return response.read()

    def fp_request(self, file_path: str, filearea: str, description: str) -> str:
        '''
        Upload file to filearea.

        Args:
            file_path: Path to uploading file.
            filearea: Filearea name.
            description: Short file description.

        Returns:
            Uplink response message.
        '''
        form = MultiPartForm()
        form.add_field('pauth', self.authstr)
        form.add_field('fecho', filearea)
        form.add_field('dsc', description)
        form.add_file('file', os.path.basename(file_path), fileHandle=open(file_path, 'rb'))
        request = urllib.request.Request(f'{self.url}f/p', data=bytes(form))
        request.add_header('Content-type', form.get_content_type())
        with urllib.request.urlopen(request) as response:
            return response.read().decode('utf-8')
