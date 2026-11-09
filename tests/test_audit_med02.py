import pytest
from src.news import _download_calendar, parse_ff_xml

def test_download_calendar_refuses_non_https():
    with pytest.raises(ValueError, match="Insecure or unsupported calendar URL scheme"):
        _download_calendar("file:///C:/Windows/win.ini")

def test_parse_ff_xml_safe_from_xxe():
    malicious_xml = """<?xml version="1.0"?>
    <!DOCTYPE lolz [
      <!ENTITY lol "lol">
      <!ENTITY lol1 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">
    ]>
    <weeklyevents>
      <event>
        <title>&lol1;</title>
        <country>USD</country>
        <date>01-01-2026</date>
        <time>10:00am</time>
        <impact>High</impact>
      </event>
    </weeklyevents>"""

    # defusedxml should raise EntitiesForbidden or DTDForbidden on entity expansion
    from defusedxml.common import DefusedXmlException
    with pytest.raises(DefusedXmlException):
        parse_ff_xml(malicious_xml)
