# Copyright 2019 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import re

from sqlalchemy import Column, String, ForeignKey, Index, TIMESTAMP
from sqlalchemy.dialects.mysql import INTEGER
from sqlalchemy.orm import relationship, joinedload

import cfg
from data.models import nvd_template
from data.models.vulnerability import Vulnerability
from data.models.cwe import CweData
from data.models.base import NvdBase
from data.utils import populate_models


class Affect(nvd_template.Affect, NvdBase):
    def to_json(self):
        """Serialize object properties as dict."""
        return {
            "vendor": self.vendor,
            "product": self.product,
            "version": self.version,
        }


class Cert(nvd_template.Cert, NvdBase):
    def to_json(self):
        """Serialize object properties as dict."""
        return {
            "title": self.title,
            "link": self.link,
        }


class Cpe(nvd_template.Cpe, NvdBase):
    nvd_json_id = Column(INTEGER(10), ForeignKey("cve.nvd_jsons.id"), index=True)

    def to_json(self):
        """Serialize object properties as dict."""
        return {
            "uri": self.uri,
            "formatted_string": self.formatted_string,
            "part": self.part,
            "vendor": self.vendor,
            "product": self.product,
            "version": self.version,
            "update": self.update,
            "edition": self.edition,
            "language": self.language,
            "software_edition": self.software_edition,
            "target_sw": self.target_sw,
            "target_hw": self.target_hw,
            "other": self.other,
            "version_start_excluding": self.version_start_excluding,
            "version_start_including": self.version_start_including,
            "version_end_excluding": self.version_end_excluding,
            "version_end_including": self.version_end_including,
        }


Index("idx_cpe_product_lookup", Cpe.vendor, Cpe.product, Cpe.nvd_json_id)


class CveDetail(nvd_template.CveDetail, NvdBase):
    cve_id = Column(String(255))

    def to_json(self):
        """Serialize object properties as dict."""
        return {
            "cve_id": self.cve_id,
        }


Index("idx_cve_detail_cveid", CveDetail.cve_id)


class Cvss2(nvd_template.Cvss2, NvdBase):
    nvd_xml_id = Column(INTEGER(10))

    def to_json(self):
        """Serialize object properties as dict."""
        return {
            "vector_string": self.vector_string,
            "access_vector": self.access_vector,
            "access_complexity": self.access_complexity,
            "authentication": self.authentication,
            "confidentiality_impact": self.confidentiality_impact,
            "integrity_impact": self.integrity_impact,
            "availability_impact": self.availability_impact,
            "base_score": self.base_score,
            "severity": self.severity,
        }


Index("idx_cvsss2_nvd_xml_id", Cvss2.nvd_xml_id)


class Cvss2Extra(nvd_template.Cvss2Extra, NvdBase):
    nvd_json_id = Column(INTEGER(10))

    def to_json(self):
        """Serialize object properties as dict."""
        return {
            "vector_string": self.vector_string,
            "access_vector": self.access_vector,
            "access_complexity": self.access_complexity,
            "authentication": self.authentication,
            "confidentiality_impact": self.confidentiality_impact,
            "integrity_impact": self.integrity_impact,
            "availability_impact": self.availability_impact,
            "base_score": self.base_score,
            "severity": self.severity,
            "exploitability_score": self.exploitability_score,
            "impact_score": self.impact_score,
            "obtain_all_privilege": self.obtain_all_privilege,
            "obtain_user_privilege": self.obtain_user_privilege,
            "obtain_other_privilege": self.obtain_other_privilege,
            "user_interaction_required": self.user_interaction_required,
        }


Index("idx_cvsss2_extra_nvd_json_id", Cvss2Extra.nvd_json_id)


class Cvss3(nvd_template.Cvss3, NvdBase):
    nvd_json_id = Column(INTEGER(10), ForeignKey("cve.nvd_jsons.id"), index=True)

    def to_json(self):
        """Serialize object properties as dict."""
        return {
            "vector_string": self.vector_string,
            "attack_vector": self.attack_vector,
            "attack_complexity": self.attack_complexity,
            "privileges_required": self.privileges_required,
            "user_interaction": self.user_interaction,
            "scope": self.scope,
            "confidentiality_impact": self.confidentiality_impact,
            "integrity_impact": self.integrity_impact,
            "availability_impact": self.availability_impact,
            "base_score": self.base_score,
            "base_severity": self.base_severity,
            "exploitability_score": self.exploitability_score,
            "impact_score": self.impact_score,
        }


