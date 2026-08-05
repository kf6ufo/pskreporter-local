from __future__ import annotations

from datetime import UTC, datetime

from defusedxml import ElementTree
from defusedxml.common import DefusedXmlException

from .bands import band_from_frequency
from .models import ParsedReports, ReceptionReport, XmlTrace


class InvalidPskXml(ValueError):
    """PSK Reporter returned XML that cannot be safely normalized."""

    def __init__(self, message: str, xml_trace: XmlTrace | None = None) -> None:
        super().__init__(message)
        self.xml_trace = xml_trace


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def parse_reception_reports(xml: bytes) -> ParsedReports:
    try:
        root = ElementTree.fromstring(xml)
    except (ElementTree.ParseError, DefusedXmlException) as exc:
        raise InvalidPskXml("The response was not valid, safe XML.") from exc

    if _local_name(root.tag) != "receptionReports":
        raise InvalidPskXml(
            f"Expected receptionReports root, received {_local_name(root.tag)!r}."
        )

    reports: list[ReceptionReport] = []
    warnings: list[str] = []
    report_elements = [
        element
        for element in root.iter()
        if _local_name(element.tag) == "receptionReport"
    ]

    for index, element in enumerate(report_elements, start=1):
        attrs = element.attrib
        try:
            sender_call = attrs["senderCallsign"].strip().upper()
            receiver_call = attrs["receiverCallsign"].strip().upper()
            frequency_hz = int(attrs["frequency"])
            epoch_seconds = int(attrs["flowStartSeconds"])
            if not sender_call or not receiver_call or frequency_hz <= 0:
                raise ValueError("required values may not be empty")
            spot_time = datetime.fromtimestamp(epoch_seconds, UTC)
        except (KeyError, OverflowError, OSError, TypeError, ValueError) as exc:
            warnings.append(f"Skipped malformed receptionReport #{index}: {exc}")
            continue

        reports.append(
            ReceptionReport(
                spot_time_utc=spot_time.isoformat().replace("+00:00", "Z"),
                sender_call=sender_call,
                receiver_call=receiver_call,
                sender_locator=_optional_text(attrs.get("senderLocator")),
                receiver_locator=_optional_text(attrs.get("receiverLocator")),
                sender_region=_optional_text(attrs.get("senderRegion")),
                sender_dxcc=_optional_text(attrs.get("senderDXCC")),
                receiver_latitude=None,
                receiver_longitude=None,
                frequency_hz=frequency_hz,
                band=band_from_frequency(frequency_hz),
                mode=(
                    mode.upper()
                    if (mode := _optional_text(attrs.get("mode"))) is not None
                    else None
                ),
            )
        )

    if report_elements and not reports:
        raise InvalidPskXml("Every receptionReport record was malformed.")

    reports.sort(key=lambda report: report.spot_time_utc, reverse=True)
    return ParsedReports(reports=tuple(reports), warnings=tuple(warnings))
