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

import cfg
import nvd_template
from data.models.vulnerability import Vulnerability
from data.models.cwe import CweData
from data.models.base import NvdBase
from data.utils import populate_models
from sqlalchemy import Column, Float, String, TIMESTAMP, ForeignKey, Index
from sqlalchemy.dialects.mysql import INTEGER
from sqlalchemy.orm import relationship

class Affect(nvd_template.Affect, NvdBase):
  pass


class Cpe(nvd_template.Cpe, NvdBase):
  nvd_json_id = Column(INTEGER(10), ForeignKey('cve.nvd_jsons.id'), index=True)


class CveDetail(nvd_template.CveDetail, NvdBase):
  pass


class Cvss2(nvd_template.Cvss2, NvdBase):
  pass


class Cvss2Extra(nvd_template.Cvss2Extra, NvdBase):
  pass


class Cvss3(nvd_template.Cvss3, NvdBase):
  nvd_json_id = Column(INTEGER(10), ForeignKey('cve.nvd_jsons.id'), index=True)


class Cwe(nvd_template.Cwe, NvdBase):
  nvd_json_id = Column(INTEGER(10), ForeignKey('cve.nvd_jsons.id'), index=True)
  cwe_data = relationship(CweData, primaryjoin='foreign(CweData.cwe_id) == Cwe.cwe_id', uselist=False)

  @property
  def cwe_name(self):
    return self.cwe_data.cwe_name if self.cwe_data else None


class Description(nvd_template.Description, NvdBase):
  nvd_json_id = Column(INTEGER(10), ForeignKey('cve.nvd_jsons.id'), index=True)


class EnvCpe(nvd_template.EnvCpe, NvdBase):
  pass


class FeedMeta(nvd_template.FeedMeta, NvdBase):
  pass


class Jvn(nvd_template.Jvn, NvdBase):
  pass


class NvdXml(nvd_template.NvdXml, NvdBase):
  pass


class Reference(nvd_template.Reference, NvdBase):
  nvd_json_id = Column(INTEGER(10), ForeignKey('cve.nvd_jsons.id'), index=True)


class Nvd(nvd_template.NvdJson, NvdBase):
  __tablename__ = 'nvd_jsons'
  cwe = relationship(Cwe, uselist=False)
  cpes = relationship(Cpe, backref='nvd_entry', single_parent=True)
  description = relationship(Description, uselist=False)
  cvss3 = relationship(Cvss3, uselist=False)
  references = relationship(Reference, backref='nvd_entry', single_parent=True)
  vulns = relationship(Vulnerability)

  def get_products(self):
    return sorted(set([cpe.product for cpe in self.cpes]))

  def get_languages(self):
    return sorted(set([cpe.language for cpe in self.cpes]))

  def get_links(self):
    return [ref.link for ref in self.references]

  def get_patches(self):
    patch_regex = re.compile(cfg.PATCH_REGEX)
    return filter(patch_regex.match, self.get_links())

  def has_patch(self):
    return len(self.get_patches()) > 0

  def has_vcdb_entry(self):
    return Vulnerability.get_by_cve_id(self.cve_id)

  @classmethod
  def get_all_by_link_substring(cls, substring):
    return cls.query.join(Nvd.references).filter(
      Reference.link.contains(substring)).order_by(
      Nvd.created_at.desc()).distinct()

  @classmethod
  def get_all_by_link_regex(cls, regex):
    return cls.query.join(
      Nvd.references, aliased=True).filter(
      Reference.link.op('regexp')(regex)).order_by(
      Nvd.created_at.desc()).distinct()

  @classmethod
  def get_by_commit_hash(cls, commit_hash):
    return Nvd.get_all_by_link_substring(commit_hash).first()

  @classmethod
  def get_by_cve_id(cls, cve_id):
    return cls.query.filter_by(cve_id=cve_id).first()

  @property
  def summary(self):
    return self.description.value if self.description else None

  @property
  def score(self):
    return self.cvss3.base_score if self.cvss3 else None


# must be set after all definitions
__all__ = populate_models(__name__)