class Cwe(nvd_template.Cwe, NvdBase):
    nvd_json_id = Column(INTEGER(10), ForeignKey("cve.nvd_jsons.id"), index=True)
    cwe_data = relationship(
        CweData, primaryjoin="foreign(CweData.cwe_id) == Cwe.cwe_id", uselist=False
    )

    @property
    def cwe_name(self):
        return self.cwe_data.cwe_name if self.cwe_data else None

    def to_json(self):
        """Serialize object properties as dict."""
        return {
            "cwe_id": self.cwe_id,
            "cwe_name": self.cwe_name,
        }


class Description(nvd_template.Description, NvdBase):
    nvd_json_id = Column(INTEGER(10), ForeignKey("cve.nvd_jsons.id"), index=True)

    def to_json(self):
        """Serialize object properties as dict."""
        return {
            "lang": self.lang,
            "value": self.value,
        }


class EnvCpe(nvd_template.EnvCpe, NvdBase):
    cpe_id = Column(INTEGER(10))
    uri = Column(String(255))
    formatted_string = Column(String(255))

    def to_json(self):
        """Serialize object properties as dict."""
        return {
            "cpe_id": self.cpe_id,
            "uri": self.uri,
            "formatted_string": self.formatted_string,
            "well_formed_name": self.well_formed_name,
            "part": self.part,
            "vendor": self.vendor,
            "product": self.product,
            "version": self.version,
            "update": self.update,
            "edition": self.edition,
            "language": self.language,
            "software_edition": self.software_edition,
            "target_sw": self.target_sw,
            "target_hw": self.target_hw,
            "other": self.other,
            "version_start_excluding": self.version_start_excluding,
            "version_start_including": self.version_start_including,
            "version_end_excluding": self.version_end_excluding,
            "version_end_including": self.version_end_including,
        }


Index("idx_envcpes_cpe_id", EnvCpe.cpe_id)
Index("idx_envcpes_uri", EnvCpe.uri)
Index("idx_envcpes_formatted_string", EnvCpe.formatted_string)


class FeedMeta(nvd_template.FeedMeta, NvdBase):
    def to_json(self):
        """Serialize object properties as dict."""
        return {
            "url": self.url,
            "hash": self.hash,
            "last_modified_date": self.last_modified_date,
        }


class Jvn(nvd_template.Jvn, NvdBase):
    cve_id = Column(String(255))

    def to_json(self):
        """Serialize object properties as dict."""
        return {
            "cve_detail_id": self.cve_detail_id,
            "cve_id": self.cve_id,
            "title": self.title,
            "summary": self.summary,
            "jvn_link": self.jvn_link,
            "published_date": self.published_date,
            "last_modified_date": self.last_modified_date,
        }


Index("idx_jvns_cveid", Jvn.cve_id)


class NvdXml(nvd_template.NvdXml, NvdBase):
    cve_id = Column(String(255))

    def to_json(self):
        """Serialize object properties as dict."""
        return {
            "summary": self.summary,
            "published_date": self.published_date,
            "last_modified_date": self.last_modified_date,
        }


Index("idx_nvd_xmls_cveid", NvdXml.cve_id)


class Reference(nvd_template.Reference, NvdBase):
    nvd_json_id = Column(INTEGER(10), ForeignKey("cve.nvd_jsons.id"), index=True)

    def to_json(self):
        """Serialize object properties as dict."""
        return {
            "source": self.source,
            "link": self.link,
        }


