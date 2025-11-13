"""
Project: LandIS Portal
Institution: Cranfield University
Author: Professor Stephen Hallett

XML construction utilities for ISO 19139 metadata serialisation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Iterable
import xml.etree.ElementTree as ET

NAMESPACES = {
    "gmd": "http://www.isotc211.org/2005/gmd",
    "gco": "http://www.isotc211.org/2005/gco",
    "gml": "http://www.opengis.net/gml",
    "gts": "http://www.isotc211.org/2005/gts",
    "xsi": "http://www.w3.org/2001/XMLSchema-instance",
    "srv": "http://www.isotc211.org/2005/srv",
}

for prefix, uri in NAMESPACES.items():
    ET.register_namespace(prefix, uri)


def _qn(prefix: str, tag: str) -> str:
    """Build a fully qualified XML tag name for a registered namespace.

    Parameters:
        prefix: Namespace prefix defined in the NAMESPACES mapping.
        tag: Local tag name to qualify.

    Returns:
        Expanded tag name suitable for ElementTree operations.
    """
    return f"{{{NAMESPACES[prefix]}}}{tag}"


def _character_string(text: str | None) -> ET.Element:
    """Wrap text in a gco:CharacterString element, handling blank values.

    Parameters:
        text: Raw string content to wrap; blanks result in empty elements.

    Returns:
        Element containing the provided text or remaining empty.
    """
    element = ET.Element(_qn("gco", "CharacterString"))
    if text is not None:
        element.text = text
    return element


def _optional_element(parent: ET.Element, prefix: str, tag: str, text: str | None) -> None:
    """Attach a text element when text is supplied, otherwise skip creation.

    Parameters:
        parent: Element that will receive the child.
        prefix: Namespace prefix for the child element.
        tag: Tag name for the child element.
        text: Optional text to include within the child.

    Returns:
        None. Modifies the parent element in place.
    """
    if text is None or text == "":
        return
    child = ET.SubElement(parent, _qn(prefix, tag))
    child.append(_character_string(text))


def _format_date(value: Any) -> str | None:
    """Normalise supported date-like values into ISO formatted strings.

    Parameters:
        value: Date, datetime, or text value requiring normalisation.

    Returns:
        ISO formatted date string, or None when conversion is not possible.
    """
    if value is None:
        return None
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, datetime):
        return value.date().isoformat()
    text = str(value).strip()
    return text or None


@dataclass(slots=True)
class BuildOptions:
    """Optional overrides controlling metadata XML generation.

    Attributes:
        language_code: ISO language code used for metadata language elements.
        character_set: Declared character set identifier for the document.
        hierarchy_level: Hierarchy scope code describing the metadata record.
        date_stamp: Optional override for the metadata date stamp.
        contact_name: Optional contact person name.
        contact_organisation: Optional contact organisation name.
        contact_email: Optional contact e-mail address.
    """

    language_code: str = "eng"
    character_set: str = "utf8"
    hierarchy_level: str = "dataset"
    date_stamp: date | None = None
    contact_name: str | None = None
    contact_organisation: str | None = None
    contact_email: str | None = None


def build_metadata_tree(bundle: dict[str, Any], options: BuildOptions | None = None) -> ET.ElementTree:
    """Construct an ISO 19139 metadata tree for a prepared bundle.

    Parameters:
        bundle: Aggregated metadata content retrieved from the database layer.
        options: Optional overrides for metadata presentation defaults.

    Returns:
        ElementTree representing the final metadata document.
    """
    options = options or BuildOptions()

    root = ET.Element(_qn("gmd", "MD_Metadata"))

    _build_file_identifier(root, bundle)
    _build_language(root, options.language_code)
    _build_character_set(root, options.character_set)
    _build_hierarchy_level(root, options.hierarchy_level)
    _build_contact(root, bundle, options)
    _build_date_stamp(root, options.date_stamp)
    _build_reference_system(root)
    _build_identification_info(root, bundle)
    _build_distribution(root, bundle)
    _build_data_quality(root, bundle)
    _build_extension_info(root, bundle)

    return ET.ElementTree(root)


def _build_file_identifier(root: ET.Element, bundle: dict[str, Any]) -> None:
    """Populate the file identifier element.

    Parameters:
        root: Metadata root element to populate.
        bundle: Metadata bundle containing the identifier.

    Returns:
        None. Updates the XML tree in place.
    """
    file_identifier = ET.SubElement(root, _qn("gmd", "fileIdentifier"))
    file_identifier.append(_character_string(bundle["metadata_id"]))


def _build_language(root: ET.Element, language_code: str) -> None:
    """Populate the language element.

    Parameters:
        root: Metadata root element to populate.
        language_code: ISO language code associated with the metadata.

    Returns:
        None. Updates the XML tree in place.
    """
    language = ET.SubElement(root, _qn("gmd", "language"))
    lang_code_element = ET.SubElement(language, _qn("gmd", "LanguageCode"))
    lang_code_element.set("codeList", "http://standards.iso.org/ittf/PubliclyAvailableStandards/ISO_19139_Schemas/resources/Codelist/ML_gmxCodelists.xml#LanguageCode")
    lang_code_element.set("codeListValue", language_code)
    lang_code_element.text = language_code


def _build_character_set(root: ET.Element, character_set: str) -> None:
    """Populate the character set element.

    Parameters:
        root: Metadata root element to populate.
        character_set: Character set identifier to declare.

    Returns:
        None. Updates the XML tree in place.
    """
    character_set_element = ET.SubElement(root, _qn("gmd", "characterSet"))
    charset = ET.SubElement(character_set_element, _qn("gmd", "MD_CharacterSetCode"))
    charset.set("codeList", "http://www.isotc211.org/2005/resources/codeList.xml#MD_CharacterSetCode")
    charset.set("codeListValue", character_set)


def _build_hierarchy_level(root: ET.Element, hierarchy_level: str) -> None:
    """Populate the hierarchy level element.

    Parameters:
        root: Metadata root element to populate.
        hierarchy_level: Scope code describing the metadata hierarchy.

    Returns:
        None. Updates the XML tree in place.
    """
    hierarchy_level_element = ET.SubElement(root, _qn("gmd", "hierarchyLevel"))
    scope = ET.SubElement(hierarchy_level_element, _qn("gmd", "MD_ScopeCode"))
    scope.set("codeList", "http://standards.iso.org/ittf/PubliclyAvailableStandards/ISO_19139_Schemas/resources/Codelist/ML_gmxCodelists.xml#MD_ScopeCode")
    scope.set("codeListValue", hierarchy_level)
    scope.text = hierarchy_level


def _build_contact(root: ET.Element, bundle: dict[str, Any], options: BuildOptions) -> None:
    """Populate contact information using bundle data and override options.

    Parameters:
        root: Metadata root element to populate.
        bundle: Metadata bundle containing default contact references.
        options: Optional overrides for contact details.

    Returns:
        None. Updates the XML tree in place.
    """
    contact_element = ET.SubElement(root, _qn("gmd", "contact"))
    responsible_party = ET.SubElement(contact_element, _qn("gmd", "CI_ResponsibleParty"))

    if options.contact_name:
        individual_name = ET.SubElement(responsible_party, _qn("gmd", "individualName"))
        individual_name.append(_character_string(options.contact_name))

    if options.contact_organisation:
        organisation = ET.SubElement(responsible_party, _qn("gmd", "organisationName"))
        organisation.append(_character_string(options.contact_organisation))

    if options.contact_email:
        contact_info = ET.SubElement(responsible_party, _qn("gmd", "contactInfo"))
        ci_contact = ET.SubElement(contact_info, _qn("gmd", "CI_Contact"))
        address = ET.SubElement(ci_contact, _qn("gmd", "address"))
        ci_address = ET.SubElement(address, _qn("gmd", "CI_Address"))
        email = ET.SubElement(ci_address, _qn("gmd", "electronicMailAddress"))
        email.append(_character_string(options.contact_email))

    role = ET.SubElement(responsible_party, _qn("gmd", "role"))
    role_code = ET.SubElement(role, _qn("gmd", "CI_RoleCode"))
    role_code.set("codeList", "http://www.isotc211.org/2005/resources/codeList.xml#CI_RoleCode")
    role_code.set("codeListValue", "pointOfContact")
    role_code.text = "pointOfContact"


def _build_date_stamp(root: ET.Element, date_stamp: date | None) -> None:
    """Populate the date stamp element with an explicit or current date.

    Parameters:
        root: Metadata root element to populate.
        date_stamp: Optional override for the date stamp value.

    Returns:
        None. Updates the XML tree in place.
    """
    if date_stamp is None:
        date_value = date.today()
    else:
        date_value = date_stamp

    date_stamp_element = ET.SubElement(root, _qn("gmd", "dateStamp"))
    date_element = ET.SubElement(date_stamp_element, _qn("gco", "Date"))
    date_element.text = date_value.isoformat()


def _build_reference_system(root: ET.Element) -> None:
    """Populate reference system metadata.

    Parameters:
        root: Metadata root element to populate.

    Returns:
        None. Updates the XML tree in place.
    """
    reference_system_info = ET.SubElement(root, _qn("gmd", "referenceSystemInfo"))
    md_reference_system = ET.SubElement(reference_system_info, _qn("gmd", "MD_ReferenceSystem"))
    identifier = ET.SubElement(md_reference_system, _qn("gmd", "referenceSystemIdentifier"))
    rs_identifier = ET.SubElement(identifier, _qn("gmd", "RS_Identifier"))
    code = ET.SubElement(rs_identifier, _qn("gmd", "code"))
    code.append(_character_string("British National Grid"))


def _build_identification_info(root: ET.Element, bundle: dict[str, Any]) -> None:
    """Populate identification information using the main metadata bundle.

    Parameters:
        root: Metadata root element to populate.
        bundle: Metadata bundle containing primary descriptive data.

    Returns:
        None. Updates the XML tree in place.
    """
    main = bundle["main"]
    group = bundle.get("group")
    citation = bundle.get("citation")
    keywords = bundle.get("keywords", [])

    identification_info = ET.SubElement(root, _qn("gmd", "identificationInfo"))
    data_identification = ET.SubElement(identification_info, _qn("gmd", "MD_DataIdentification"))

    citation_element = ET.SubElement(data_identification, _qn("gmd", "citation"))
    ci_citation = ET.SubElement(citation_element, _qn("gmd", "CI_Citation"))

    title = ET.SubElement(ci_citation, _qn("gmd", "title"))
    title.append(_character_string(main.get("title")))

    if citation:
        _optional_element(ci_citation, "gmd", "alternateTitle", citation.get("citation_title"))
        date_element = ET.SubElement(ci_citation, _qn("gmd", "date"))
        ci_date = ET.SubElement(date_element, _qn("gmd", "CI_Date"))
        publication_date = _format_date(citation.get("citation_pubdate"))
        if publication_date:
            date_value = ET.SubElement(ci_date, _qn("gmd", "date"))
            date_value.append(_character_string(publication_date))
        date_type = ET.SubElement(ci_date, _qn("gmd", "dateType"))
        date_type_code = ET.SubElement(date_type, _qn("gmd", "CI_DateTypeCode"))
        date_type_code.set("codeList", "http://www.isotc211.org/2005/resources/codeList.xml#CI_DateTypeCode")
        date_type_code.set("codeListValue", "publication")
        date_type_code.text = "publication"

    abstract = ET.SubElement(data_identification, _qn("gmd", "abstract"))
    abstract.append(_character_string(main.get("abstract")))

    if group and group.get("purpose"):
        purpose = ET.SubElement(data_identification, _qn("gmd", "purpose"))
        purpose.append(_character_string(group["purpose"]))
    elif main.get("supplemental_information"):
        supplemental = ET.SubElement(data_identification, _qn("gmd", "purpose"))
        supplemental.append(_character_string(main["supplemental_information"]))

    status_value = main.get("status_progress")
    if status_value:
        status = ET.SubElement(data_identification, _qn("gmd", "status"))
        progress = ET.SubElement(status, _qn("gmd", "MD_ProgressCode"))
        progress.set("codeList", "http://www.isotc211.org/2005/resources/codeList.xml#MD_ProgressCode")
        progress.set("codeListValue", status_value)
        progress.text = status_value

    if keywords:
        for keyword_group, group_keywords in _group_keywords_by_type(keywords).items():
            descriptive_keywords = ET.SubElement(data_identification, _qn("gmd", "descriptiveKeywords"))
            md_keywords = ET.SubElement(descriptive_keywords, _qn("gmd", "MD_Keywords"))
            for keyword in group_keywords:
                keyword_element = ET.SubElement(md_keywords, _qn("gmd", "keyword"))
                keyword_element.append(_character_string(keyword["keyword"]))
            if keyword_group:
                keyword_type = ET.SubElement(md_keywords, _qn("gmd", "type"))
                keyword_code = ET.SubElement(keyword_type, _qn("gmd", "MD_KeywordTypeCode"))
                keyword_code.set("codeList", "http://www.isotc211.org/2005/resources/codeList.xml#MD_KeywordTypeCode")
                keyword_code.set("codeListValue", keyword_group)
                keyword_code.text = keyword_group

    _build_constraints(data_identification, group)
    _build_spatial_representation(data_identification, main)
    _build_extent(data_identification, main)


def _group_keywords_by_type(keywords: Iterable[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Group keyword records by their declared type.

    Parameters:
        keywords: Iterable of keyword dictionaries sourced from the database.

    Returns:
        Mapping between keyword type and list of keyword records.
    """
    grouped: dict[str, list[dict[str, Any]]] = {}
    for keyword in keywords:
        keyword_type = (keyword.get("keyword_type") or "").strip()
        grouped.setdefault(keyword_type, []).append(keyword)
    return grouped


