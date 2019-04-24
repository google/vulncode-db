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

# This file was mostly generated with sqlacodegen which creates a SqlAlchemy
# description from a given SQL schema which is useful since we only have the
# DB schema for the NVD database.
# Documentation: https://pypi.org/project/sqlacodegen/
# Executed: ./sqlacodegen mysql://[name]:[pass]@localhost/cve
import re
import cfg
from data.models.vulnerability import Vulnerability
from data.models.cwe import Cwe
from data.models.base import NvdBase
from data.utils import populate_models
from sqlalchemy import Column, Float, String, TIMESTAMP, ForeignKey, Index
from sqlalchemy.dialects.mysql import INTEGER
from sqlalchemy.orm import relationship





class Cpe(NvdBase):
  __tablename__ = 'cpes'

  id = Column(INTEGER(10), primary_key=True)
  created_at = Column(TIMESTAMP)
  updated_at = Column(TIMESTAMP)
  deleted_at = Column(TIMESTAMP, index=True)
  jvn_id = Column(INTEGER(10), index=True)
  nvd_id = Column(INTEGER(10), ForeignKey('cve.nvds.id'), index=True)
  cpe_name = Column(String(255), index=True)
  part = Column(String(255))
  vendor = Column(String(255))
  product = Column(String(255))
  version = Column(String(255))
  vendor_update = Column(String(255))
  edition = Column(String(255))
  language = Column(String(255))


class CveDetail(NvdBase):
  __tablename__ = 'cve_details'

  id = Column(INTEGER(10), primary_key=True)
  created_at = Column(TIMESTAMP)
  updated_at = Column(TIMESTAMP)
  deleted_at = Column(TIMESTAMP, index=True)
  cve_info_id = Column(INTEGER(10))
  cve_id = Column(String(255), index=True)


class Jvn(NvdBase):
  __tablename__ = 'jvns'

  id = Column(INTEGER(10), primary_key=True)
  created_at = Column(TIMESTAMP)
  updated_at = Column(TIMESTAMP)
  deleted_at = Column(TIMESTAMP, index=True)
  cve_detail_id = Column(INTEGER(10), index=True)
  cve_id = Column(String(255))
  title = Column(String(255))
  summary = Column(String(8192))
  jvn_link = Column(String(255))
  jvn_id = Column(String(255))
  score = Column(Float(asdecimal=True))
  severity = Column(String(255))
  vector = Column(String(255))
  published_date = Column(TIMESTAMP)
  last_modified_date = Column(TIMESTAMP)


class Reference(NvdBase):
  __tablename__ = 'references'

  id = Column(INTEGER(10), primary_key=True)
  created_at = Column(TIMESTAMP)
  updated_at = Column(TIMESTAMP)
  deleted_at = Column(TIMESTAMP, index=True)
  jvn_id = Column(INTEGER(10), index=True)
  nvd_id = Column(INTEGER(10), ForeignKey('cve.nvds.id'), index=True)
  source = Column(String(255))
  link = Column(String(512))


class Nvd(NvdBase):
  #__fulltext_columns__ = ('summary',)
  __tablename__ = 'nvds'

  id = Column(INTEGER(10), primary_key=True)
  created_at = Column(TIMESTAMP)
  updated_at = Column(TIMESTAMP)
  deleted_at = Column(TIMESTAMP, index=True)
  cve_detail_id = Column(INTEGER(10), index=True)
  cve_id = Column(String(255), unique=True)
  summary = Column(String(4096))
  score = Column(Float(asdecimal=True))
  access_vector = Column(String(255))
  access_complexity = Column(String(255))
  authentication = Column(String(255))
  confidentiality_impact = Column(String(255))
  integrity_impact = Column(String(255))
  availability_impact = Column(String(255))
  cwe_id = Column(String(255))
  published_date = Column(TIMESTAMP)
  last_modified_date = Column(TIMESTAMP)

  cwe = relationship(Cwe, primaryjoin='foreign(Cwe.cwe_id) == Nvd.cwe_id')
  cpes = relationship(Cpe, backref='nvd_entry', single_parent=True)
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


Index('nvd_cve_id_index', Nvd.cve_id)

# must be set after all definitions
__all__ = populate_models(__name__)
