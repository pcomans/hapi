"""Museum source identifiers and license metadata."""

from enum import Enum


class MuseumSource(str, Enum):
    """Canonical identifiers for each museum source.

    Adding a new museum requires:
    1. Adding an entry here
    2. Creating ingest + normalize assets
    3. Adding fixture data + mapper tests
    See pipeline/CLAUDE.md for the full checklist.
    """

    MET = "met"
    BROOKLYN = "brooklyn"
    HARVARD = "harvard"


class License(str, Enum):
    """License types that govern image rendering in the UI."""

    NONE = "none"  # No image available — nothing to license
    CC0 = "cc0"
    CC_BY = "cc-by"
    CC_BY_NC = "cc-by-nc"
    CC_BY_NC_ND = "cc-by-nc-nd"
    CC_BY_NC_SA = "cc-by-nc-sa"
    NON_COMMERCIAL_EDUCATIONAL = "non-commercial-educational"
    RESTRICTED = "restricted"
    UNKNOWN = "unknown"


# Maps each museum to its license for image content
MUSEUM_LICENSE: dict[MuseumSource, License] = {
    MuseumSource.MET: License.CC0,
    MuseumSource.BROOKLYN: License.CC_BY_NC_ND,
    MuseumSource.HARVARD: License.NON_COMMERCIAL_EDUCATIONAL,
}