def _build_constraints(parent: ET.Element, group: dict[str, Any] | None) -> None:
    """Populate constraint elements when group data is available.

    Parameters:
        parent: Identification element receiving constraint information.
        group: Metadata group record containing constraint details.

    Returns:
        None. Updates the XML tree in place.
    """
    if not group:
        return

    if group.get("use_constraint"):
        constraint = ET.SubElement(parent, _qn("gmd", "resourceConstraints"))
        md_constraints = ET.SubElement(constraint, _qn("gmd", "MD_Constraints"))
        use_limitation = ET.SubElement(md_constraints, _qn("gmd", "useLimitation"))
        use_limitation.append(_character_string(group["use_constraint"]))

    if group.get("access_constraint"):
        legal_constraint = ET.SubElement(parent, _qn("gmd", "resourceConstraints"))
        md_legal = ET.SubElement(legal_constraint, _qn("gmd", "MD_LegalConstraints"))
        access_constraints = ET.SubElement(md_legal, _qn("gmd", "accessConstraints"))
        restriction = ET.SubElement(access_constraints, _qn("gmd", "MD_RestrictionCode"))
        restriction.set("codeList", "http://standards.iso.org/ittf/PubliclyAvailableStandards/ISO_19139_Schemas/resources/Codelist/ML_gmxCodelists.xml#MD_RestrictionCode")
        restriction.set("codeListValue", group["access_constraint"])
        restriction.text = group["access_constraint"]


