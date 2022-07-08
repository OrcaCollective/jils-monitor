import base64
import dataclasses
import json
from typing import Any, Dict, List

import jmespath
import requests
from bs4 import BeautifulSoup


class RequestVerificationToken:
    """
    RequestVerificationTokens for the JILS portal. I'm guessing this is
    something like a CSRF token.

    The JILS portal uses two request verification tokens, both included in the
    response from `REQUEST_VERIFICATION_URL`. The DOM token is included in the
    `value` attribute of the returned <input>, while the cookie token is
    returned in the response `Set-Cookie` header.

    To use these tokens in the JILS call, the DOM token is added to the header
    as the value to the REQUEST_VERIFICATION_KEY. The cookie token is added
    to the `Cookie` header included in the call.
    """

    KEY = "__RequestVerificationToken"
    URL = "https://dajd-jms.powerappsportals.us/_layout/tokenhtml"

    def __init__(self, cookie: str, dom: str):
        self.cookie = cookie
        self.dom = dom

    @classmethod
    def create(cls) -> "RequestVerificationToken":
        resp = requests.get(cls.URL)

        cookie_token = resp.cookies[cls.KEY]

        soup = BeautifulSoup(resp.text, features="html.parser")
        dom_token = soup.find("input", {"name": cls.KEY}).attrs["value"]

        return RequestVerificationToken(cookie_token, dom_token)


@dataclasses.dataclass(frozen=True)
class JILSRecord:
    """Holds information on a person who was or is in DAJD custody."""

    ucn: str
    name: str
    book_date: str
    facility: str


class JILSRecordEncoder(json.JSONEncoder):
    """
    A sub-class of JSONEncoder that enables encoding dataclasses as JSON.
    See: https://stackoverflow.com/questions/51286748/
    """

    def default(self, obj):
        if dataclasses.is_dataclass(obj):
            return dataclasses.asdict(obj)
        return super().default(obj)


class JILSRecordReader:
    """
    An iterable class that reads JSON booking records from JILS and converts
    them into JILSRecord objects.
    """

    def __init__(self, records):
        self.records = records

    def __iter__(self):
        return self

    def __next__(self) -> JILSRecord:
        if len(self.records) > 1:
            self.records.pop(0)
            return self.read(self.records[0])
        raise StopIteration

    def _get_record_attr(self, record: Dict[str, Any], key: str, attr: str) -> str:
        return jmespath.search(f"Attributes[?Name == '{key}'].{attr}", record)[0]

    def read(self, record: Dict[str, Any]) -> JILSRecord:
        """Return a JILSRecord for a given JILS JSON booking record."""
        ucn = self._get_record_attr(record, "tri_offenderid", "Value")
        name = self._get_record_attr(record, "name", "Value")
        book_date = self._get_record_attr(
            record,
            "a_3132e4ba991de911a95e001dd80081ad.tri_completedon",
            "FormattedValue",
        )
        facility = self._get_record_attr(record, "tri_facilityid", "Value.Name")
        return JILSRecord(ucn, name, book_date, facility)


class JILSClient:
    """(Unofficial) API client for JILS."""

    API_URL: str = "https://dajd-jms.powerappsportals.us/_services/entity-grid-data.json/d78574f9-20c3-4dcc-8d8d-85cf5b7ac141"
    PORTAL_URL: str = "https://dajd-jms.powerappsportals.us/public/subject-lookup/"
    STANDARD_HEADERS: Dict[str, str] = {
        "Content-Type": "application/json; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
    }

    def _get_secure_config(self, view_display_name: str) -> str:
        soup = BeautifulSoup(requests.get(self.PORTAL_URL).text, features="html.parser")
        grid = soup.find("div", class_="entity-grid")
        layouts = json.loads(base64.b64decode(grid.attrs["data-view-layouts"]))

        return jmespath.search(
            f"[?Configuration.ViewDisplayName == '{view_display_name}'].Base64SecureConfiguration",
            layouts,
        ).pop()

    def _call(
        self, view_display_name: str, page: int = 1, page_size: int = 100
    ) -> List[JILSRecord]:
        token = RequestVerificationToken.create()

        headers = self.STANDARD_HEADERS.copy()
        headers[RequestVerificationToken.KEY] = token.dom
        headers["Cookie"] = f"{RequestVerificationToken.KEY}={token.cookie}"

        payload = {
            "base64SecureConfiguration": self._get_secure_config(view_display_name),
            # "sortExpression": "tri_offenderid DESC",
            "sortExpression": "a_3132e4ba991de911a95e001dd80081ad.tri_completedon DESC",
            "search": "",
            "page": page,
            "pageSize": page_size,
            "filter": None,
            "metaFilter": "0=&1=&2=&3=&4=&5=&6=&7=&8=&9=",
            "timezoneOffset": 420,
            "customParameters": [],
        }

        resp = requests.post(
            self.API_URL, headers=headers, data=json.dumps(payload)
        ).json()
        records = list(JILSRecordReader(resp["Records"]))

        # If more records, recursively check next page
        if resp["MoreRecords"]:
            records += self._call(view_display_name, page + 1, page_size)

        return records

    def list_bookings_in_last_24_hours(self) -> List[JILSRecord]:
        """Return a list of JILSRecords for bookings in the last 24 hours."""
        return self._call("Subjects Booked in Last 24 Hours")


if __name__ == "__main__":
    print(
        json.dumps(
            JILSClient().list_bookings_in_last_24_hours(),
            cls=JILSRecordEncoder,
            indent=4,
            sort_keys=True
        )
    )