class Nvd(nvd_template.NvdJson, NvdBase):
    __tablename__ = "nvd_jsons"
    # Note: An index is defined further below.
    cve_id = Column(String(255))
    cwes = relationship(Cwe, lazy="joined", uselist=True)
    cpes = relationship(Cpe, backref="nvd_entry")
    descriptions = relationship(Description)
    cvss3 = relationship(Cvss3, uselist=False)
    references = relationship(Reference, backref="nvd_entry")
    published_date = Column(TIMESTAMP, index=True)

    def get_products(self):
        return sorted({(cpe.vendor, cpe.product) for cpe in self.cpes})

    def get_languages(self):
        return sorted({cpe.language for cpe in self.cpes})

    def get_links(self):
        return [ref.link for ref in self.references]

    def get_patches(self):
        links = [
            ref.link for ref in self.references if ref.tags and "Patch" in ref.tags
        ]
        patch_regex = re.compile(cfg.PATCH_REGEX)
        return list(filter(patch_regex.match, links))

    def has_patch(self):
        return len(self.get_patches()) > 0

    def has_vcdb_entry(self):
        return Vulnerability.get_by_cve_id(self.cve_id)

    @classmethod
    def get_all_by_link_substring(cls, substring):
        return (
            cls.query.join(Nvd.references)
            .filter(Reference.link.contains(substring))
            .order_by(Nvd.created_at.desc())
            .distinct()
        )

    @classmethod
    def get_all_by_link_regex(cls, regex):
        return (
            cls.query.join(Nvd.references, aliased=True)
            .filter(Reference.link.op("regexp")(regex))
            .order_by(Nvd.created_at.desc())
            .distinct()
            .options(default_nvd_view_options)
        )

    @classmethod
    def get_by_commit_hash(cls, commit_hash):
        return Nvd.get_all_by_link_substring(commit_hash).first()

    @classmethod
    def get_by_cve_id(cls, cve_id):
        return (
            cls.query.filter_by(cve_id=cve_id).options(default_nvd_view_options).first()
        )

    @property
    def description(self):
        if not self.descriptions:
            return None
        return self.descriptions[0].value

    @property
    def score(self):
        return self.cvss3.base_score if self.cvss3 else None

    def to_json(self):
        """Prepare object for Json serialisation."""
        products = [{"vendor": v, "product": p} for v, p in self.get_products()]
        return {
            "is_processed": False,
            "comment": "",
            "cve_id": self.cve_id,
            "cwes": [{"id": c.cwe_id, "name": c.cwe_name} for c in self.cwes],
            "exploit_exists": False,
            "has_annotations": False,
            "master_commit": {},
            "products": products,
            "langs": self.get_languages(),
            "description": self.description,
            "score": self.score,
            "references": [l.link for l in self.references],
        }

    def to_json_full(self):
        """Serialize object properties as dict."""
        data = self.to_json()
        data["nvd"] = self.to_json_raw_data()
        data["commits"] = []
        data["creator"] = None
        data["date_created"] = None
        data["date_modified"] = None
        return data

    def to_json_raw_data(self):
        """Serialize object properties as dict."""
        return {
            "cve_id": self.cve_id,
            "cwes": [c.to_json() for c in self.cwes if self.cwes is not None],
            "cpes": [c.to_json() for c in self.cpes if self.cpes is not None],
            "cvss3": self.cvss3.to_json() if self.cvss3 is not None else None,
            "descriptions": [d.to_json() for d in self.descriptions],
            "published_date": self.published_date,
            "last_modified_date": self.last_modified_date,
            "references": [r.to_json() for r in self.references],
        }


Index("idx_nvd_jsons_cveid", Nvd.cve_id)

# pylint: disable=invalid-name
load_only_cpe_product = joinedload(Nvd.cpes).load_only(Cpe.vendor, Cpe.product)
load_only_cwe_subset = joinedload(Nvd.cwes).load_only(Cwe.cwe_id)
load_only_cwe_subset = load_only_cwe_subset.joinedload(Cwe.cwe_data).load_only(
    CweData.cwe_name
)
load_only_base_score = joinedload(Nvd.cvss3).load_only(Cvss3.base_score)
load_only_description_value = joinedload(Nvd.descriptions).load_only(Description.value)
default_nvd_view_options = [
    load_only_cpe_product,
    load_only_cwe_subset,
    load_only_base_score,
    load_only_description_value,
]
# pylint: enable=invalid-name

# must be set after all definitions
__all__ = populate_models(__name__)