def _build_spatial_representation(parent: ET.Element, main: dict[str, Any]) -> None:
    """Populate spatial representation using the metadata facing value.

    Parameters:
        parent: Identification element receiving spatial metadata.
        main: Main metadata record containing spatial representation info.

    Returns:
        None. Updates the XML tree in place.
    """
    spatial_type = main.get("metadata_facing")
    if not spatial_type:
        return

    representation = ET.SubElement(parent, _qn("gmd", "spatialRepresentationType"))
    spatial_code = ET.SubElement(representation, _qn("gmd", "MD_SpatialRepresentationTypeCode"))
    spatial_code.set("codeList", "http://www.isotc211.org/2005/resources/codeList.xml#MD_SpatialRepresentationTypeCode")
    spatial_code.set("codeListValue", spatial_type)
    spatial_code.text = spatial_type


def _build_extent(parent: ET.Element, main: dict[str, Any]) -> None:
    """Populate geographic and temporal extent details.

    Parameters:
        parent: Identification element receiving extent definitions.
        main: Main metadata record containing extent boundaries and dates.

    Returns:
        None. Updates the XML tree in place.
    """
    bounds = (
        main.get("west_bounding_coordinate"),
        main.get("east_bounding_coordinate"),
        main.get("south_bounding_coordinate"),
        main.get("north_bounding_coordinate"),
    )
    if not any(value is not None for value in bounds):
        return

    extent = ET.SubElement(parent, _qn("gmd", "extent"))
    ex_extent = ET.SubElement(extent, _qn("gmd", "EX_Extent"))
    geographic_element = ET.SubElement(ex_extent, _qn("gmd", "geographicElement"))
    bbox = ET.SubElement(geographic_element, _qn("gmd", "EX_GeographicBoundingBox"))

    names = [
        ("westBoundLongitude", main.get("west_bounding_coordinate")),
        ("eastBoundLongitude", main.get("east_bounding_coordinate")),
        ("southBoundLatitude", main.get("south_bounding_coordinate")),
        ("northBoundLatitude", main.get("north_bounding_coordinate")),
    ]
    for tag, value in names:
        if value is None:
            continue
        element = ET.SubElement(bbox, _qn("gmd", tag))
        decimal = ET.SubElement(element, _qn("gco", "Decimal"))
        decimal.text = str(value)

    start = _format_date(main.get("temporal_date_from"))
    end = _format_date(main.get("temporal_date_to"))
    if start or end:
        temporal_element = ET.SubElement(ex_extent, _qn("gmd", "temporalElement"))
        temporal_extent = ET.SubElement(temporal_element, _qn("gmd", "EX_TemporalExtent"))
        time_period = ET.SubElement(temporal_extent, _qn("gml", "TimePeriod"))
        if start:
            begin = ET.SubElement(time_period, _qn("gml", "beginPosition"))
            begin.text = start
        if end:
            end_position = ET.SubElement(time_period, _qn("gml", "endPosition"))
            end_position.text = end


