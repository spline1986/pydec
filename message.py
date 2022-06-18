'''
Idec/ii message implemetation.
'''
from __future__ import annotations
from typing import NamedTuple


class Message(NamedTuple):
    '''
    Immutable message implementation.
    '''

    msgid: str
    tags: str
    echoarea: str
    date: int
    msgfrom: str
    address: str
    msgto: str
    subject: str
    body: str

    @classmethod
    def from_raw_text(cls, msgid: str, text: str) -> Message:
        '''
        Build message object by raw text message.

        Args:
            text: Raw text message.

        Returns:
            Message object.
        '''
        lines = text.split('\n')
        return cls(msgid,
                lines[0],
                lines[1],
                int(lines[2]),
                lines[3],
                lines[4],
                lines[5],
                lines[6],
                '\n'.join(lines[8:]))
