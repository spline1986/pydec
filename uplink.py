'''
IDEC uplink implementation for clients.
'''
import urllib.parse
import urllib.request
from base64 import b64encode, b64decode
from collections.abc import Collection
from typing import List, NamedTuple, Optional, Set, Tuple

from exceptions import AreaNameError, MsgIdError
from message import Message


AreaListItem = NamedTuple('AreaListItem',
                          [('name', str), ('count', int), ('description', str)])


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

    def list_txt(self) -> List[AreaListItem]:
        '''
        Get list.txt scheme.

        Returns:
            Information about public areas of uplink: name, messages count, description.
        '''
        result = []
        with urllib.request.urlopen(urllib.parse.urljoin(self.url, 'list.txt')) as response:
            for line in response.read().decode('utf-8').split('\n'):
                area = line.split(':')
                if len(area) > 2:
                    result.append(AreaListItem(area[0], int(area[1]), ':'.join(area[2:])))
        return result

    def blacklist_txt(self) -> Set[str]:
        '''
        Get blacklist.txt scheme.

        Returns:
            Blacklisted msgids.
        '''
        with urllib.request.urlopen(urllib.parse.urljoin(self.url, 'blacklist.txt')) as response:
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
        with urllib.request.urlopen(urllib.parse.urljoin(f'{self.url}e/', area)) as response:
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
        with urllib.request.urlopen(urllib.parse.urljoin(f'{self.url}m/', msgid)) as response:
            return Message.from_raw_text(msgid, response.read().decode('utf-8'))

    def ue_request(self,
                   area_collection: Collection[str],
                   start: Optional[int]=None,
                   end: Optional[int]=None) -> Tuple[str, ...]:
        '''
        Get areas index by areas names with optional slice.

        Args:
            area-collection: Areas names.
            start: Slice start position.
            end: Slice end offset.

        Returns:
            Universal (/u/) format areas index.
        '''
        is_names_correct, incorrect_area_name = self._is_area_collection_correct_names(area_collection)
        if not is_names_correct:
            raise AreaNameError(f'incorrect area name: {incorrect_area_name}')

        if start and end:
            url = urllib.parse.urljoin(f'{self.url}u/e/', '/'.join(area_collection) + \
                                       f'/{start}:{end}')
        else:
            url = urllib.parse.urljoin(f'{self.url}u/e/', '/'.join(area_collection))

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

        # TODO: Нарезать список msgid на куски по 40 штук и запрашивать пакетами
        url = urllib.parse.urljoin(f'{self.url}u/m/', '/'.join(msgid_collection))
        result = []
        with urllib.request.urlopen(url) as response:
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