def _build_distribution(root: ET.Element, bundle: dict[str, Any]) -> None:
    """Populate distribution information including format details.

    Parameters:
        root: Metadata root element to populate.
        bundle: Metadata bundle containing citation and distribution data.

    Returns:
        None. Updates the XML tree in place.
    """
    citation = bundle.get("citation") or {}

    distribution_info = ET.SubElement(root, _qn("gmd", "distributionInfo"))
    md_distribution = ET.SubElement(distribution_info, _qn("gmd", "MD_Distribution"))
    distribution_format = ET.SubElement(md_distribution, _qn("gmd", "distributionFormat"))
    md_format = ET.SubElement(distribution_format, _qn("gmd", "MD_Format"))

    format_name = citation.get("citation_data_form") or "Unknown"
    name = ET.SubElement(md_format, _qn("gmd", "name"))
    name.append(_character_string(format_name))

    if citation.get("citation_title"):
        version = ET.SubElement(md_format, _qn("gmd", "version"))
        version.append(_character_string(citation["citation_title"]))


def _build_data_quality(root: ET.Element, bundle: dict[str, Any]) -> None:
    """Populate data quality information including lineage sources.

    Parameters:
        root: Metadata root element to populate.
        bundle: Metadata bundle containing group and source data.

    Returns:
        None. Updates the XML tree in place.
    """
    group = bundle.get("group") or {}
    sources = bundle.get("sources", [])
    citation_lookup = bundle.get("citation_lookup", {})

    data_quality_info = ET.SubElement(root, _qn("gmd", "dataQualityInfo"))
    data_quality = ET.SubElement(data_quality_info, _qn("gmd", "DQ_DataQuality"))

    scope = ET.SubElement(data_quality, _qn("gmd", "scope"))
    dq_scope = ET.SubElement(scope, _qn("gmd", "DQ_Scope"))
    level = ET.SubElement(dq_scope, _qn("gmd", "level"))
    scope_code = ET.SubElement(level, _qn("gmd", "MD_ScopeCode"))
    scope_code.set("codeList", "http://www.isotc211.org/2005/resources/codeList.xml#MD_ScopeCode")
    scope_code.set("codeListValue", "dataset")
    scope_code.text = "dataset"

    report = ET.SubElement(data_quality, _qn("gmd", "report"))
    domain_consistency = ET.SubElement(report, _qn("gmd", "DQ_DomainConsistency"))
    result = ET.SubElement(domain_consistency, _qn("gmd", "result"))
    conformance = ET.SubElement(result, _qn("gmd", "DQ_ConformanceResult"))
    explanation = ET.SubElement(conformance, _qn("gmd", "explanation"))
    accuracy = group.get("attribute_accuracy_report") or "No attribute accuracy report supplied."
    explanation.append(_character_string(accuracy))
    passed = ET.SubElement(conformance, _qn("gmd", "pass"))
    passed_boolean = ET.SubElement(passed, _qn("gco", "Boolean"))
    passed_boolean.text = "true"

    lineage = ET.SubElement(data_quality, _qn("gmd", "lineage"))
    li_lineage = ET.SubElement(lineage, _qn("gmd", "LI_Lineage"))

    if sources:
        for source in sources:
            source_element = ET.SubElement(li_lineage, _qn("gmd", "source"))
            li_source = ET.SubElement(source_element, _qn("gmd", "LI_Source"))

            if source.get("source_contribution"):
                description = ET.SubElement(li_source, _qn("gmd", "description"))
                description.append(_character_string(source["source_contribution"]))

            if source.get("source_name"):
                source_scale = ET.SubElement(li_source, _qn("gmd", "sourceScale"))
                md_extent = ET.SubElement(source_scale, _qn("gmd", "MD_RepresentativeFraction"))
                denominator = ET.SubElement(md_extent, _qn("gmd", "denominator"))
                denominator.append(_character_string(source.get("source_scale")))

            linked_citation_ids = []
            if source.get("citation_id"):
                linked_citation_ids.append(source["citation_id"])
            for row in bundle.get("source_citations", {}).get(source["source_id"], []):
                linked_citation_ids.append(row["citation_id"])

            for citation_id in linked_citation_ids:
                citation = citation_lookup.get(citation_id)
                if citation:
                    citation_element = ET.SubElement(li_source, _qn("gmd", "sourceCitation"))
                    citation_element.append(_build_ci_citation(citation))


