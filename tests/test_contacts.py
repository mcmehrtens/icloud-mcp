import vobject

from icloud_mcp import contacts

VCARD = """BEGIN:VCARD
VERSION:3.0
FN:Jane Doe
N:Doe;Jane;;;
TEL;TYPE=HOME,VOICE:+1 (555) 010-1234
TEL;TYPE=WORK:+1 555 010 9999
EMAIL;TYPE=INTERNET,HOME:jane@example.com
NOTE:Met at <b>conf</b><br>2025
END:VCARD"""


def test_read_back(monkeypatch):
    monkeypatch.setattr(contacts.config, "HTML_MODE", "text")
    vcard = vobject.readOne(VCARD)
    data = contacts._vcard_to_dict(vcard, "https://p1-contacts.icloud.com/c.vcf")
    assert data["name"] == "Jane Doe"
    assert data["notes"] == "Met at conf\n2025"
    assert data["phones"] == ["+1 (555) 010-1234", "+1 555 010 9999"]
    assert data["emails"] == ["jane@example.com"]


def test_contacts_are_read_only():
    for name in ("create_contact", "update_contact", "delete_contact", "_apply_fields"):
        assert not hasattr(contacts, name), name