def _build_ci_citation(citation: dict[str, Any]) -> ET.Element:
    """Build a citation element for lineage or distribution references.

    Parameters:
        citation: Citation record describing publication details.

    Returns:
        Prepared Element representing the citation segment.
    """
    ci_citation = ET.Element(_qn("gmd", "CI_Citation"))
    title = ET.SubElement(ci_citation, _qn("gmd", "title"))
    title.append(_character_string(citation.get("citation_title")))

    if citation.get("citation_pubdate"):
        date_element = ET.SubElement(ci_citation, _qn("gmd", "date"))
        ci_date = ET.SubElement(date_element, _qn("gmd", "CI_Date"))
        date_value = ET.SubElement(ci_date, _qn("gmd", "date"))
        date_value.append(_character_string(_format_date(citation.get("citation_pubdate"))))
        date_type = ET.SubElement(ci_date, _qn("gmd", "dateType"))
        date_type_code = ET.SubElement(date_type, _qn("gmd", "CI_DateTypeCode"))
        date_type_code.set("codeList", "http://www.isotc211.org/2005/resources/codeList.xml#CI_DateTypeCode")
        date_type_code.set("codeListValue", "publication")
        date_type_code.text = "publication"

    if citation.get("online_linkage"):
        linkage = ET.SubElement(ci_citation, _qn("gmd", "onlineResource"))
        online_resource = ET.SubElement(linkage, _qn("gmd", "CI_OnlineResource"))
        url = ET.SubElement(online_resource, _qn("gmd", "linkage"))
        url_value = ET.SubElement(url, _qn("gmd", "URL"))
        url_value.text = citation["online_linkage"]
    return ci_citation


def _build_extension_info(root: ET.Element, bundle: dict[str, Any]) -> None:
    """Populate metadata extension details derived from attribute records.

    Parameters:
        root: Metadata root element to populate.
        bundle: Metadata bundle containing attribute definitions.

    Returns:
        None. Updates the XML tree in place.
    """
    attributes = bundle.get("attributes", [])
    if not attributes:
        return

    metadata_extension = ET.SubElement(root, _qn("gmd", "metadataExtensionInfo"))
    md_extension = ET.SubElement(metadata_extension, _qn("gmd", "MD_MetadataExtensionInformation"))
    for attribute in attributes:
        extended_element = ET.SubElement(md_extension, _qn("gmd", "extendedElementInformation"))
        _optional_element(extended_element, "gmd", "name", attribute.get("attribute_name"))
        _optional_element(extended_element, "gmd", "shortName", attribute.get("attribute_alias"))
        _optional_element(extended_element, "gmd", "definition", attribute.get("attribute_definition"))
        _optional_element(extended_element, "gmd", "condition", attribute.get("codeset_name"))
        data_type_value = attribute.get("attribute_type")
        if data_type_value:
            data_type = ET.SubElement(extended_element, _qn("gmd", "dataType"))
            data_type.append(_character_string(data_type_value))

        precision = attribute.get("attribute_precision")
        scale = attribute.get("attribute_scale")
        width = attribute.get("attribute_width")
        detail_parts = []
        if width is not None:
            detail_parts.append(f"width={width}")
        if precision is not None:
            detail_parts.append(f"precision={precision}")
        if scale is not None:
            detail_parts.append(f"scale={scale}")
        if detail_parts:
            detail_text = "; ".join(detail_parts)
            _optional_element(extended_element, "gmd", "description", detail_text)

